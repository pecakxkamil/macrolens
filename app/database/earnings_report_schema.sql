-- E2D opt-in: new append-only evidence and original-currency facts only.
CREATE TABLE earnings_report_documents (
 document_id UUID PRIMARY KEY, event_id UUID NOT NULL, period_id UUID NOT NULL,
 company_id UUID NOT NULL, cik CHAR(10) NOT NULL,
 period_end DATE, document_type TEXT NOT NULL CHECK(document_type IN ('earnings_release','earnings_date_announcement')),
 release_date DATE, source_url TEXT NOT NULL CHECK(source_url LIKE 'https://%'), linked_from TEXT,
 verified_on DATE NOT NULL, verification_method TEXT NOT NULL CHECK(verification_method='manual_official_report_review'),
 source_version TEXT NOT NULL CHECK(length(trim(source_version))>0), facts TEXT NOT NULL CHECK(length(trim(facts))>0),
 reporting_standard TEXT CHECK(reporting_standard IN ('US_GAAP','IFRS')),
 reporting_currency TEXT CHECK(reporting_currency IN ('USD','EUR','TWD')),
 eps_share_basis TEXT CHECK(eps_share_basis IN ('common_share','ordinary_share','ADR')),
 version INT NOT NULL CHECK(version>0), supersedes_id UUID, correction_reason TEXT,
 record_fingerprint CHAR(64) NOT NULL UNIQUE, captured_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(company_id,cik) REFERENCES earnings_companies(company_id,cik),
 FOREIGN KEY(event_id,company_id) REFERENCES earnings_events(event_id,company_id),
 FOREIGN KEY(period_id,company_id) REFERENCES earnings_periods(period_id,company_id),
 UNIQUE(document_id,event_id,period_id,company_id), UNIQUE(document_id,event_id), UNIQUE(event_id,version),
 FOREIGN KEY(supersedes_id,event_id) REFERENCES earnings_report_documents(document_id,event_id),
 CHECK((version=1 AND supersedes_id IS NULL AND correction_reason IS NULL)
    OR (version>1 AND supersedes_id IS NOT NULL AND length(trim(correction_reason))>0)),
 CHECK((document_type='earnings_release' AND release_date IS NOT NULL AND release_date<=verified_on
      AND (period_end IS NULL OR period_end<=release_date))
    OR (document_type='earnings_date_announcement' AND release_date IS NULL))
);
CREATE TABLE earnings_report_observations (
 observation_id UUID PRIMARY KEY, document_id UUID NOT NULL, event_id UUID NOT NULL,
 period_id UUID NOT NULL, company_id UUID NOT NULL,
 metric TEXT NOT NULL CHECK(metric IN ('revenue','reported_diluted_eps')),
 actual NUMERIC NOT NULL CHECK(actual::text NOT IN ('NaN','Infinity','-Infinity')),
 source_value NUMERIC NOT NULL CHECK(source_value::text NOT IN ('NaN','Infinity','-Infinity')),
 currency TEXT NOT NULL CHECK(currency IN ('USD','EUR','TWD')),
 source_unit TEXT NOT NULL CHECK(source_unit IN ('units','thousands','millions','billions','per_share')),
 unit TEXT NOT NULL, decimal_places INT NOT NULL CHECK(decimal_places BETWEEN 0 AND 6),
 reporting_standard TEXT NOT NULL CHECK(reporting_standard IN ('US_GAAP','IFRS')),
 share_basis TEXT NOT NULL CHECK(share_basis IN ('not_applicable','common_share','ordinary_share','ADR')),
 methodology TEXT NOT NULL, version INT NOT NULL CHECK(version>0), supersedes_id UUID, correction_reason TEXT,
 record_fingerprint CHAR(64) NOT NULL UNIQUE, captured_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(document_id,event_id,period_id,company_id) REFERENCES earnings_report_documents(document_id,event_id,period_id,company_id),
 UNIQUE(event_id,metric,version), UNIQUE(observation_id,event_id,metric),
 FOREIGN KEY(supersedes_id,event_id,metric) REFERENCES earnings_report_observations(observation_id,event_id,metric),
 CHECK(source_value=round(source_value,decimal_places)),
 CHECK((version=1 AND supersedes_id IS NULL AND correction_reason IS NULL)
    OR (version>1 AND supersedes_id IS NOT NULL AND length(trim(correction_reason))>0)),
 CHECK((metric='revenue' AND actual>=0 AND unit=currency AND share_basis='not_applicable'
    AND methodology='consolidated_revenue' AND source_unit<>'per_share'
    AND actual=source_value*(CASE source_unit WHEN 'thousands' THEN 1000 WHEN 'millions' THEN 1000000 WHEN 'billions' THEN 1000000000 ELSE 1 END))
   OR (metric='reported_diluted_eps' AND actual=source_value AND source_unit='per_share'
    AND unit=currency||'/share' AND share_basis<>'not_applicable' AND methodology='reported_diluted_total_eps'))
);
CREATE FUNCTION earnings_report_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE e earnings_events; p earnings_periods; d earnings_report_documents;
 prior_d earnings_report_documents; prior_o earnings_report_observations;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Report evidence and observations are append-only'; END IF;
 SELECT * INTO e FROM earnings_events WHERE event_id=NEW.event_id FOR UPDATE;
 SELECT * INTO p FROM earnings_periods WHERE period_id=NEW.period_id;
 IF e.period_id IS DISTINCT FROM NEW.period_id OR e.company_id IS DISTINCT FROM NEW.company_id THEN
  RAISE EXCEPTION 'Report issuer/event/fiscal period conflict'; END IF;
 IF TG_TABLE_NAME='earnings_report_documents' THEN
  IF p.period_end IS NOT NULL AND p.period_end IS DISTINCT FROM NEW.period_end THEN
   RAISE EXCEPTION 'Report period end conflicts with existing metadata'; END IF;
  SELECT * INTO prior_d FROM earnings_report_documents WHERE event_id=NEW.event_id ORDER BY version DESC LIMIT 1;
  IF prior_d.document_id IS NULL THEN
   IF NEW.version<>1 OR NEW.supersedes_id IS NOT NULL THEN RAISE EXCEPTION 'Invalid first document version'; END IF;
  ELSIF NEW.version<>prior_d.version+1 OR NEW.supersedes_id IS DISTINCT FROM prior_d.document_id
     OR (prior_d.document_type='earnings_release' AND NEW.document_type<>'earnings_release') THEN
   RAISE EXCEPTION 'Document must extend current evidence without unpublishing a release'; END IF;
 ELSE
  SELECT * INTO d FROM earnings_report_documents WHERE document_id=NEW.document_id;
  IF d.document_type IS DISTINCT FROM 'earnings_release' OR d.reporting_standard IS DISTINCT FROM NEW.reporting_standard
    OR d.reporting_currency IS DISTINCT FROM NEW.currency
    OR (NEW.metric='reported_diluted_eps' AND d.eps_share_basis IS DISTINCT FROM NEW.share_basis) THEN
   RAISE EXCEPTION 'Actual requires published evidence with matching currency/standard/share basis'; END IF;
  IF d.version IS DISTINCT FROM (SELECT max(version) FROM earnings_report_documents WHERE event_id=NEW.event_id) THEN
   RAISE EXCEPTION 'Cannot add new metrics against superseded evidence'; END IF;
  SELECT * INTO prior_o FROM earnings_report_observations WHERE event_id=NEW.event_id AND metric=NEW.metric ORDER BY version DESC LIMIT 1;
  IF prior_o.observation_id IS NULL THEN
   IF NEW.version<>1 OR NEW.supersedes_id IS NOT NULL THEN RAISE EXCEPTION 'Invalid first metric version'; END IF;
  ELSIF NEW.version<>prior_o.version+1 OR NEW.supersedes_id IS DISTINCT FROM prior_o.observation_id THEN
   RAISE EXCEPTION 'Metric must extend current version'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER earnings_report_document_guard BEFORE INSERT OR UPDATE OR DELETE ON earnings_report_documents FOR EACH ROW EXECUTE FUNCTION earnings_report_guard();
CREATE TRIGGER earnings_report_observation_guard BEFORE INSERT OR UPDATE OR DELETE ON earnings_report_observations FOR EACH ROW EXECUTE FUNCTION earnings_report_guard();
CREATE TRIGGER earnings_report_document_truncate BEFORE TRUNCATE ON earnings_report_documents FOR EACH STATEMENT EXECUTE FUNCTION earnings_report_guard();
CREATE TRIGGER earnings_report_observation_truncate BEFORE TRUNCATE ON earnings_report_observations FOR EACH STATEMENT EXECUTE FUNCTION earnings_report_guard();
