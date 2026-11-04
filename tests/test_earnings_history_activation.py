"""Approval and exact E2D manifest gates without database access."""
from unittest.mock import Mock
import pytest
from app.database import activate_earnings_history as a, activate_earnings as b


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


def test_exact_history_scope():
    rows=a.seed();assert len(rows)==23
    assert sum(m['metric']=='revenue' for r in rows for m in r['observations'])==23
    assert sum(m['metric']=='reported_diluted_eps' for r in rows for m in r['observations'])==22
    assert len(a.manifest(rows)[a.TABLES[0]])==23


def test_rollback_document_is_frozen():
    assert a.ROLLBACK in a.artifacts()
    assert len(a.AFTER)==11 and a.AFTER['earnings_financial_documents']==6 and a.AFTER['earnings_financial_observations']==12
