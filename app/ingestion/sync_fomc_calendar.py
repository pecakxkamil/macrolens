"""Official FOMC decisions and related events through one stored schedule.

Run: python -m app.ingestion.sync_fomc_calendar
"""
import calendar
import json
import os
import re
import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, urlparse

import httpx
from app.analytics.fomc_calendar import SNAPSHOT_PATH, SOURCE_URL
from app.source_checks import availability_check
from app.ingestion.request_budget import before_request


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def text(self):
        return " ".join(child.text() if isinstance(child, Node) else child for child in self.children).strip()

    def find(self, predicate):
        result = []
        for child in self.children:
            if isinstance(child, Node):
                if predicate(child):
                    result.append(child)
                result.extend(child.find(predicate))
        return result


class Tree(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def has_class(node, name):
    return name in node.attrs.get("class", "").split()


def parse_meetings(html, minimum_year, detailed=False):
    tree = Tree(html).root
    meetings = []
    for panel in tree.find(lambda node: has_class(node, "panel")):
        headings = panel.find(lambda node: node.tag == "h4")
        year_match = re.search(r"(20[0-9]{2}) FOMC Meetings", " ".join(node.text() for node in headings))
        if not year_match or int(year_match[1]) < minimum_year:
            continue
        year = int(year_match[1])
        ordinal = 0
        for row in panel.find(lambda node: has_class(node, "fomc-meeting")):
            months = row.find(lambda node: has_class(node, "fomc-meeting__month"))
            days = row.find(lambda node: has_class(node, "fomc-meeting__date"))
            if not months or not days:
                raise ValueError("Incomplete official FOMC meeting row")
            label, day_text = months[0].text(), days[0].text().replace("*", "").strip()
            if re.search(r"unscheduled|notation", row.text(), re.I):
                continue
            numbers = re.fullmatch(r"(\d{1,2})(?:\s*[-\u2013]\s*(\d{1,2}))?", day_text)
            if not numbers:
                raise ValueError(f"Unsupported official meeting date: {label} {day_text}")
            month_names = label.replace(" ", "").split("/")
            def month_number(name):
                return next(i for i in range(1, 13) if calendar.month_name[i].lower().startswith(name.lower()))
            start_month, end_month = month_number(month_names[0]), month_number(month_names[-1])
            start_day, end_day = int(numbers[1]), int(numbers[2] or numbers[1])
            start = date(year, start_month, start_day)
            end = date(year + (end_month < start_month), end_month, end_day)
            if end < start:
                raise ValueError("FOMC meeting ends before it starts")
            ordinal += 1
            links = [urljoin(SOURCE_URL, a.attrs.get('href', '')) for a in row.find(lambda n: n.tag == 'a')]
            documents = {kind: next((url for url in links if token in url and urlparse(url).hostname == 'www.federalreserve.gov' and url.endswith('.htm')), None)
                         for kind, token in [('fomc_press_conference', 'fomcpresconf'), ('fomc_minutes', 'fomcminutes'), ('fomc_sep', 'fomcprojtabl')]}
            released = re.search(r'Released\s+(\w+\s+\d{1,2},\s+20\d{2})', row.text())
            meetings.append({'start': start, 'end': end, 'meeting_id': f'fomc:{year}:meeting-{ordinal}',
                             'sep': '*' in days[0].text(), 'documents': documents,
                             'minutes_date': datetime.strptime(released[1], '%B %d, %Y').date() if released else None})
    if not meetings or len({m['end'] for m in meetings}) != len(meetings):
        raise ValueError("No unique future-year FOMC schedule found")
    meetings.sort(key=lambda m: m['end'])
    return meetings if detailed else [(m['start'], m['end']) for m in meetings]


def monthly_url(day):
    return f"https://www.federalreserve.gov/newsevents/{day.year}-{calendar.month_name[day.month].lower()}.htm"


def parse_decision_time(html, day):
    tree = Tree(html).root
    headings = tree.find(lambda node: node.tag in {"h2", "h3", "h4"})
    if not any(re.search(calendar.month_name[day.month] + r"\s+" + str(day.year), node.text(), re.I) for node in headings):
        return None
    matches = []
    for row in tree.find(lambda node: has_class(node, "row")):
        columns = [child for child in row.children if isinstance(child, Node) and child.tag == "div"]
        if len(columns) != 3:
            continue
        clock, description, date_text = [node.text() for node in columns]
        titles = columns[1].find(lambda node: node.tag == "p")
        if not titles or titles[0].text() != "FOMC Meeting" or "Two-day meeting" not in description or date_text.strip() != str(day.day):
            continue
        match = re.fullmatch(r"(\d{1,2}):(\d{2})\s*([ap])\.m\.", clock, re.I)
        if match:
            hour = int(match[1]) % 12 + (12 if match[3].lower() == "p" else 0)
            matches.append(time(hour, int(match[2])).isoformat())
    return matches[0] if len(matches) == 1 else None


def make_event(start, end, release_time, retrieved_at, time_source_url=None):
    instant = (datetime.combine(end, time.fromisoformat(release_time), ZoneInfo("America/New_York"))
               .astimezone(timezone.utc).isoformat() if release_time else None)
    return {"event_id": f"fomc:{end.isoformat()}", "event_type": "fomc_decision", "release_id": None,
            "release_name": "FOMC policy decision", "release_date": end.isoformat(),
            "meeting_start_date": start.isoformat(), "meeting_end_date": end.isoformat(),
            "release_time": release_time, "source_timezone": "America/New_York" if release_time else None,
            "release_datetime_utc": instant, "time_source_url": time_source_url if release_time else None,
            "source_link": SOURCE_URL, "retrieved_at": retrieved_at, "importance": "high",
            "date_precision": "date", "series": []}


FED_EVENT_NAMES = {'fomc_press_conference': 'FOMC Press Conference',
                   'fomc_minutes': 'FOMC Meeting Minutes', 'fomc_sep': 'Fed Economic Projections (SEP)'}


def monthly_events(html, month):
    """Read independently timed rows; never use the decision's clock for SEP."""
    root = Tree(html).root
    if not any(re.search(calendar.month_name[month.month] + r'\s+' + str(month.year), n.text(), re.I)
               for n in root.find(lambda n: n.tag in {'h2', 'h3', 'h4'})):
        return []
    result = {}
    titles = {'FOMC Press Conference': 'fomc_press_conference', 'FOMC Minutes': 'fomc_minutes',
              'Summary of Economic Projections': 'fomc_sep', 'FOMC Economic Projections': 'fomc_sep'}
    for row in root.find(lambda n: has_class(n, 'row')):
        columns = [n for n in row.children if isinstance(n, Node) and n.tag == 'div']
        if len(columns) != 3:
            continue
        labels = columns[1].find(lambda n: n.tag == 'p')
        title = labels[0].text() if labels else ''
        kind = titles.get(title)
        if not kind or not re.fullmatch(r'\d{1,2}', columns[2].text()):
            continue
        day = date(month.year, month.month, int(columns[2].text()))
        clock = re.fullmatch(r'(\d{1,2}):(\d{2})\s*([ap])\.m\.', columns[0].text(), re.I)
        release_time = time(int(clock[1]) % 12 + (12 if clock[3].lower() == 'p' else 0), int(clock[2])).isoformat() if clock else None
        item = dict(kind=kind, day=day, clock=release_time, description=columns[1].text())
        key = (kind, day)
        if key in result and result[key] != item:
            raise ValueError('Conflicting official Fed event rows')
        result[key] = item
    return list(result.values())


def related_meeting(item, meetings):
    if item['kind'] != 'fomc_minutes':
        return next((m for m in meetings if m['end'] == item['day']), None)
    # Exact meeting range in the row, not an assumed three-week offset.
    match = re.search(r'Meeting of\s+(\w+)(?:\s+(\d{1,2})\s*[-–]\s*(?:(\w+)\s+)?)?(\d{1,2})(?:,?\s+(20\d{2}))?', item['description'])
    if not match:
        return None
    start_month = next((i for i in range(1,13) if calendar.month_name[i].lower() == match[1].lower()), None)
    end_month = next((i for i in range(1,13) if calendar.month_name[i].lower() == (match[3] or match[1]).lower()), None)
    if not start_month or not end_month:
        return None
    start_day, end_day = int(match[2] or match[4]), int(match[4])
    candidates = [m for m in meetings if m['start'].month == start_month and m['end'].month == end_month
                  and m['start'].day == start_day and m['end'].day == end_day and m['end'] <= item['day']
                  and (item['day']-m['end']).days < 90 and (not match[5] or m['end'].year == int(match[5]))]
    return candidates[0] if len(candidates) == 1 else None


def nonnumeric_event(meeting, kind, day, clock, retrieved_at, source_url, raw_hash):
    event = make_event(meeting['start'], meeting['end'], None, retrieved_at)
    event.update(event_id=f"{meeting['meeting_id']}:{kind}", meeting_id=meeting['meeting_id'],
                 event_type=kind, release_name=FED_EVENT_NAMES[kind], release_date=str(day), release_time=clock,
                 source_timezone='America/New_York', time_source_url=source_url if clock else None,
                 release_datetime_utc=datetime.combine(day, time.fromisoformat(clock), ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat() if clock else None,
                 importance='medium' if kind == 'fomc_minutes' else 'high', expects_numeric_result=False, measures=[],
                 date_status='confirmed', time_status='confirmed' if clock else 'unconfirmed',
                 date_source_url=source_url, schedule_provenance={'source_url':source_url,'retrieved_at':retrieved_at,'raw_hash':raw_hash},
                 document_url=meeting['documents'].get(kind),
                 document_status='available' if meeting['documents'].get(kind) else 'not_available',
                 description={'fomc_press_conference':'Official FOMC press conference; a transcript may be published later.',
                              'fomc_minutes':'Official minutes of the linked FOMC meeting.',
                              'fomc_sep':'Official economic projections; the dot plot is part of SEP.'}[kind])
    return event


def sync_schedule(client, path=None, raw_root=None, now=None):
    with availability_check("fed:calendar", {"provider": "Federal Reserve", "scope": "meeting dates and explicitly published decision times"}) as check:
        result = _sync_schedule(client, path, raw_root, now, check["scope"])
        check["scope"]["dates"] = [event["release_date"] for event in result["events"]]
        unknown = sorted(set([event["release_date"] for event in result["events"]
                   if event["release_date"] >= (now or datetime.now(timezone.utc)).date().isoformat() and not event["release_time"]]
                   + [row['release_date'] for row in check['scope'].get('time_checks', []) if row['time_status']=='unconfirmed']))
        if unknown:
            check.update(status="partial", error_code="decision_times_unavailable")
            check["scope"]["missing_times"] = unknown
        if check['scope'].get('page_errors'):
            check.update(status='partial', error_code='decision_times_unavailable')
        return result


def _sync_schedule(client, path=None, raw_root=None, now=None, check_scope=None):
    now = now or datetime.now(timezone.utc)
    target = Path(path or SNAPSHOT_PATH)
    raw = Path(raw_root or target.parents[1] / "raw/federal_reserve/fomc") / (now.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex)
    raw.mkdir(parents=True, exist_ok=False)
    hashes = {}
    def fetch(url):
        before_request("Federal Reserve")
        response = client.get(url)
        # Preserve response and provenance before parsing, including failed responses.
        name = url.rsplit("/", 1)[-1]
        (raw / name).write_bytes(response.content)
        hashes[url] = hashlib.sha256(response.content).hexdigest()
        (raw / (name + ".json")).write_text(json.dumps({"source_url": url, "retrieved_at": now.isoformat(), "status_code": response.status_code, 'raw_hash':hashes[url]}), encoding="utf-8")
        response.raise_for_status()
        return response.text
    main_html = fetch(SOURCE_URL)
    history_start = date(now.year - (now.month == 1), (now.month - 2) % 12 + 1, 1)
    meetings = [m for m in parse_meetings(main_html, now.year - 1, detailed=True)
                if m['end'] >= history_start or m['end'].year >= now.year]
    try:
        previous = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    prior = {e['event_id']: e for e in previous.get('events', [])}
    events, pages, page_errors = [], {}, {}
    time_checks = []
    # Existing decision coverage is retained; new history is deliberately bounded.
    recent = [m for m in meetings if m['end'] >= history_start]
    months = {m['end'].replace(day=1) for m in recent}
    months.update(date(m['end'].year + (m['end'].month == 12), m['end'].month % 12 + 1, 1) for m in recent)
    for month in sorted(months):
        url = monthly_url(month)
        try:
            pages[url] = fetch(url)
        except httpx.HTTPError as error:
            pages[url] = ''
            page_errors[url] = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
    for meeting in meetings:
        start, end = meeting['start'], meeting['end']
        url = monthly_url(end)
        release_time = parse_decision_time(pages.get(url, ''), end)
        event = make_event(start, end, release_time, now.isoformat(), url)
        event['meeting_id'] = meeting['meeting_id']
        old = prior.get(event['event_id'])
        if not release_time and old and old.get('release_time'):
            for key in ('release_time','source_timezone','release_datetime_utc','time_source_url'):
                event[key] = old[key]
        events.append(event)
        if end >= now.astimezone(ZoneInfo('America/New_York')).date():
            time_checks.append({'release_date':str(end), 'fetch_status':'error' if url in page_errors else 'success',
                                'http_status':page_errors.get(url), 'time_status':'confirmed' if release_time else 'unconfirmed'})
    new_events = {}
    def add(meeting, kind, day, clock, url):
        event = nonnumeric_event(meeting, kind, day, clock, now.isoformat(), url, hashes[url])
        old = prior.get(event['event_id'])
        if old and not clock and old.get('release_time') and old['release_date'] == str(day):
            for key in ('release_time','release_datetime_utc','time_source_url','time_status'):
                event[key] = old[key]
        if old and old.get('document_url') and not event['document_url']:
            event['document_url'], event['document_status'] = old['document_url'], old['document_status']
        new_events[event['event_id']] = event
    for meeting in recent:
        if meeting['sep']:
            add(meeting, 'fomc_sep', meeting['end'], None, SOURCE_URL)
        if meeting['documents']['fomc_press_conference']:
            add(meeting, 'fomc_press_conference', meeting['end'], None, SOURCE_URL)
        if meeting['minutes_date']:
            add(meeting, 'fomc_minutes', meeting['minutes_date'], None, SOURCE_URL)
    for month in sorted(months):
        url = monthly_url(month)
        for item in monthly_events(pages[url], month):
            meeting = related_meeting(item, recent)
            if meeting and (item['kind'] != 'fomc_sep' or meeting['sep']):
                add(meeting, item['kind'], item['day'], item['clock'], url)
    # A failed/shortened page is not evidence that a previously confirmed event vanished.
    for key, old in prior.items():
        if old.get('event_type') in FED_EVENT_NAMES and key not in new_events:
            new_events[key] = old
    time_checks.extend({'event_id':e['event_id'], 'release_date':e['release_date'],
                        'fetch_status':'error' if monthly_url(date.fromisoformat(e['release_date'])) in page_errors else 'success',
                        'http_status':page_errors.get(monthly_url(date.fromisoformat(e['release_date']))),
                        'time_status':e['time_status']} for e in new_events.values())
    events.extend(new_events.values())
    history = previous.get('history', [])[:]
    changes = []
    for event in events:
        old = prior.get(event['event_id'])
        keys = ('release_date','release_time','document_url','meeting_start_date','meeting_end_date')
        if old and any(old.get(k) != event.get(k) for k in keys):
            record = {'event_id':event['event_id'],'changed_at':now.isoformat(),'before':old,
                      'after':{k:event.get(k) for k in keys}}
            history.append(record)
            changes.append({'event_id':event['event_id'],'status':'schedule_changed' if any(old.get(k)!=event.get(k) for k in ('release_date','release_time')) else 'document_available'})
        elif not old:
            changes.append({'event_id':event['event_id'],'status':'event_confirmed'})
    if check_scope is not None:
        check_scope['time_checks'] = time_checks
        check_scope['event_changes'] = changes
        check_scope['page_errors'] = page_errors
        check_scope['unconfirmed_event_times'] = [e['event_id'] for e in new_events.values() if not e['release_time']]
    payload = {'version':1,'adapter_version':2,'source_url':SOURCE_URL,'retrieved_at':now.isoformat(),'events':events,
               'page_errors':page_errors}
    if history:
        payload['history'] = history
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return payload


def main():
    with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "MacroLens official calendar refresh"}) as client:
        result = sync_schedule(client)
    print(f"Stored {len(result['events'])} FOMC events; retrieved {result['retrieved_at']}. No FRED data modified.")


if __name__ == "__main__":
    main()
