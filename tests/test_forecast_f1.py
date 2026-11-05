import copy
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import uuid4
import pytest
from app import forecast_f1 as f
from app.forecast_f1_sources import parse_cleveland

NOW=datetime(2026,11,5,12,tzinfo=timezone.utc)

def record():
 return dict(kind='model_nowcast',subject=dict(domain='macro',country='US',indicator='CPIAUCSL',period='2026-10-01',transform='mom',adjustment='SA',unit='percent',methodology='publisher_index_change',publication_stage='main'),value='0.24',low=None,high=None,source_id='test',source_url='https://example.org/source',published_at='2026-11-03T00:00:00Z',publication_precision='date',methodology='test model',source_sha256='a'*64,rights='noncommercial_attributed',note='synthetic test only')
def vintage(r=None,version=1,at=NOW):
 r=r or record();return dict(forecast_id=uuid4(),subject_key=f.digest(r['subject']),kind=r['kind'],source_id=r['source_id'],version=version,payload=r,captured_at=at)

@pytest.mark.parametrize('change',[{'kind':'guidance'},{'value':'NaN'},{'value':'Infinity'},{'low':'2','high':'1'},{'low':'0','high':None},{'value':'3','low':'0','high':'2'},{'source_sha256':'not-a-sha'},{'rights':'public_webpage'},{'published_at':'2026-11-03'},{'publication_precision':'guessed'}])
def test_reject_ambiguous_or_unlicensed(change):
 r=record();r.update(change)
 with pytest.raises((ValueError,AssertionError)):f.validate(r)

@pytest.mark.parametrize('field,value',[('country','DE'),('period','2026-10-15'),('transform','raw'),('adjustment','unknown'),('unit','index'),('methodology','ytd')])
def test_strict_macro_identity(field,value):
 r=record();r['subject'][field]=value
 with pytest.raises((ValueError,AssertionError)):f.validate(r)

def test_capture_is_not_retroactive_and_cutoff_is_strict():
 v=vintage();s=v['payload']['subject'];cutoff=NOW-timedelta(days=1)
 assert f.choose(([v],[]),s,'e',cutoff,True)[0] is None
 assert f.choose(([v],[]),s,'e',NOW+timedelta(days=1),False,NOW)[0]['kind']=='model_nowcast'
 assert f.choose(([v],[]),s,'e',NOW,False,NOW)[0] is None
 assert f.choose(None,s,'e',None,False)[1]=='not_activated'

def test_no_latest_period_or_currency_fallback():
 v=vintage();s=copy.deepcopy(v['payload']['subject']);s['period']='2026-11-01'
 assert f.choose(([v],[]),s,'e',NOW+timedelta(days=1),False,NOW)[0] is None

def test_freeze_preserves_null_and_older_vintage_even_after_new_capture():
 v=vintage();r=copy.deepcopy(v['payload']);r['value']='0.30';later=vintage(r,2,NOW+timedelta(hours=1));s=r['subject']
 frozen=dict(event_id='e',subject_key=f.digest(s),forecast_id=v['forecast_id'])
 selected,state=f.choose(([v,later],[frozen]),s,'e',NOW,True,NOW+timedelta(hours=2))
 assert state=='frozen' and selected['value']=='0.24'
 frozen['forecast_id']=None
 assert f.choose(([v,later],[frozen]),s,'e',NOW,True)[0] is None

def test_new_range_does_not_fall_back_to_old_point_or_invent_midpoint():
 v=vintage();r=copy.deepcopy(v['payload']);r.update(value=None,low='0.2',high='0.4');new=vintage(r,2)
 result=f.choose(([v,new],[]),r['subject'],'e',NOW+timedelta(days=1),False,NOW)[0]
 assert result['value'] is None and result['low']=='0.2'

def test_consensus_and_nowcast_are_explicit_distinct_types():
 nowcast=vintage();r=copy.deepcopy(nowcast['payload']);r.update(kind='consensus',source_id='survey');consensus=vintage(r)
 result=f.choose(([nowcast,consensus],[]),r['subject'],'e',NOW+timedelta(days=1),False,NOW)[0]
 assert result['kind']=='consensus' and not result['comparison_allowed']

def test_normal_write_guard_before_schema_or_network():
 class C:info=type('I',(),dict(dbname='macrolens',server_version=170000))()
 for fn,args in [(f.initialize,()),(f.append,([] ,))]:
  with pytest.raises(ValueError,match='isolated'):fn(C(),*args)

def test_reviewed_guidance_basis_and_no_midpoints():
 records=json.loads((f.ROOT/'config/forecast_f1_reviewed.json').read_text())['earnings_records']
 for r in records:f.validate(r)
 assert len(records)==4
 assert next(r for r in records if r['subject']['metric']=='reported_diluted_eps')['value'] is None

# These tiny HTML values are SYNTHETIC parser tests, not the live pilot.
def page():
 headers='<tr>'+''.join('<th>'+x+'</th>' for x in ['Month','CPI','Core CPI','PCE','Core PCE','Updated'])+'</tr>'
 return ('Inflation Nowcasting'+''.join('<table><caption>'+label+'</caption>'+headers+'<tr><td>October 2026</td><td>0.24</td><td>0.21</td><td>0.27</td><td>0.26</td><td>11/04</td></tr></table>' for label in ['Inflation, month-over-month percent change','Inflation, year-over-year percent change'])).encode()

def test_parser_exact_columns_transform_source_and_staleness():
 rows=parse_cleveland(page(),NOW);assert len(rows)==8 and {r['subject']['transform'] for r in rows}=={'mom','yoy'}
 with pytest.raises(ValueError):parse_cleveland(page().replace(b'Core CPI',b'Unknown'),NOW)
 with pytest.raises(ValueError):parse_cleveland(page(),NOW+timedelta(days=10))
 with pytest.raises(ValueError):parse_cleveland(b'challenge',NOW)


def test_gdp_release_stage_is_part_of_identity():
 m=dict(series_id='GDPC1',mapping_status='confirmed',reference_period='2026-10-01',feature_name='qoq_annualized',unit='percent')
 assert f.macro_subject(m,{'estimate_stage':'advance'})!=f.macro_subject(m,{'estimate_stage':'second'})

def test_earnings_guidance_does_not_cross_gaap_adr_or_fiscal_quarters():
 r=json.loads((f.ROOT/'config/forecast_f1_reviewed.json').read_text())['earnings_records'][2]
 v=vintage(r)
 for key,value in [('standard','non_GAAP'),('share_basis','ADR'),('fiscal_quarter',1),('currency','EUR')]:
  subject=copy.deepcopy(r['subject']);subject[key]=value
  assert f.choose(([v],[]),subject,'e',NOW+timedelta(days=1),False,NOW)[0] is None
