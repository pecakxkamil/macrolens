"""Reviewed publisher-specific parsers, bounded HTTP, actual source receipts.

Unrecognized layouts stop for review. No LLM extraction, consensus or numeric
fallback. Source bindings contain identities/periods, never expected amounts.
"""
import hashlib
import io
import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urljoin
import httpx
from pypdf import PdfReader
from app.ingestion.request_budget import before_request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'config/earnings_monitor_sources.json'
METHOD = 'automated_official_report_validation'
MAX_BYTES = 8 * 1024 * 1024
PARSER_VERSION = 'official-pdf-v1'


class NotPublished(ValueError):
    pass


class ReviewRequired(ValueError):
    pass


class RetryHTTP(ValueError):
    def __init__(self, status, retry_after=0):
        self.status, self.retry_after = status, retry_after
        super().__init__('http_' + str(status))


def bindings():
    return json.loads(DATA.read_text(encoding='utf-8'))


def binding(event):
    return next((r for r in bindings() if all(event[k] == r[k] for k in
                ('cik', 'ticker', 'fiscal_year', 'fiscal_quarter', 'period_label'))), None)


def fetch(client, spec, directory, now, pace=None):
    url = spec['url']
    chain = []
    for _ in range(3):
        if url not in spec['allowed_urls']:
            raise ReviewRequired('unreviewed_redirect')
        if pace:
            pace(url)
        before_request('EARNINGS')
        with client.stream('GET', url) as response:
            status = response.status_code
            chain.append(dict(url=url, status=status))
            if status in (301, 302, 303, 307, 308):
                url = urljoin(url, response.headers.get('location', ''))
                continue
            if status == 404:
                raise NotPublished('document_not_found')
            if status == 429 or status >= 500:
                value = response.headers.get('retry-after', '')
                try:
                    retry = int(value)
                except ValueError:
                    from email.utils import parsedate_to_datetime
                    try:
                        retry = max(0, int((parsedate_to_datetime(value) - now).total_seconds()))
                    except (ValueError, TypeError, OverflowError):
                        retry = 0
                raise RetryHTTP(status, min(max(retry, 0), 7200))
            if status != 200:
                raise ReviewRequired('publisher_http_' + str(status))
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise ReviewRequired('document_too_large')
            body = bytes(body)
            if not body.startswith(b'%PDF'):
                raise ReviewRequired('not_a_pdf_or_publisher_challenge')
            sha = hashlib.sha256(body).hexdigest()
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / (sha + '.pdf')
            if not path.exists():
                with path.open('xb') as output:
                    output.write(body)
            receipt = dict(url=url, linked_from=spec['url'], sha256=sha, bytes=len(body),
                           fetched_at=now.isoformat(), path=str(path.resolve()), chain=chain,
                           content_type=response.headers.get('content-type'),
                           etag=response.headers.get('etag'), last_modified=response.headers.get('last-modified'))
            (directory / (sha + '.receipt.json')).write_text(json.dumps(receipt, indent=2), encoding='utf-8')
            return body, receipt
    raise ReviewRequired('too_many_redirects')


def normalized(text):
    return re.sub(r'\s+', ' ', text).strip()


NUMBER = r'(\(?\$?\s*\(?-?\d[\d,]*(?:\.\d+)?\)?)'


def number(text):
    negative = '(' in text
    result = Decimal(re.sub(r'[\s$,()]', '', text))
    return -result if negative else result


def value(pattern, text):
    matches = re.findall(pattern, text)
    if len(matches) != 1:
        raise ReviewRequired('ambiguous_or_changed_financial_layout')
    return number(matches[0])


def parse(body, spec, receipt):
    if receipt['sha256'] != hashlib.sha256(body).hexdigest() or receipt['url'] not in spec['allowed_urls']:
        raise ReviewRequired('receipt_identity_mismatch')
    try:
        pdf = PdfReader(io.BytesIO(body))
        if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 40:
            raise ReviewRequired('unsupported_pdf')
        pages = [normalized(page.extract_text() or '') for page in pdf.pages]
    except ReviewRequired:
        raise
    except Exception as error:
        raise ReviewRequired('pdf_parse_failed') from error
    if sum(map(len, pages)) > 1000000:
        raise ReviewRequired('pdf_text_too_large')
    all_text = ' '.join(pages)
    day = datetime.fromisoformat(spec['release_date'])
    release_label = day.strftime('%B ') + str(day.day) + day.strftime(', %Y')
    if release_label not in all_text:
        raise NotPublished('release_date_not_found')
    if spec['adapter'] == 'qcom-quarterly-gaap-v1':
        text = pages[0]
        if 'Qualcomm Incorporated (NASDAQ: QCOM)' not in text:
            raise ReviewRequired('issuer_mismatch')
        title = 'Qualcomm Announces Fourth Quarter and Fiscal ' + str(spec['fiscal_year']) + ' Results'
        end = datetime.fromisoformat(spec['period_end'])
        end_label = end.strftime('%B ') + str(end.day) + end.strftime(', %Y')
        if spec['fiscal_quarter'] != 4 or title not in text or 'year ended ' + end_label not in text:
            raise NotPublished('fiscal_period_mismatch')
        header = ('Fourth Quarter Results1 GAAP Non-GAAP (in millions, except per share data and percentages) '
                  'Q4 Fiscal {0} Q4 Fiscal {1} Change Q4 Fiscal {0} Q4 Fiscal {1} Change').format(spec['fiscal_year'], spec['fiscal_year']-1)
        if header not in text:
            raise ReviewRequired('gaap_column_or_unit_not_verified')
        quarter = text.split(header, 1)[1].split('Fiscal ' + str(spec['fiscal_year']) + ' Results', 1)[0]
        revenue = value(r'Revenues\s+' + NUMBER, quarter)
        eps = value(r'Diluted earnings \(loss\) per share \(EPS\)\s+' + NUMBER, quarter)
    elif spec['adapter'] == 'arm-shareholder-letter-v1':
        if 'Arm Holdings plc' not in all_text:
            raise ReviewRequired('issuer_mismatch')
        summary = [p for p in pages if 'GAAP Non-GAAP (1) Q2 FYE' in p and 'Key Financial and Operating Metrics' in p]
        income = [p for p in pages if 'Condensed Consolidated Income Statements' in p and 'Weighted average ordinary shares outstanding' in p]
        if len(summary) != 1 or len(income) != 1:
            raise ReviewRequired('missing_quarterly_gaap_statements')
        period = datetime.fromisoformat(spec['period_end'])
        period_label = period.strftime('%B ') + str(period.day) + period.strftime(', %Y')
        fy = str(spec['fiscal_year'])[-2:]
        if (spec['fiscal_quarter'] != 2 or 'Q2 FYE'+fy not in summary[0]
            or 'three months ended '+period_label not in summary[0]):
            raise NotPublished('fiscal_period_mismatch')
        if '(in millions, except where indicated) GAAP Non-GAAP (1) Q2 FYE'+fy not in summary[0]:
            raise ReviewRequired('gaap_column_or_unit_not_verified')
        revenue = value(r'Total revenue \(2\)\s+' + NUMBER, summary[0])
        eps = value(r'Diluted earnings \(loss\) per share \(\$\)\s+' + NUMBER, summary[0])
        if not income[0].startswith('Three Months Ended September 30, Six Months Ended September 30, '+str(period.year)+' '+str(period.year-1)):
            raise ReviewRequired('quarter_vs_ytd_not_verified')
        check_revenue = value(r'Total revenue\s+' + NUMBER, income[0])
        eps_section = income[0].split('Net income (loss) per share attributable to ordinary shareholders', 1)
        if len(eps_section) != 2:
            raise ReviewRequired('ordinary_share_basis_not_verified')
        check_eps = value(r'Diluted\s+' + NUMBER, eps_section[1].split('Weighted average', 1)[0])
        if (revenue, eps) != (check_revenue, check_eps):
            raise ReviewRequired('quarterly_gaap_crosscheck_failed')
    else:
        raise ReviewRequired('unsupported_adapter')
    if not revenue.is_finite() or revenue < 0 or not eps.is_finite():
        raise ReviewRequired('invalid_numeric_values')
    if spec['currency'] != 'USD' or spec['reporting_standard'] != 'US_GAAP' or not spec.get('basis_source'):
        raise ReviewRequired('unreviewed_reporting_basis')
    observations = []
    for metric, amount, unit, basis, methodology in (
        ('revenue', revenue, 'millions', 'not_applicable', 'consolidated_revenue'),
        ('reported_diluted_eps', eps, 'per_share', spec['share_basis'], 'reported_diluted_total_eps')):
        observations.append(dict(metric=metric, source_value=str(amount), source_unit=unit,
                                 currency='USD', decimal_places=max(0, -amount.as_tuple().exponent),
                                 reporting_standard='US_GAAP', share_basis=basis, methodology=methodology))
    return dict(**{k:spec[k] for k in ('ticker','cik','fiscal_year','fiscal_quarter','period_label','period_end')},
                correction_reason='Verified automated completion of prior date announcement',
                document=dict(document_type='earnings_release', source_url=receipt['url'],
                              linked_from=spec['url'], release_date=spec['release_date'],
                              verified_on=receipt['fetched_at'][:10], verification_method=METHOD,
                              source_version=PARSER_VERSION+':'+receipt['sha256'],
                              facts=json.dumps(dict(parser=PARSER_VERSION, source_sha256=receipt['sha256'],
                                                    basis_source=spec['basis_source'], receipt=receipt), sort_keys=True),
                              reporting_standard='US_GAAP', reporting_currency='USD', eps_share_basis=spec['share_basis']),
                observations=observations)
