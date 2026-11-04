"""Manual, keyless public Market Cap collection. No database connection.

Run: python -m app.earnings_market_cap_public refresh
TGMCharts first, dated DeltaScreener CSV for gaps. No scheduler/startup hook.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone, date
from decimal import Decimal
from pathlib import Path
import httpx
from app import earnings_market_cap_cache as cache
from app.earnings import identity

PILOT = ('AAPL', 'NVDA', 'MSFT', 'AMZN', 'GOOGL', 'AMD', 'TSM', 'ASML')
TGM = 'https://tgmcharts.com/api/v1/summary/'
DELTA = 'https://deltascreener.com/data'


class DataGap(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def reviewed():
    from app.earnings_coverage import registry
    items = json.loads(cache.REVIEW.read_text(encoding='utf-8'))
    known = registry()
    if len(items) != 53 or len({r['cik'] for r in items}) != 53:
        raise ValueError('53 unique reviewed issuers required')
    for r in items:
        if known[r['cik']]['ticker'] != r['ticker']:
            raise ValueError('Registry changed; identity review required')
    return items


def amount(value):
    if isinstance(value, (float, bool)) or value is None:
        raise DataGap('missing_or_invalid_decimal')
    v = Decimal(value)
    if not v.is_finite() or v <= 0:
        raise DataGap('missing_or_invalid_decimal')
    return format(v, 'f')


def record(item, value, as_of, provider, name, exchange, receipt, basis):
    if not item['scope_reviewed']:
        raise DataGap(item['gap_reason'])
    stamp = date.fromisoformat(as_of)
    retrieved = datetime.fromisoformat(receipt['retrieved_at'])
    if not 0 <= (retrieved.date() - stamp).days <= (45 if provider == 'DeltaScreener' else 7):
        raise DataGap('stale_or_future_snapshot')
    return dict(cik=item['cik'], company_id=identity(item['cik']), ticker=item['ticker'],
                source_symbol=item['tgm_symbol' if provider == 'TGMCharts' else 'delta_symbol'],
                source_name=name, exchange=exchange, market_cap_usd=amount(value), currency='USD',
                as_of=as_of, retrieved_at=receipt['retrieved_at'], provider=provider,
                source_url=cache.SOURCES[provider], response_sha256=receipt['sha256'],
                measurement_basis=basis, issuer_scope='whole_issuer_provider_reported',
                identity_basis=item['basis'], source_document=receipt['url'])


def tgm_record(item, payload, receipt):
    if payload['symbol'] != item['tgm_symbol'] or payload['name'] != item['tgm_name']:
        raise DataGap('tgm_identity_changed')
    if payload['currency'] != 'USD':
        raise DataGap('non_usd')
    classification = payload['classification']
    if classification['flags']['adr'] is not False or classification['flags']['fund'] is not False:
        raise DataGap('adr_or_unclassified_scope')
    if classification['type'] not in ('operating', 'bank', 'insurer', 'capital_markets'):
        raise DataGap('not_reviewed_common_equity')
    price = payload['price']
    # Summary also contains a delayed quote. lastCloseDate alone cannot date
    # a different quote-based cap. Do not re-date it or calculate our own cap.
    if price.get('latestPrice') is not None and price['latestPrice'] != price['lastClose']:
        raise DataGap('market_cap_date_ambiguous_with_delayed_quote')
    return record(item, price['marketCap'], price['lastCloseDate'], 'TGMCharts', payload['name'],
                  item['delta_exchange'], receipt, 'EOD summary; latest quote absent or equal to official last close; source lastCloseDate')


def delta_rows(body):
    rows = {}
    reader = csv.DictReader(io.StringIO(body.decode('utf-8-sig')))
    if not {'ticker', 'name', 'exchange', 'mktCap'}.issubset(reader.fieldnames or []):
        raise DataGap('invalid_csv_columns')
    for row in reader:
        if row['ticker'] in rows:
            raise DataGap('duplicate_csv_symbol')
        rows[row['ticker']] = row
    return rows


def delta_record(item, rows, receipt):
    row = rows.get(item['delta_symbol'])
    if not row:
        raise DataGap('missing_csv_symbol')
    if row['name'] != item['delta_name'] or row['exchange'] != item['delta_exchange']:
        raise DataGap('delta_identity_or_exchange_changed')
    match = re.fullmatch(r'https://deltascreener.com/data/us-stock-universe-(\d{4}-\d{2}-\d{2})\.csv', receipt['url'])
    if not match:
        raise DataGap('dated_csv_required')
    return record(item, row['mktCap'], match[1], 'DeltaScreener', row['name'], row['exchange'], receipt,
                  'Monthly dated company snapshot in USD; prices are last close before file stamp. As-of is snapshot date, not exact quote timestamp.')


class PublicClient:
    def __init__(self, capture_dir, *, transport=None, sleeper=time.sleep, budget=120):
        self.root = Path(capture_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(timeout=25, trust_env=False, follow_redirects=False, transport=transport)
        self.sleep = sleeper
        self.count = 0
        self.budget = min(budget, 120)

    def close(self):
        self.client.close()

    def get(self, url):
        if not (re.fullmatch(r'https://tgmcharts.com/api/v1/summary/[A-Z0-9.-]{1,10}', url) or
                re.fullmatch(r'https://deltascreener.com/data(?:/us-stock-universe-\d{4}-\d{2}-\d{2}\.csv)?', url)):
            raise DataGap('unapproved_endpoint')
        key = hashlib.sha256(url.encode()).hexdigest()
        body_path = self.root / (key + '.body')
        meta_path = self.root / (key + '.json')
        if body_path.exists() and meta_path.exists():
            receipt = json.loads(meta_path.read_text())
            elapsed = (datetime.fromisoformat(now()) - datetime.fromisoformat(receipt['retrieved_at'])).total_seconds()
            body = body_path.read_bytes()
            if 0 <= elapsed < 3600 and receipt['sha256'] == hashlib.sha256(body).hexdigest():
                return body, receipt
        for attempt in range(3):
            if self.count >= self.budget:
                raise DataGap('request_budget_exhausted')
            if self.count:
                self.sleep(1.1)
            self.count += 1
            try:
                with self.client.stream('GET', url) as response:
                    if response.status_code == 429 or response.status_code >= 500:
                        delay = response.headers.get('Retry-After', str(2 ** (attempt + 1)))
                        if attempt == 2 or not delay.isdigit() or int(delay) > 60:
                            raise DataGap('provider_limited_or_unavailable')
                        self.sleep(max(2 ** (attempt + 1), int(delay)))
                        continue
                    if response.status_code != 200:
                        raise DataGap('provider_http_' + str(response.status_code))
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 3000000:
                            raise DataGap('response_too_large')
            except httpx.HTTPError:
                raise DataGap('provider_connection_failed') from None
            receipt = dict(url=url, retrieved_at=now(), sha256=hashlib.sha256(body).hexdigest())
            body_path.write_bytes(body)
            meta_path.write_text(json.dumps(receipt))
            return bytes(body), receipt
        raise DataGap('provider_unavailable')


def build(items, summaries, delta=None):
    records, gaps = [], []
    rows = delta_rows(delta[0]) if delta else {}
    for item in items:
        reasons = []
        result = None
        if item['ticker'] in summaries:
            body, receipt = summaries[item['ticker']]
            try:
                result = tgm_record(item, json.loads(body, parse_float=Decimal, parse_int=Decimal), receipt)
            except (DataGap, ValueError, TypeError, KeyError, ArithmeticError) as exc:
                reasons.append(str(exc) if isinstance(exc, DataGap) else 'invalid_tgm_response')
        else:
            reasons.append('tgm_unavailable')
        if result is None and delta:
            try:
                result = delta_record(item, rows, delta[1])
            except (DataGap, ValueError, TypeError, KeyError, ArithmeticError) as exc:
                reasons.append(str(exc) if isinstance(exc, DataGap) else 'invalid_delta_response')
        if result:
            records.append(result)
        else:
            gaps.append(dict(cik=item['cik'], ticker=item['ticker'], reasons=reasons))
    return dict(version=1, synthetic=False, generated_at=now(), records=records, gaps=gaps)


def publish(bundle, destination=cache.CACHE):
    cache.validate(bundle, datetime.now(timezone.utc).date())
    if not bundle['records']:
        raise DataGap('no_verified_values_keep_existing_cache')
    destination = Path(destination)
    if destination.exists():
        try:
            old = json.loads(destination.read_text(encoding='utf-8'))
            stable = lambda r: {k:v for k,v in r.items() if k != 'retrieved_at'}
            ordered=lambda rows:sorted([stable(r) for r in rows],key=lambda r:r['cik'])
            if ordered(old['records']) == ordered(bundle['records']) and old['gaps'] == bundle['gaps']:
                return 'unchanged'
        except (ValueError,KeyError,TypeError):
            pass
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement: concurrent GET sees either complete old or new cache.
    handle, temporary = tempfile.mkstemp(prefix='.cap-', dir=destination.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as output:
            json.dump(bundle, output, indent=2)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return 'updated'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['refresh'])
    parser.add_argument('--scope', choices=['pilot', 'all'], default='all')
    parser.add_argument('--if-due', action='store_true', help='For a future external task: once per UTC day, on the supplied earnings date')
    parser.add_argument('--event-date', type=date.fromisoformat)
    args = parser.parse_args()
    stamp=datetime.fromisoformat(now()).date()
    if args.if_due:
        if args.event_date!=stamp:
            print(json.dumps({'outcome':'not_an_earnings_day'}));return
        attempt=cache.CACHE.parent/'attempts'/(stamp.isoformat()+'.json')
        attempt.parent.mkdir(parents=True,exist_ok=True)
        try:
            with attempt.open('x') as output:json.dump({'day':stamp.isoformat()},output)
        except FileExistsError:
            print(json.dumps({'outcome':'already_attempted_today'}));return
    client = PublicClient(cache.CACHE.parent / 'responses')
    items = [r for r in reviewed() if args.scope == 'all' or r['ticker'] in PILOT]
    summaries = {}
    try:
        for item in items:
            try:
                summaries[item['ticker']] = client.get(TGM + item['tgm_symbol'])
            except DataGap as exc:
                if str(exc) in ('provider_http_401', 'provider_http_403', 'provider_limited_or_unavailable', 'request_budget_exhausted'):
                    break
        delta = None
        preliminary = build(items, summaries)
        previous=cache.read(stamp)
        monthly=[r for r in previous.values() if r['provider']=='DeltaScreener']
        # The scheduled form only checks monthly data near expiry; manual
        # refresh remains explicit. Original measurement dates never change.
        delta_state=cache.CACHE.parent/'delta-attempt.json'
        last_delta=json.loads(delta_state.read_text()) if delta_state.exists() else {}
        delta_due=not monthly or max((stamp-date.fromisoformat(r['as_of'])).days for r in monthly)>=38
        recent=last_delta.get('day') and (stamp-date.fromisoformat(last_delta['day'])).days<3
        if preliminary['gaps'] and (not args.if_due or delta_due and not recent):
            delta_state.write_text(json.dumps({'day':stamp.isoformat()}))
            try:
                page, _ = client.get(DELTA)
                links = re.findall(rb'us-stock-universe-(\d{4}-\d{2}-\d{2})\.csv', page)
                if not links:
                    raise DataGap('dated_csv_link_missing')
                stamp = max(links).decode('ascii')
                delta = client.get(DELTA + '/us-stock-universe-' + stamp + '.csv')
            except DataGap:
                pass
        result = build(items, summaries, delta)
        selected={r['cik'] for r in result['records']}
        # Keep still-valid prior data when a provider has no newer snapshot.
        for item in items:
            r=previous.get(item['cik'])
            if r and item['cik'] not in selected:
                result['records'].append(r)
                result['gaps']=[g for g in result['gaps'] if g['cik']!=item['cik']]
        result['records'].sort(key=lambda r:r['cik'])
        outcome=publish(result)
        print(json.dumps({'outcome':outcome,'values': len(result['records']), 'gaps': result['gaps'], 'requests': client.count}))
    finally:
        client.close()


if __name__ == '__main__':
    main()
