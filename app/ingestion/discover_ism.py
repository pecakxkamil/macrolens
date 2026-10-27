"""Discover latest ISM releases on its public PR Newswire publisher page."""
import re
from urllib.parse import urljoin, urlparse
import httpx
from app.ingestion import import_ism
from app.database.connection import get_connection
from app.ingestion.request_budget import before_request

INDEX_URL = 'https://www.prnewswire.com/news/institute-for-supply-management/'


def discover(html):
    tree = import_ism.Tree(html).root
    if 'Institute for Supply Management' not in tree.text():
        raise ValueError('ISM publisher listing was not confirmed.')
    found = {}
    for link in tree.all('a'):
        title = import_ism.clean(link.text())
        url = urljoin(INDEX_URL, link.attrs.get('href', ''))
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'www.prnewswire.com' or not parsed.path.startswith('/news-releases/'):
            continue
        for kind in import_ism.KINDS:
            match = re.search(r'([A-Za-z]+ 20[0-9]{2}) ISM ' + kind + r' PMI Report', title, re.I)
            if not match:
                continue
            month = import_ism.month(match[1])
            candidate = (month, parsed._replace(query='', fragment='').geturl())
            if kind not in found or month > found[kind][0]:
                found[kind] = candidate
            elif month == found[kind][0] and candidate[1] != found[kind][1]:
                raise ValueError('Ambiguous latest ISM document for one month.')
    if set(found) != set(import_ism.KINDS):
        raise ValueError('Both latest ISM report types were not discoverable.')
    return found


def fetch_listing():
    before_request('ISM')
    response = httpx.get(INDEX_URL, timeout=20, follow_redirects=False)
    response.raise_for_status()
    if 'text/html' not in response.headers.get('content-type', '').lower():
        raise ValueError('ISM publisher listing is not HTML.')
    return discover(response.text)


def import_discovered(kind, candidate):
    expected_month, url = candidate
    before_request('ISM')
    report, content = import_ism.fetch_report(url, kind)
    if report['report_month'] != expected_month or report['series_id'] != import_ism.KINDS[kind]:
        raise ValueError('Discovered ISM report period/type disagrees with its document.')
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT report_month, published_at FROM ism_documents WHERE series_id=%s ORDER BY report_month DESC, published_at DESC LIMIT 1', (report['series_id'],))
            latest = cursor.fetchone()
        if latest and (report['report_month'], report['published_at']) < latest:
            raise ValueError('Discovered ISM document is older than the stored latest report.')
    finally:
        connection.close()
    inserted = import_ism.store_report(report, url, content)
    return {'latest_publication_discovered': True, 'report_month': str(expected_month),
        'published_at': report['published_at'].isoformat(), 'source_url': url, 'new_document': inserted}
