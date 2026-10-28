"""BLS PPI definitions, SA/NSA pairing and independent publication availability."""
import copy
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from app.analytics.calendar_readings import bind_events, value_at
from app.analytics.features import calculate_features
from app.analytics.ppi_measures import (PPI_SERIES, PPI_PAIRS, PPI_NAMES, PPI_BASES,
    NEW_PPI_SERIES, validate_metadata, expand_ppi_evidence)
from app.database.sync_series import load_series_config
from tests.test_calendar_agenda import event


def data():
    result = {}
    for index, sid in enumerate(PPI_SERIES):
        result[sid] = [dict(observation_date=str(d.date()),value=100+index*20+i*(index+1),
                            vintage_date='2026-10-28',source='fred_snapshot')
                       for i,d in enumerate(pd.date_range('2025-04-01','2026-09-01',freq='MS'))]
    return result


def evidence(day='2026-10-15',period='2026-09-01'):
    return {'periods':[dict(release_id=46,series_ids=['PPIFIS'],release_date=day,
        reference_period=period,source_url='https://www.bls.gov/schedule/news_release/ppi.htm',
        retrieved_at='2026-10-01T12:00:00Z',binding_method='bls_release_table')]}


def bind(current=None,updates=None,proof=None,day='2026-10-15'):
    return bind_events([event(46,day,PPI_SERIES)],{},data() if current is None else current,
        datetime(2026,10,28,tzinfo=timezone.utc),evidence() if proof is None else proof,
        dict.fromkeys(PPI_SERIES,'2026-10-15 09:21:00-05') if updates is None else updates)[0]


@pytest.mark.parametrize('sid',PPI_SERIES)
def test_exact_series_metadata_base_and_sa_nsa_definition(sid):
    config=load_series_config()
    assert config[sid]['name']==PPI_NAMES[sid] and config[sid]['frequency']=='monthly'
    if sid!='PPIFIS':
        assert config[sid]['fred_units']==f'Index {PPI_BASES[sid]}=100'
        assert config[sid]['transformations']==['mom' if sid in PPI_PAIRS else 'yoy']
    metadata=dict(id=sid,title=PPI_NAMES[sid],units=f'Index {PPI_BASES[sid]}=100',frequency='Monthly',
                  seasonal_adjustment='Seasonally Adjusted' if sid in PPI_PAIRS else 'Not Seasonally Adjusted')
    validate_metadata(sid,metadata)
    for key,wrong in [('units','Index 1982=100'),('frequency','Quarterly'),('title','PPI finished goods'),
                      ('seasonal_adjustment','Not Seasonally Adjusted' if sid in PPI_PAIRS else 'Seasonally Adjusted')]:
        with pytest.raises(ValueError):validate_metadata(sid,{**metadata,key:wrong})


def test_one_event_three_primary_rows_with_independent_nsa_yearly_context():
    result=bind();rows=result['measures']
    assert [m['series_id'] for m in rows]==list(PPI_PAIRS)
    for row in rows:
        annual=row['year_over_year'];assert annual['series_id']==PPI_PAIRS[row['series_id']]
        assert annual['feature_name']=='yoy' and row['feature_name']=='mom'
        assert annual['seasonal_adjustment']=='Not Seasonally Adjusted'
        assert row['seasonal_adjustment']=='Seasonally Adjusted'
        for m in [row,annual]:
            assert m['reference_period']=='2026-09-01' and m['previous_period']=='2026-08-01'
            assert m['actual'] is not None and m['previous'] is not None
            assert m['unit']=='percent' and m['forecast'] is None and m['consensus_status']=='not_integrated'
            assert m['data_version']=='current_vintage' and m['previous_kind']=='previous_period'
    assert 'trade services remain included' in rows[1]['definition']
    assert 'wholesale and retail margins' in rows[2]['definition']


@pytest.mark.parametrize('sid',sorted(NEW_PPI_SERIES))
def test_exact_month_ratios_use_one_series_and_its_own_base(sid):
    points=data()[sid];feature='mom' if sid in PPI_PAIRS else 'yoy'
    current=points[-1]['value'];prior=points[-2 if feature=='mom' else -13]['value']
    actual=value_at(sid,feature,points,'2026-09-01','monthly')
    assert actual==pytest.approx(100*(current/prior-1))
    scaled=[dict(p,value=p['value']*5) for p in points]
    assert value_at(sid,feature,scaled,'2026-09-01','monthly')==pytest.approx(actual)


@pytest.mark.parametrize('sid',['PPIFES','PPICOR'])
@pytest.mark.parametrize('fault',['missing','zero','negative','vintage','source'])
def test_missing_invalid_or_mixed_denominator_stays_empty(sid,fault):
    current=data();feature='mom' if sid=='PPIFES' else 'yoy'
    index=-2 if feature=='mom' else -13
    if fault=='missing':current[sid].pop(index)
    elif fault=='zero':current[sid][index]['value']=0
    elif fault=='negative':current[sid][index]['value']=-1
    elif fault=='vintage':current[sid][index]['vintage_date']='2026-10-27'
    else:current[sid][index]['source']='alfred'
    assert value_at(sid,feature,current[sid],'2026-09-01','monthly') is None


@pytest.mark.parametrize('sid',['PPIFES','WPSFD49116','PPIFID','PPICOR','WPUFD49116'])
def test_stored_transform_does_not_compress_missing_calendar_months(sid):
    feature='mom' if sid in PPI_PAIRS else 'yoy'
    frame=pd.DataFrame(data()[sid])
    frame=frame[frame.observation_date!='2026-08-01']
    result=calculate_features(sid,frame,[feature])
    assert '2026-09-01' not in result.observation_date.astype(str).tolist()


def test_partial_provider_update_does_not_fill_other_series_or_sa_from_nsa():
    current=data();current['PPIFES'].pop()
    result=bind(current=current)['measures']
    assert result[1]['actual'] is None and result[1]['year_over_year']['actual'] is not None
    assert result[2]['actual'] is not None
    updates=dict.fromkeys(PPI_SERIES,'2026-10-15 09:21:00-05');updates['WPUFD49116']='2026-10-14 09:21:00-05'
    result=bind(updates=updates)['measures']
    assert result[2]['actual'] is not None and result[2]['year_over_year']['actual'] is None


def test_new_timestamp_without_new_snapshot_or_confirmed_period_is_not_an_actual():
    current=data()
    for point in current['PPIFES']:point['vintage_date']='2026-10-14'
    assert bind(current=current)['measures'][1]['actual'] is None
    assert all(m['actual'] is None for m in bind(proof={})['measures'][1:])
    updates=dict.fromkeys(PPI_SERIES,'2026-10-15 07:00:00-05')  # before 08:30 New York
    assert all(m['actual'] is None for m in bind(updates=updates)['measures'][1:])


def test_future_actual_and_forecast_are_empty_even_with_future_observations():
    current=data()
    for sid in current:current[sid].append(dict(current[sid][-1],observation_date='2026-10-01'))
    rows=bind(current=current,day='2026-11-13',proof=evidence('2026-11-13','2026-10-01'))['measures']
    for row in rows:
        for m in [row,row['year_over_year']]:
            assert m['actual'] is None and m['forecast'] is None and m['previous'] is not None
            assert m['reference_period']=='2026-10-01' and m['previous_period']=='2026-09-01'


def test_revisions_recompute_only_the_appropriate_measure_and_keep_current_vintage():
    current=data();before=bind(current=current)['measures']
    current['PPICOR'][-1]['value']+=1
    after=bind(current=current)['measures']
    assert before[1]['actual']==after[1]['actual']
    assert before[1]['year_over_year']['actual']!=after[1]['year_over_year']['actual']
    assert before[2]['actual']==after[2]['actual']
    assert after[1]['year_over_year']['data_version']=='current_vintage'


def test_legacy_ppi_evidence_expansion_is_idempotent_and_never_creates_dates():
    proof=evidence();original=copy.deepcopy(proof)
    expanded=expand_ppi_evidence(proof)
    assert expanded['periods'][0]['series_ids']==list(PPI_SERIES)
    assert proof==original and expand_ppi_evidence(expanded)==expanded
    assert len(expanded['periods'])==1


def test_existing_headline_values_are_unchanged():
    old=bind_events([event(46,'2026-10-15',('PPIFIS',))],{},data(),datetime(2026,10,28,tzinfo=timezone.utc),
                    evidence(),dict.fromkeys(PPI_SERIES,'2026-10-15'))[0]['measures'][0]
    new=bind()['measures'][0]
    assert (old['actual'],old['previous'])==(new['actual'],new['previous'])


@pytest.mark.parametrize('sid',sorted(NEW_PPI_SERIES))
def test_existing_ingestion_keys_remain_idempotent_for_new_ppi_series(monkeypatch,tmp_path,sid):
    from tests.test_calendar_retail_measures import test_existing_ingester_reuses_retail_observation_keys_on_reimport
    test_existing_ingester_reuses_retail_observation_keys_on_reimport(monkeypatch,tmp_path,sid)
