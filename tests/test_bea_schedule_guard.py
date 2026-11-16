from datetime import date,datetime,timezone
import json,copy
from pathlib import Path
import httpx,pytest
from app.ingestion.sync_calendar_periods import parse_schedule,sync_periods,SOURCES
URL=SOURCES['bea']
CASES=[('November 25','3rd Quarter 2026 (Second Estimate)',53,'2026-07-01'),('December 23','3rd Quarter 2026 (Third Estimate)',53,'2026-07-01'),('November 25','Personal Income and Outlays, October 2026',54,'2026-10-01'),('December 23','Personal Income and Outlays, November 2026',54,'2026-11-01')]
def html(year,day,label):
 if not label.startswith('Personal'):label='GDP ('+label+')'
 return '<table><caption>Year '+str(year)+'</caption><tr><td>'+day+'</td><td>8:30</td><td>'+label+'</td></tr></table>'
@pytest.mark.parametrize('day,label,rid,period',CASES)
def test_good_and_bad_year(day,label,rid,period):
 good=parse_schedule('bea',html(2026,day,label),URL,'2026-11-16T12:00:00Z');assert good[0]['reference_period']==period
 with pytest.raises(ValueError,match='precedes'):parse_schedule('bea',html(2025,day,label),URL,'2026-11-16T12:00:00Z')
def test_previous_month_final_day_is_rejected():
 with pytest.raises(ValueError,match='precedes'):parse_schedule('bea',html(2026,'October 30','Personal Income and Outlays, October 2026'),URL,'2026-11-16T12:00:00Z')
def test_later_historical_revision_allowed():
 assert parse_schedule('bea',html(2027,'January 28','3rd Quarter 2026 (Updated Estimate)'),URL,'2027-01-28T15:00:00Z')[0]['estimate_stage']=='updated'
def test_synthetic_bad_capture_preserves_previous_proofs(tmp_path,monkeypatch):
 import app.source_checks
 monkeypatch.setattr(app.source_checks,"write_run",lambda *a,**k:None)
 target=tmp_path/'data/derived/calendar_periods_v1.json';target.parent.mkdir(parents=True)
 seed={'version':1,'periods':sum([parse_schedule('bea',html(2026,day,label),URL,'2026-11-11T12:00:00Z') for day,label,_,_ in CASES],[])}
 original=json.dumps(seed).encode();target.write_bytes(original)
 body=(''.join(html(2025,day,label) for day,label,_,_ in CASES)).encode()
 with httpx.Client(transport=httpx.MockTransport(lambda q:httpx.Response(200,content=body))) as client:
  result=sync_periods(client,date(2026,11,1),date(2026,12,31),[],datetime(2026,11,16,12,tzinfo=timezone.utc),path=target,source_kinds=['bea'],include_results=False)
 before=json.loads(original)
 assert result['periods']==before['periods']
 assert any(c['status']=='error' and c['source_url']==URL for c in result['checks'])
 assert any(p.read_bytes()==body for p in (tmp_path/'data/raw/calendar_periods').rglob('*.html'))
