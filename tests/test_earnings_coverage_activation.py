"""Approval gates reject invalid plans before touching SQL."""
from unittest.mock import Mock
import pytest
from app.database import activate_earnings_coverage as a, activate_earnings as b


@pytest.mark.parametrize('target,token',[('wrong','hash'),('db','wrong')])
def test_approval_gate(target,token):
    connection=Mock()
    with pytest.raises(ValueError,match='Explicit target'):
        a.apply(connection,{'target_label':'db'},target,token)
    assert not connection.mock_calls


@pytest.mark.parametrize('change',[{'version':2},{'ready_for_apply':False},{'artifacts':{}}])
def test_frozen_gate(change):
    connection=Mock()
    plan={'target_label':'db','version':1,'ready_for_apply':True,'artifacts':a.artifacts(),**change}
    with pytest.raises(ValueError,match='Frozen artifacts'):
        a.apply(connection,plan,'db',b.digest(plan))
    assert not connection.mock_calls


def test_seed_scope():
    rows=a.seed()
    assert len(rows)==27 and len({r['cik'] for r in rows})==27
    assert len(a.coverage.registry())==53
    assert a.AFTER['earnings_financial_documents']==6
    assert a.AFTER['earnings_financial_observations']==12
