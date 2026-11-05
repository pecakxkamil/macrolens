-- Forecast F1: isolated initialization only; never startup/GET DDL.
CREATE TABLE forecast_vintages(
 forecast_id UUID PRIMARY KEY,subject_key TEXT NOT NULL CHECK(subject_key ~ '^[0-9a-f]{64}$'),
 kind TEXT NOT NULL CHECK(kind IN ('consensus','model_nowcast','issuer_guidance')),
 source_id TEXT NOT NULL CHECK(length(source_id)>0),version INTEGER NOT NULL CHECK(version>0),
 fingerprint TEXT NOT NULL UNIQUE CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
 payload JSONB NOT NULL CHECK(jsonb_typeof(payload)='object'),
 captured_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(subject_key,kind,source_id,version),UNIQUE(forecast_id,subject_key,kind)
);
CREATE TABLE forecast_freezes(
 event_id TEXT NOT NULL,subject_key TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('consensus','model_nowcast','issuer_guidance')),
 release_cutoff TIMESTAMPTZ NOT NULL,forecast_id UUID,
 reason TEXT NOT NULL CHECK(reason IN ('last_pre_release','no_pre_release_evidence')),
 frozen_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(event_id,subject_key,kind),
 FOREIGN KEY(forecast_id,subject_key,kind) REFERENCES forecast_vintages(forecast_id,subject_key,kind),
 CHECK((forecast_id IS NULL)=(reason='no_pre_release_evidence'))
);
CREATE TABLE forecast_refresh_checks(
 check_id UUID PRIMARY KEY,source_id TEXT NOT NULL,checked_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 outcome TEXT NOT NULL CHECK(outcome IN ('success','error','blocked','not_modified')),
 retry_at TIMESTAMPTZ NOT NULL,detail JSONB NOT NULL CHECK(jsonb_typeof(detail)='object')
);
CREATE INDEX forecast_refresh_latest ON forecast_refresh_checks(source_id,checked_at DESC);
CREATE FUNCTION forecast_f1_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prior INTEGER; n NUMERIC; lo NUMERIC; hi NUMERIC; s JSONB;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Forecast F1 is append-only'; END IF;
 IF TG_TABLE_NAME='forecast_vintages' THEN
  PERFORM pg_advisory_xact_lock(hashtextextended(NEW.subject_key,726530030));
  SELECT max(version) INTO prior FROM forecast_vintages WHERE subject_key=NEW.subject_key AND kind=NEW.kind AND source_id=NEW.source_id;
  IF NEW.version<>coalesce(prior,0)+1 THEN RAISE EXCEPTION 'Exact forecast version required'; END IF;
  NEW.captured_at=clock_timestamp();
  IF NOT (NEW.payload ?& ARRAY['subject','kind','source_id','value','low','high','published_at','publication_precision','rights','source_url','source_sha256','methodology','note'])
   OR NEW.payload->>'kind' IS DISTINCT FROM NEW.kind OR NEW.payload->>'source_id' IS DISTINCT FROM NEW.source_id
   OR coalesce(NEW.payload->>'rights','') NOT IN ('noncommercial_attributed','public_filing_facts')
   OR NEW.payload->>'source_url' NOT LIKE 'https://%'
   OR NEW.payload->>'source_sha256' !~ '^[0-9a-f]{64}$'
   OR (NEW.payload->>'published_at')::timestamptz>NEW.captured_at
   OR coalesce(NEW.payload->>'publication_precision','') NOT IN ('date','instant') THEN RAISE EXCEPTION 'Invalid forecast provenance'; END IF;
  n=(NEW.payload->>'value')::numeric;lo=(NEW.payload->>'low')::numeric;hi=(NEW.payload->>'high')::numeric;
  IF (n IS NULL AND lo IS NULL) OR (lo IS NULL)<>(hi IS NULL) OR lo>hi OR n<lo OR n>hi
   OR coalesce(n::text,'') IN ('NaN','Infinity','-Infinity') OR coalesce(lo::text,'') IN ('NaN','Infinity','-Infinity') OR coalesce(hi::text,'') IN ('NaN','Infinity','-Infinity') THEN RAISE EXCEPTION 'Invalid forecast numbers'; END IF;
  s=NEW.payload->'subject';
  IF s->>'domain'='macro' THEN
   IF NOT(s ?& ARRAY['country','indicator','period','transform','adjustment','unit','methodology','publication_stage']) OR s->>'country'<>'US'
    OR s->>'indicator' NOT IN ('CPIAUCSL','CPILFESL','PCEPI','PCEPILFE','GDPC1') OR s->>'unit'<>'percent'
    OR s->>'publication_stage' NOT IN ('main','advance','second','third') OR s->>'adjustment' NOT IN ('SA','NSA') OR s->>'transform' NOT IN ('mom','yoy','qoq_annualized')
    OR s->>'methodology'<>'publisher_index_change' OR extract(day FROM (s->>'period')::date)<>1
    OR (s->>'indicator'='GDPC1' AND s->>'transform'<>'qoq_annualized') THEN RAISE EXCEPTION 'Invalid macro identity';END IF;
  ELSIF s->>'domain'='earnings' THEN
   IF NOT(s ?& ARRAY['company_id','cik','fiscal_year','fiscal_quarter','metric','currency','standard','eps_basis','share_basis','methodology'])
    OR s->>'cik' !~ '^[0-9]+$' OR (s->>'fiscal_year')::int NOT BETWEEN 2000 AND 2100 OR (s->>'fiscal_quarter')::int NOT BETWEEN 1 AND 4
    OR s->>'currency' NOT IN ('USD','EUR','TWD') OR s->>'standard' NOT IN ('US_GAAP','IFRS','non_GAAP')
    OR s->>'metric' NOT IN ('revenue','reported_diluted_eps')
    OR (s->>'metric'='reported_diluted_eps' AND (s->>'eps_basis'<>'diluted' OR s->>'share_basis' NOT IN ('common_share','ordinary_share','ADR') OR s->>'methodology'<>'reported_diluted_eps'))
    OR (s->>'metric'='revenue' AND (s->>'eps_basis'<>'not_applicable' OR s->>'share_basis'<>'not_applicable' OR s->>'methodology'<>'consolidated_quarterly_revenue')) THEN RAISE EXCEPTION 'Invalid Earnings identity';END IF;
   IF NOT EXISTS(SELECT 1 FROM earnings_companies WHERE company_id=(s->>'company_id')::uuid AND cik=s->>'cik') THEN RAISE EXCEPTION 'Unknown issuer/CIK';END IF;
  ELSE RAISE EXCEPTION 'Invalid domain';END IF;
 ELSIF TG_TABLE_NAME='forecast_freezes' THEN
  IF NEW.release_cutoff>clock_timestamp() THEN RAISE EXCEPTION 'Future freeze';END IF;
  NEW.frozen_at=clock_timestamp();
  IF NEW.forecast_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM forecast_vintages v WHERE v.forecast_id=NEW.forecast_id AND v.captured_at<NEW.release_cutoff AND
   (v.payload->>'published_at')::timestamptz < NEW.release_cutoff) THEN RAISE EXCEPTION 'Post-release knowledge';END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER forecast_vintage_insert BEFORE INSERT ON forecast_vintages FOR EACH ROW EXECUTE FUNCTION forecast_f1_guard();
CREATE TRIGGER forecast_vintage_immutable BEFORE UPDATE OR DELETE ON forecast_vintages FOR EACH ROW EXECUTE FUNCTION forecast_f1_guard();
CREATE TRIGGER forecast_vintage_no_truncate BEFORE TRUNCATE ON forecast_vintages FOR EACH STATEMENT EXECUTE FUNCTION forecast_f1_guard();
CREATE TRIGGER forecast_freeze_insert BEFORE INSERT ON forecast_freezes FOR EACH ROW EXECUTE FUNCTION forecast_f1_guard();
CREATE TRIGGER forecast_freeze_immutable BEFORE UPDATE OR DELETE ON forecast_freezes FOR EACH ROW EXECUTE FUNCTION forecast_f1_guard();
CREATE TRIGGER forecast_freeze_no_truncate BEFORE TRUNCATE ON forecast_freezes FOR EACH STATEMENT EXECUTE FUNCTION forecast_f1_guard();
CREATE TRIGGER forecast_check_immutable BEFORE UPDATE OR DELETE ON forecast_refresh_checks FOR EACH ROW EXECUTE FUNCTION forecast_f1_guard();
CREATE TRIGGER forecast_check_no_truncate BEFORE TRUNCATE ON forecast_refresh_checks FOR EACH STATEMENT EXECUTE FUNCTION forecast_f1_guard();
