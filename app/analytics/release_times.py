"""Official publication-time conventions for a small set of tracked releases.

FRED supplies release dates, not these times. Confirm a provider's schedule before
adding another name. These conventions may change for an individual release.
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


SOURCE_TIMEZONE = "America/New_York"
EASTERN = ZoneInfo(SOURCE_TIMEZONE)

# BLS: https://www.bls.gov/schedule/2026/home.htm
# BEA: https://www.bea.gov/news/schedule/full
# Census: https://www.census.gov/construction/soc/schedule.html
OFFICIAL_RELEASE_TIMES = {
    "Employment Situation": time(8, 30),
    "Consumer Price Index": time(8, 30),
    "Job Openings and Labor Turnover Survey": time(10, 0),
    "Gross Domestic Product": time(8, 30),
    "Personal Income and Outlays": time(8, 30),
    "New Residential Construction": time(8, 30),
    "New Residential Sales": time(10, 0),
}


def release_time_metadata(name: str, release_date: date, evidence=None) -> dict:
    supplied=evidence is not None
    evidence=evidence or {}
    from app.analytics.calendar_evidence import claims_rule, period_evidence
    from app.ingestion.bls_schedule import GROUPS
    documented=None
    if name=='New Residential Construction' and supplied:
        proof=period_evidence(evidence,27,str(release_date),'PERMIT')
        if proof and proof.get('estimate_stage')=='revised_permits':
            if not proof.get('release_time'):return dict(release_time=None,source_timezone=None,release_datetime_utc=None)
            documented=dict(time=proof['release_time'],source_url=proof['source_url'],valid_from=str(release_date),valid_through=str(release_date))
    scoped={'Advance Monthly Sales for Retail and Food Services':(9,'RSAFS'),
            'G.17 Industrial Production and Capacity Utilization':(13,'INDPRO')}
    if name in scoped:
        rid,sid=scoped[name]
        proof=period_evidence(evidence,rid,str(release_date),sid)
        if proof and proof.get('release_time'):
            documented=dict(time=proof['release_time'],source_url=proof.get('clock_source_url') or proof['source_url'],valid_from=str(release_date),valid_through=str(release_date))
        else:
            clocks=[r for r in evidence.get('rules',[]) if r.get('release_id')==rid and r.get('valid_from','9999')<=str(release_date)<=r.get('valid_through','') and str(release_date) in r.get('dates',{})]
            if clocks:
                rule=max(clocks,key=lambda r:r['retrieved_at'])
                documented=dict(time=rule['dates'][str(release_date)],source_url=rule['source_url'],valid_from=rule['valid_from'],valid_through=rule['valid_through'])
    if name in GROUPS and supplied:
        rid,sids,_=GROUPS[name]
        proof=period_evidence(evidence,rid,str(release_date),sids[0])
        if proof and proof.get('release_time'):
            documented=dict(time=proof['release_time'],source_url=proof['source_url'],valid_from=str(release_date),valid_through=str(release_date))
        elif not proof:
            return dict(release_time=None,source_timezone=None,release_datetime_utc=None)
    elif name in ('Chicago Fed National Activity Index','Chicago Fed National Financial Conditions Index') and date(2026,1,1)<=release_date<=date(2026,12,31):
        documented=dict(time='08:30:00',source_url='https://www.chicagofed.org/research/data/data-release-calendar',valid_from='2026-01-01',valid_through='2026-12-31')
        proof=period_evidence(evidence,219 if name=='Chicago Fed National Activity Index' else 221,str(release_date),'CFNAI' if name=='Chicago Fed National Activity Index' else 'NFCI')
        if proof and proof.get('release_time'):documented.update(time=proof['release_time'],source_url=proof['source_url'],valid_from=str(release_date),valid_through=str(release_date))
    elif name=='Unemployment Insurance Weekly Claims Report':
        rule=claims_rule(evidence,str(release_date))
        if rule:documented=dict(time=rule.get('exceptions',{}).get(str(release_date),'08:30:00'),source_url=rule['source_url'],valid_from=rule['valid_from'],valid_through=rule['valid_through'])
        proof=period_evidence(evidence,180,str(release_date),'ICSA')
        if proof and proof.get('release_time'):documented=dict(time=proof['release_time'],source_url=proof['source_url'],valid_from=str(release_date),valid_through=str(release_date))
    elif name=="Manufacturer's Shipments, Inventories, and Orders (M3) Survey":
        proof=period_evidence(evidence,95,str(release_date),'DGORDER')
        if proof and proof.get('estimate_stage') in ('advance','full'):
            documented=dict(time=proof.get('release_time') or ('08:30:00' if proof['estimate_stage']=='advance' else '10:00:00'),source_url=proof['source_url'],valid_from=str(release_date),valid_through=str(release_date))
    if documented:
        source_time=time.fromisoformat(documented['time'])
        instant=datetime.combine(release_date,source_time,tzinfo=EASTERN).astimezone(timezone.utc)
        return dict(release_time=source_time.isoformat(),source_timezone=SOURCE_TIMEZONE,release_datetime_utc=instant.isoformat().replace('+00:00','Z'),
                    time_source_url=documented['source_url'],time_rule={**documented,'source_timezone':SOURCE_TIMEZONE})
    source_time = OFFICIAL_RELEASE_TIMES.get(name)
    if source_time is None:
        return {
            "release_time": None,
            "source_timezone": None,
            "release_datetime_utc": None,
        }
    source_datetime = datetime.combine(release_date, source_time, tzinfo=EASTERN)
    utc_datetime = source_datetime.astimezone(timezone.utc)
    return {
        "release_time": source_time.isoformat(timespec="seconds"),
        "source_timezone": SOURCE_TIMEZONE,
        "release_datetime_utc": utc_datetime.isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
