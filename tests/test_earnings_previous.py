import copy
import json
import pytest
from app import earnings_previous as p, earnings_history as h


def metric(value='0', **kwargs):
    return dict(metric='reported_diluted_eps', actual=value, currency='USD', reporting_standard='US_GAAP',
                share_basis='common_share', methodology='reported_diluted_total_eps', source_url='https://issuer.test/report', **kwargs)


def event(year=2027, quarter=1, company='issuer', **kwargs):
    return dict(company_id=company, cik=company, fiscal_year=year, fiscal_quarter=quarter,
                period_label=f'Q{quarter} FY{year}',period_end=None, **kwargs)


@pytest.fixture(autouse=True)
def absent_history(monkeypatch):
    monkeypatch.setattr(h,'load',lambda c:([],'not_activated'))


@pytest.mark.parametrize('quarter,expected',[(1,(2026,4)),(2,(2027,1)),(3,(2027,2)),(4,(2027,3))])
def test_fiscal_predecessor(quarter,expected):
    assert p.previous_quarter(2027,quarter)==expected


@pytest.mark.parametrize('value',['0','-2.16'])
def test_future_null_current_separate_previous_and_no_forecasts(value):
    prior=event(2026,4,reported_eps_actual=metric(value))
    future=event()
    p.attach(None,[prior,future])
    assert future['current_eps_actual'] is None and future['previous_eps_actual']['actual']==value
    assert future['previous_period']['period_label']=='Q4 FY2026'
    assert all(future[k] is None for k in future if k.endswith('_forecast'))


@pytest.mark.parametrize('change',[{'currency':'EUR'},{'reporting_standard':'IFRS'},{'share_basis':'ADR'},{'methodology':'basic_eps'},{'methodology':'non_gaap'},{'methodology':'continuing_only'}])
def test_incompatible_eps_never_projected(change):
    prior=event(2026,4,reported_eps_actual={**metric(),**change})
    current=event(reported_eps_actual=metric('1'))
    p.attach(None,[prior,current])
    assert current['previous_eps_actual'] is None


def test_no_nearest_fallback_or_cross_issuer_or_cik():
    current=event()
    wrong_cik={**event(2026,4), 'cik':'other','reported_eps_actual':metric()}
    p.attach(None,[event(2026,3,reported_eps_actual=metric()),event(2026,4,'other',reported_eps_actual=metric()),wrong_cik,current])
    assert current['previous_eps_actual'] is None and current['previous_period'] is None


def test_pending_predecessor_does_not_inherit_obsolete_financial_history():
    prior=event(2026,4,reported_eps_actual=None,financial_history=[metric('9')])
    current=event(reported_eps_actual=None)
    p.attach(None,[prior,current])
    assert current['previous_eps_actual'] is None


def test_event_snapshot_wins_over_historical_store(monkeypatch):
    historical=event(2026,4,reported_eps_actual=metric('9'))
    monkeypatch.setattr(h,'load',lambda c:([historical],'available'))
    prior=event(2026,4,reported_eps_actual=None)
    current=event()
    p.attach(None,[prior,current])
    assert current['previous_eps_actual'] is None
    assert current['previous_history']==[historical]


def test_declared_current_basis_applies_even_before_actual():
    prior=event(2026,4,reported_eps_actual=metric())
    current=event(report_documents=[{'reporting_currency':'TWD','reporting_standard':'IFRS','eps_share_basis':'ordinary_share'}])
    p.attach(None,[prior,current]);assert current['previous_eps_actual'] is None


def test_old_e2b_explicit_gaap_model_is_compatible():
    old=metric('-2.16');old.pop('reporting_standard');old.pop('share_basis');old['methodology']='gaap_diluted'
    prior=event(2026,4,gaap_diluted_eps_actual=old)
    current=event(reported_eps_actual=metric())
    p.attach(None,[prior,current]);assert current['previous_eps_actual']==old


def test_reviewed_23_issuer_scope_scaling_and_split_gap():
    records=json.loads(h.DATA.read_text(encoding='utf-8'))
    assert len(records)==23 and sum(len(r['observations']) for r in records)==45
    for record in records:
        validated=h.validate(record)
        assert all('actual' in m for m in validated['observations'])
        bad=copy.deepcopy(record);bad['observations'][0]['source_value']='999'
        with pytest.raises(ValueError):h.validate(bad)
    crowd=next(r for r in records if r['ticker']=='CRWD')
    assert [m['metric'] for m in crowd['observations']]==['revenue']
    tsm=h.validate(next(r for r in records if r['ticker']=='TSM'))
    assert tsm['observations'][0]['actual']=='1270380000000.00'


def test_history_normal_database_is_rejected_before_sql():
    class Connection:
        class info:dbname='macrolens'
        def execute(self,*args):raise AssertionError('SQL attempted')
    with pytest.raises(ValueError):h.initialize_isolated(Connection())
    with pytest.raises(ValueError):h.import_records(Connection(),[])
