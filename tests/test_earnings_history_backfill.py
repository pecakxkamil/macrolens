"""Offline gates for the separately reviewed E2E extension."""
import copy
import json
import pytest
from app import earnings_history as history
from integrations.earnings_history_backfill import activation as a


def test_exact_seven_reports_and_existing_importer_does_not_change():
    before=history.DATA
    rows=a.records()
    assert history.DATA==before
    values={r['ticker']:{m['metric']:m['actual'] for m in r['observations']} for r in rows}
    assert values=={'ARM':{'revenue':'1289000000','reported_diluted_eps':'0.25'},'QCOM':{'revenue':'9947000000','reported_diluted_eps':'1.87'},'PANW':{'revenue':'3410000000','reported_diluted_eps':'-0.35'},'SNOW':{'revenue':'1546793000','reported_diluted_eps':'-0.55'},'NVDA':{'revenue':'68127000000','reported_diluted_eps':'1.76'},'AMZN':{'revenue':'181519000000','reported_diluted_eps':'2.78'},'INTC':{'revenue':'13577000000'}}
    assert len(history.DATA.read_text())>0


def test_prepared_records_keep_exact_source_units_and_share_basis():
    rows={r['ticker']:r for r in a.records()}
    assert rows['ARM']['observations'][1]['share_basis']=='ordinary_share'
    assert rows['SNOW']['observations'][0]['source_unit']=='thousands'
    assert all(r['reporting_standard']=='US_GAAP' for r in rows.values())
    assert all(r['document_type']=='earnings_release' for r in rows.values())


@pytest.mark.parametrize('change',[lambda r:r[0].update(fiscal_quarter=2),lambda r:r[0].update(reporting_standard='non_GAAP'),lambda r:r[0]['observations'][1].update(share_basis='ADR'),lambda r:r[0]['observations'][1].update(methodology='adjusted_eps'),lambda r:r.append(copy.deepcopy(r[0]))])
def test_bad_reviewed_ledger_is_rejected(monkeypatch,tmp_path,change):
    data=json.loads(a.LEDGER.read_text());change(data);path=tmp_path/'review.json';path.write_text(json.dumps(data));monkeypatch.setattr(a,'LEDGER',path)
    with pytest.raises(ValueError):a.records()


@pytest.mark.parametrize('target,approval',[('wrong','wrong'),('localhost:5432/macrolens','old-f1-approval')])
def test_unapproved_normal_apply_never_reaches_sql(target,approval):
    with pytest.raises(ValueError,match='New exact'):a.apply(object(),{'target_label':'localhost:5432/macrolens'},target,approval,{})


def test_no_ddl_or_automatic_runtime_activation():
    assert not a.CONDITIONS['ddl'] and a.CONDITIONS['insert_reports']==7
    assert a.TABLE=='earnings_historical_reports'
    assert not a.CONDITIONS['changes_to_existing_rows']
