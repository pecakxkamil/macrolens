"""Offline E2C contracts; no provider clients."""
import copy
import json
import pytest
from app import earnings_coverage as c, earnings as e

def records(): return json.loads(c.DATA.read_text(encoding='utf-8'))

def test_registry_is_issuers_not_tickers():
    rows=c.registry()
    assert len(rows)==53
    assert rows['0001652044']['aliases']==['GOOGL','GOOG']
    assert rows['0001067983']['aliases']==['BRK-B','BRK.B']
    assert len({e.identity(k) for k in rows})==53
    assert all(r['identity_source'].startswith('https://www.sec.gov/') for r in rows.values())

@pytest.mark.parametrize('record',records(),ids=lambda r:r['ticker'])
def test_official_dates_keep_precision_and_provenance(record):
    row=c.validate(record)
    assert row['release']['source_local_date']
    if row['release']['precision']=='date_only':
        assert row['release']['scheduled_at_utc'] is None and row['release']['expected_time_utc'] is None
    assert row['release']['evidence']['verified_on']=='2026-11-03'
    assert 'revenue_actual' not in row

@pytest.mark.parametrize('change',[
    lambda r:r.update(cik='0000000000'),lambda r:r.update(ticker='MSFT'),
    lambda r:r.update(fiscal_year=True),lambda r:r.update(fiscal_quarter=1),
    lambda r:r.update(period_label='Q1 2027'),lambda r:r.update(period_end='2027-01-01'),
    lambda r:r['release']['evidence'].update(cik='0000789019'),
    lambda r:r['release']['evidence'].update(source_url='https://investing.com/earnings'),
    lambda r:r['release']['evidence'].update(source_url='https://www.apple.com@evil.example/x'),
    lambda r:r['release']['evidence'].update(verification_method='inferred'),
    lambda r:r['release'].update(precision='exact'),lambda r:r.update(revenue_actual=1),
])
def test_invalid_metadata_rejected_before_writes(change):
    row=copy.deepcopy(records()[0]);change(row)
    with pytest.raises((ValueError,KeyError,TypeError)):c.validate(row)

def test_no_generated_unknown_event_or_foreign_timestamp():
    row=copy.deepcopy(records()[0]);row['release']=row['call']={'date_status':'unknown','precision':'unknown'}
    with pytest.raises(ValueError,match='Register the issuer'):c.validate(row)
    foreign=next(r for r in records() if r['ticker']=='ASML')
    assert c.registry()[foreign['cik']]['issuer_timezone']=='Europe/Amsterdam'
    assert c.validate(foreign)['release']['scheduled_at_utc'] is None
    foreign['release'].update(precision='exact',source_local_time='07:00',source_timezone='Europe/Amsterdam')
    foreign['release']['timezone_label_raw']='Europe/Amsterdam'
    assert c.validate(foreign)['release']['scheduled_at_utc']=='2026-10-14T05:00:00+00:00'

def test_new_import_does_not_expand_pilot_guard():
    assert set(e.PILOTS)=={'0001045810','0001018724','0000050863'}
    with pytest.raises(ValueError,match='pilot allowlist'):e.validate(records()[0])

def test_exact_call_is_separate_from_after_close_release():
    row=c.validate(next(r for r in records() if r['ticker']=='QCOM'))
    assert row['release']['scheduled_at_utc'] is None
    assert row['call']['scheduled_at_utc']=='2026-11-04T21:45:00+00:00'
