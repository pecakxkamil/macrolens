import json
from copy import deepcopy
import pytest
from app import earnings_market_cap as cap


def snapshot():
    return dict(cik='0000320193',market_cap_usd='850400000000.123456789',currency='USD',as_of='2026-11-03',measured_at=None,
                source_url='https://example.invalid/synthetic-market-cap',source_id='synthetic',source_version='test-1',
                method='provider_reported_issuer_equity',issuer_scope='whole_issuer_all_classes',basis_evidence='Synthetic whole issuer, all classes, not ADR-only or EV',
                access_evidence='Owned test fixture; no real market data',verified_on='2026-11-04')


def approve(monkeypatch,tmp_path,record):
    path=tmp_path/'synthetic.json';path.write_text(json.dumps([record]));monkeypatch.setattr(cap,'DATA',path)


def test_no_production_source_or_valuation_is_invented():
    assert json.loads(cap.DATA.read_text())==[]
    with pytest.raises(ValueError):cap.validate(snapshot())


def test_exact_decimal_direct_issuer_snapshot(monkeypatch,tmp_path):
    record=snapshot();approve(monkeypatch,tmp_path,record)
    assert cap.validate(record)['market_cap_usd']=='850400000000.123456789'


@pytest.mark.parametrize('field,value',[
    ('market_cap_usd','0'),('market_cap_usd','-1'),('market_cap_usd','NaN'),('market_cap_usd','Infinity'),('market_cap_usd',850.4),
    ('currency','TWD'),('method','enterprise_value'),('method','price_times_diluted_weighted_average_shares'),
    ('issuer_scope','ADR_only'),('issuer_scope','class_A_only'),('issuer_scope','public_float'),
    ('access_evidence',''),('basis_evidence',''),('as_of','2099-01-01'),('source_url','http://invalid.test'),
    ('measured_at','2026-11-03T16:00:00'),('measured_at','2026-11-02T16:00:00+00:00')])
def test_invalid_basis_dates_currency_and_rights(monkeypatch,tmp_path,field,value):
    record=snapshot();record[field]=value;approve(monkeypatch,tmp_path,record)
    with pytest.raises((ValueError,TypeError)):cap.validate(record)


def test_normal_database_rejected_before_sql():
    class Connection:
        class info:dbname='macrolens'
        def execute(self,*args):raise AssertionError('Normal write attempted')
    with pytest.raises(ValueError):cap.initialize_isolated(Connection())
    with pytest.raises(ValueError):cap.import_records(Connection(),[])


def test_missing_and_partial_store():
    class Connection:
        def __init__(self,row):self.row=row
        def execute(self,*args):return self
        def fetchone(self):return self.row
    events=[{'company_id':'one','cik':'0000000001'}]
    assert cap.attach(Connection((None,None)),events)[0]['market_cap_usd'] is None
    assert events[0]['market_cap_status']=='not_activated'
    with pytest.raises(ValueError):cap.attach(Connection(('table',None)),events)
