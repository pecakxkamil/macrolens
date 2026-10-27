"""Explicit refresh of public Federal Reserve schedules, independent of FRED ingestion.

Run: python -m app.ingestion.sync_fomc_calendar
"""
import calendar
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

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


def parse_meetings(html, minimum_year):
    tree = Tree(html).root
    meetings = []
    for panel in tree.find(lambda node: has_class(node, "panel")):
        headings = panel.find(lambda node: node.tag == "h4")
        year_match = re.search(r"(20[0-9]{2}) FOMC Meetings", " ".join(node.text() for node in headings))
        if not year_match or int(year_match[1]) < minimum_year:
            continue
        year = int(year_match[1])
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
            meetings.append((start, end))
    if not meetings or len({end for _, end in meetings}) != len(meetings):
        raise ValueError("No unique future-year FOMC schedule found")
    return sorted(meetings)


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


def sync_schedule(client, path=None, raw_root=None, now=None):
    with availability_check("fed:calendar", {"provider": "Federal Reserve", "scope": "meeting dates and explicitly published decision times"}) as check:
        result = _sync_schedule(client, path, raw_root, now, check["scope"])
        check["scope"]["dates"] = [event["release_date"] for event in result["events"]]
        unknown = [event["release_date"] for event in result["events"]
                   if event["release_date"] >= (now or datetime.now(timezone.utc)).date().isoformat() and not event["release_time"]]
        if unknown:
            check.update(status="partial", error_code="decision_times_unavailable")
            check["scope"]["missing_times"] = unknown
        return result


def _sync_schedule(client, path=None, raw_root=None, now=None, check_scope=None):
    now = now or datetime.now(timezone.utc)
    target = Path(path or SNAPSHOT_PATH)
    raw = Path(raw_root or target.parents[1] / "raw/federal_reserve/fomc") / (now.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex)
    raw.mkdir(parents=True, exist_ok=False)
    def fetch(url):
        before_request("Federal Reserve")
        response = client.get(url)
        # Preserve response and provenance before parsing, including failed responses.
        name = url.rsplit("/", 1)[-1]
        (raw / name).write_text(response.text, encoding="utf-8")
        (raw / (name + ".json")).write_text(json.dumps({"source_url": url, "retrieved_at": now.isoformat(), "status_code": response.status_code}), encoding="utf-8")
        response.raise_for_status()
        return response.text
    meetings = parse_meetings(fetch(SOURCE_URL), now.year)
    events, pages, page_errors = [], {}, {}
    time_checks = []
    for start, end in meetings:
        release_time = None
        if end >= now.astimezone(ZoneInfo("America/New_York")).date():
            url = monthly_url(end)
            if url not in pages:
                try:
                    pages[url] = fetch(url)
                except httpx.HTTPError as error:
                    pages[url] = ""
                    page_errors[url] = (error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None)
            release_time = parse_decision_time(pages[url], end)
            time_checks.append({"release_date": end.isoformat(),
                "fetch_status": "error" if url in page_errors else "success",
                "http_status": page_errors.get(url),
                "time_status": "confirmed" if release_time else "unconfirmed"})
        events.append(make_event(start, end, release_time, now.isoformat(), monthly_url(end)))
    if check_scope is not None:
        check_scope["time_checks"] = time_checks
    payload = {"version": 1, "source_url": SOURCE_URL, "retrieved_at": now.isoformat(), "events": events}
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
    print(f"Stored {len(result['events'])} FOMC meetings; retrieved {result['retrieved_at']}. No FRED data modified.")


if __name__ == "__main__":
    main()
