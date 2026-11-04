"""Approval and exact E2D manifest gates without database access."""
from unittest.mock import Mock
import pytest
from app.database import activate_earnings_reports as a, activate_earnings as b


@pytest.mark.parametrize('target,token',[('wrong','hash'),('db','wrong')])
def test_approval_gate(target,token):
    c=Mock()
    with pytest.raises(ValueError,match='Explicit target'):a.apply(c,{'target_label':'db'},target,token)
    assert not c.mock_calls


@pytest.mark.parametrize('change',[{'version':2},{'ready_for_apply':False},{'artifacts':{}}])
def test_frozen_gate(change):
    c=Mock();plan={'target_label':'db','version':1,'ready_for_apply':True,'artifacts':a.artifacts(),**change}
    with pytest.raises(ValueError,match='Frozen artifacts'):a.apply(c,plan,'db',b.digest(plan))
    assert not c.mock_calls


def test_exact_manifest_scope_and_units():
    records=a.seed();manifest=a.manifest(records)
    assert [len(manifest[t]) for t in a.TABLES]==[27,46]
    assert len({d['event_id'] for d in manifest[a.TABLES[0]]})==27
    for ticker,currency,standard,scale in [('TSM','TWD','IFRS','1000000000'),('ASML','EUR','US_GAAP','1000000'),('NFLX','USD','US_GAAP','1000'),('LRCX','USD','US_GAAP','1000'),('PLTR','USD','US_GAAP','1000'),('CRWD','USD','US_GAAP','1000'),('MU','USD','US_GAAP','1000000')]:
        record=next(r for r in records if r['ticker']==ticker)
        doc=next(d for d in manifest[a.TABLES[0]] if d['cik']==record['cik'])
        revenue=next(o for o in manifest[a.TABLES[1]] if o['document_id']==doc['document_id'] and o['metric']=='revenue')
        assert revenue['currency']==currency and revenue['reporting_standard']==standard
        assert a.reports.Decimal(revenue['actual'])==a.reports.Decimal(revenue['source_value'])*a.reports.Decimal(scale)
    assert all(o['version']=='1' and o['supersedes_id'] is None for o in manifest[a.TABLES[1]])


def test_rollback_document_is_frozen():
    assert a.ROLLBACK in a.artifacts()
    assert len(a.AFTER)==10 and a.AFTER['earnings_financial_documents']==6 and a.AFTER['earnings_financial_observations']==12
