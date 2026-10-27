"""Explicit local import of ISM press-release tables; no discovery or scheduling."""
import argparse
import calendar
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
import httpx
from app.database.connection import get_connection

MONTHS = {name.lower(): n for n in range(1, 13) for name in (calendar.month_name[n], calendar.month_abbr[n])}
KINDS = {"manufacturing": "ISM_MANUFACTURING_PMI", "services": "ISM_SERVICES_PMI"}
RAW_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw" / "ism"

class Node:
    def __init__(self, tag, attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
    def text(self):
        return " ".join(child.text() if isinstance(child, Node) else child for child in self.children)
    def all(self, tag):
        return [child for item in self.children if isinstance(item, Node) for child in ([item] if item.tag == tag else []) + item.all(tag)]

class Tree(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]
        self.nodes = []
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break
    def handle_data(self, data):
        self.stack[-1].children.append(data)

def clean(text):
    return re.sub(r"\s+", " ", text.replace("\u00ae", "")).strip()

def month(text):
    match = re.fullmatch(r"([A-Za-z]+) (\d{4})", clean(text))
    if not match or match[1].lower() not in MONTHS:
        raise ValueError("Invalid month in ISM history table.")
    return date(int(match[2]), MONTHS[match[1].lower()], 1)

def parse_report(html, kind):
    if kind not in KINDS:
        raise ValueError("Unknown ISM index kind.")
    tree = Tree(html)
    authors = [n.attrs.get("content", "") for n in tree.nodes if n.tag == "meta" and n.attrs.get("name") == "author"]
    if authors != ["Institute for Supply Management"]:
        raise ValueError("Release publisher must be Institute for Supply Management.")
    label = kind.capitalize()
    headings = tree.root.all("h1")
    if len(headings) != 1:
        raise ValueError("Expected one release heading.")
    title = clean(headings[0].text())
    report = re.search(r"; ([A-Za-z]+ \d{4}) ISM " + label + r" PMI Report", title)
    if not report:
        raise ValueError("Release type/month does not match requested index.")
    title_value = re.search(label + r" PMI at ([0-9]+(?:\.[0-9]+)?)", title)
    if not title_value:
        raise ValueError("Missing headline reading.")
    report_month = month(report[1])
    published = re.findall(r'"datePublished"\s*:\s*"([^"]+)"', html)
    if len(set(published)) != 1:
        raise ValueError("Missing or ambiguous document publication timestamp.")
    published_at = datetime.fromisoformat(published[0].replace("Z", "+00:00"))
    if published_at.tzinfo is None or published_at.date() < report_month or published_at > datetime.now(timezone.utc):
        raise ValueError("Invalid publication timestamp.")
    bodies = [n for n in tree.nodes if n.tag == "section" and "release-body" in n.attrs.get("class", "").split()]
    if len(bodies) != 1:
        raise ValueError("Expected ISM release body, not a challenge/error page.")
    body = clean(bodies[0].text())
    headline = re.search(label + r" PMI registered ([0-9]+(?:\.[0-9]+)?) percent", body)
    if not headline:
        raise ValueError("Missing principal reading in release body.")
    caption = "THE LAST 12 MONTHS" if kind == "manufacturing" else "SERVICES PMI HISTORY"
    markers = [n for n in bodies[0].all("p") if clean(n.text()).upper() == caption]
    if len(markers) != 1:
        raise ValueError("Missing or ambiguous required ISM history table heading.")
    after = tree.nodes[tree.nodes.index(markers[0])+1:]
    table = next((n for n in after if n.tag == "table"), None)
    if table is None or table not in bodies[0].all("table"):
        raise ValueError("Missing history table.")
    rows = table.all("tr")
    if not rows or clean(rows[0].text()).count("Month") != 2 or label + " PMI" not in clean(rows[0].text()):
        raise ValueError("Unexpected history table columns.")
    readings = []
    for row in rows[1:]:
        cells = [clean(n.text()) for n in row.all("td")]
        if cells and cells[0].startswith("Average for 12 months"):
            continue
        if len(cells) != 4:
            raise ValueError("Unexpected history row structure.")
        for i in (0, 2):
            day, value = month(cells[i]), float(cells[i+1])
            if not math.isfinite(value) or not 0 <= value <= 100:
                raise ValueError("ISM value outside finite 0-100 range.")
            readings.append((day, value))
    ordinal = report_month.year * 12 + report_month.month - 1
    expected = {date((ordinal-i)//12, (ordinal-i)%12+1, 1) for i in range(12)}
    if len(readings) != 12 or {d for d, v in readings} != expected:
        raise ValueError("Expected 12 unique consecutive months ending at report month.")
    readings.sort()
    if readings[-1][1] != float(headline[1]) or float(headline[1]) != float(title_value[1]):
        raise ValueError("Principal reading disagrees with newest table row.")
    return {"series_id": KINDS[kind], "report_month": report_month, "published_at": published_at, "readings": readings}

def fetch_report(url, kind):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "www.prnewswire.com" or not parsed.path.startswith("/news-releases/") or parsed.username or parsed.password:
        raise ValueError("Use a public HTTPS PR Newswire news-release URL.")
    response = httpx.get(url, timeout=40, follow_redirects=False)
    response.raise_for_status()
    if "text/html" not in response.headers.get("content-type", "").lower():
        raise ValueError("Expected a PR Newswire HTML release.")
    report = parse_report(response.text, kind)
    return report, response.content

def store_report(report, url, content):
    retrieved = datetime.now(timezone.utc)
    digest = hashlib.sha256(content).hexdigest()
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    path = RAW_ROOT / (retrieved.strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex + ".html")
    with path.open("xb") as raw:
        raw.write(content)
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""INSERT INTO ism_documents (series_id, report_month, published_at, source_url, retrieved_at, raw_hash, raw_path)
                VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (series_id, raw_hash) DO NOTHING RETURNING id""",
                (report["series_id"], report["report_month"], report["published_at"], url, retrieved, digest, str(path.relative_to(RAW_ROOT.parent.parent))))
            row = cursor.fetchone()
            if row:
                cursor.executemany("INSERT INTO ism_observations (document_id, observation_date, value) VALUES (%s,%s,%s)", [(row[0], day, value) for day, value in report["readings"]])
        connection.commit()
        return bool(row)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=KINDS)
    parser.add_argument("url")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        report, content = fetch_report(args.url, args.kind)
        print(json.dumps({**{k:v for k,v in report.items() if k != "readings"}, "count": len(report["readings"]), "current": report["readings"][-1], "previous": report["readings"][-2], "dry_run": args.dry_run}, default=str))
        if not args.dry_run:
            print("Imported." if store_report(report, args.url, content) else "Already imported; no database change.")
        return 0
    except Exception as error:
        print(f"ISM import failed: {error}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
