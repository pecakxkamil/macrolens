"""Optional local public-data cache. Reads only; never HTTP or PostgreSQL writes."""
import json
import re
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path
from app.earnings import identity

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data/raw/earnings-market-cap-cache/current.json'
REVIEW = ROOT / 'config/earnings_market_cap_public_identity.json'
SOURCES = {'TGMCharts': 'https://tgmcharts.com', 'DeltaScreener': 'https://deltascreener.com/data'}


def validate(bundle, today):
    if bundle['version'] != 1 or bundle.get('synthetic') is not False:
        raise ValueError('Public live cache required')
    generated = datetime.fromisoformat(bundle['generated_at'])
    if generated.tzinfo is None or generated.astimezone(timezone.utc).date() > today:
        raise ValueError('Invalid cache generation time')
    reviewed = {r['cik']: r for r in json.loads(REVIEW.read_text(encoding='utf-8'))}
    records, seen = {}, set()
    for r in bundle['records']:
        check = reviewed[r['cik']]
        if r['cik'] in seen or not check['scope_reviewed'] or r['company_id'] != identity(r['cik']) or r['ticker'] != check['ticker']:
            raise ValueError('Duplicate, ambiguous or wrong issuer')
        seen.add(r['cik'])
        provider = r['provider']
        expected_symbol = check['tgm_symbol' if provider == 'TGMCharts' else 'delta_symbol']
        expected_name = check['tgm_name' if provider == 'TGMCharts' else 'delta_name']
        if provider not in SOURCES or r['source_url'] != SOURCES[provider] or r['source_symbol'] != expected_symbol or r['source_name'] != expected_name:
            raise ValueError('Unreviewed public source identity')
        if r['exchange'] != check['delta_exchange'] or r['issuer_scope'] != 'whole_issuer_provider_reported':
            raise ValueError('Unreviewed exchange or share scope')
        value = r['market_cap_usd']
        if not isinstance(value, str) or not re.fullmatch(r'\d+(\.\d+)?', value) or not Decimal(value).is_finite() or Decimal(value) <= 0 or r['currency'] != 'USD':
            raise ValueError('Invalid USD decimal')
        as_of = date.fromisoformat(r['as_of'])
        retrieved = datetime.fromisoformat(r['retrieved_at'])
        if retrieved.tzinfo is None or not as_of <= retrieved.astimezone(timezone.utc).date() <= generated.astimezone(timezone.utc).date():
            raise ValueError('Invalid source/retrieval dates')
        if not re.fullmatch('[0-9a-f]{64}', r['response_sha256']) or not r['measurement_basis']:
            raise ValueError('Missing provenance')
        # Date remains a measurement/snapshot date, never a retrieval date.
        if 0 <= (today - as_of).days <= (45 if provider == 'DeltaScreener' else 7):
            records[r['cik']] = r
    return records


def read(today):
    try:
        if CACHE.stat().st_size > 1000000:
            return {}
        return validate(json.loads(CACHE.read_text(encoding='utf-8')), today)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        # Missing, malformed or partial cache must not break Calendar.
        return {}


def attach(events, today):
    cached = read(today)
    for event in events:
        # A verified fresh SQL snapshot always wins, even if cache is newer.
        if event['market_cap_status'] == 'verified_snapshot':
            continue
        r = cached.get(event['cik'])
        if r is None or r['company_id'] != event['company_id']:
            continue
        event.update(market_cap_usd=r['market_cap_usd'], market_cap_as_of=r['as_of'],
                     market_cap_source=r['source_url'], market_cap_provider=r['provider'],
                     market_cap_status='verified_snapshot', market_cap_snapshot=dict(r))
    return events
