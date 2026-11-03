-- E2B opt-in. No ALTER/DROP of E2A or macro objects. Never applied by GET/startup.
CREATE TABLE earnings_financial_documents (
 document_id UUID PRIMARY KEY, company_id UUID NOT NULL, period_id UUID NOT NULL,
 event_id UUID NOT NULL, cik CHAR(10) NOT NULL,
 period_end DATE NOT NULL, release_date DATE NOT NULL,
 source_url TEXT NOT NULL CHECK(source_url LIKE 'https://%'),
 document_type TEXT NOT NULL CHECK(document_type='earnings_release'),
 sec_accession TEXT CHECK(sec_accession ~ '^[0-9]{10}-[0-9]{2}-[0-9]{6}$'),
 verified_on DATE NOT NULL CHECK(verified_on>=release_date),
 evidence_method TEXT NOT NULL CHECK(evidence_method='manual_official_fact_entry'),
 source_version TEXT NOT NULL CHECK(length(source_version)>0),
 availability_status TEXT NOT NULL CHECK(availability_status='manually_verified'),
 record_fingerprint CHAR(64) NOT NULL UNIQUE,
 captured_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(company_id,cik) REFERENCES earnings_companies(company_id,cik),
 FOREIGN KEY(period_id,company_id) REFERENCES earnings_periods(period_id,company_id),
 FOREIGN KEY(event_id,company_id) REFERENCES earnings_events(event_id,company_id),
 UNIQUE(document_id,event_id,period_id,company_id)
);
CREATE TABLE earnings_financial_observations (
 observation_id UUID PRIMARY KEY, document_id UUID NOT NULL,
 event_id UUID NOT NULL, period_id UUID NOT NULL, company_id UUID NOT NULL,
 metric TEXT NOT NULL CHECK(metric IN ('revenue','gaap_diluted_eps')),
 actual NUMERIC NOT NULL CHECK(actual::text NOT IN ('NaN','Infinity','-Infinity')),
 currency TEXT NOT NULL CHECK(currency='USD'),
 unit TEXT NOT NULL, source_value NUMERIC NOT NULL,
 source_unit TEXT NOT NULL, decimal_places INT NOT NULL CHECK(decimal_places BETWEEN 0 AND 6),
 methodology TEXT NOT NULL, version INT NOT NULL CHECK(version>0),
 supersedes_id UUID, correction_reason TEXT,
 record_fingerprint CHAR(64) NOT NULL UNIQUE,
 captured_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(document_id,event_id,period_id,company_id)
   REFERENCES earnings_financial_documents(document_id,event_id,period_id,company_id),
 UNIQUE(event_id,metric,version), UNIQUE(observation_id,event_id,metric),
 FOREIGN KEY(supersedes_id,event_id,metric)
   REFERENCES earnings_financial_observations(observation_id,event_id,metric),
 CHECK((version=1 AND supersedes_id IS NULL AND correction_reason IS NULL)
   OR (version>1 AND supersedes_id IS NOT NULL AND length(trim(correction_reason))>0)),
 CHECK(source_value=round(source_value,decimal_places)),
 CHECK((metric='revenue' AND unit='USD' AND source_unit IN ('USD','USD_millions','USD_billions')
   AND methodology='consolidated_revenue' AND actual>=0
   AND actual=source_value*CASE source_unit WHEN 'USD_millions' THEN 1000000 WHEN 'USD_billions' THEN 1000000000 ELSE 1 END)
   OR (metric='gaap_diluted_eps' AND unit='USD/share' AND source_unit='USD/share' AND actual=source_value
   AND methodology IN ('gaap_diluted','gaap_diluted_attributable_to_intel')))
);
CREATE FUNCTION earnings_financial_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prior earnings_financial_observations; e earnings_events; p earnings_periods;
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Financial history is append-only'; END IF;
 SELECT * INTO e FROM earnings_events WHERE event_id=NEW.event_id FOR UPDATE;
 SELECT * INTO p FROM earnings_periods WHERE period_id=NEW.period_id;
 IF e.period_id IS DISTINCT FROM NEW.period_id OR e.company_id IS DISTINCT FROM NEW.company_id
 THEN RAISE EXCEPTION 'Financial event/period/company conflict'; END IF;
 IF TG_TABLE_NAME='earnings_financial_documents' THEN
  IF p.period_end IS DISTINCT FROM NEW.period_end OR NEW.release_date<NEW.period_end
  THEN RAISE EXCEPTION 'Financial period end conflict'; END IF;
 ELSE
  SELECT * INTO prior FROM earnings_financial_observations
   WHERE event_id=NEW.event_id AND metric=NEW.metric ORDER BY version DESC LIMIT 1;
  IF (prior.observation_id IS NULL AND (NEW.version<>1 OR NEW.supersedes_id IS NOT NULL))
    OR (prior.observation_id IS NOT NULL AND (NEW.version<>prior.version+1 OR NEW.supersedes_id IS DISTINCT FROM prior.observation_id))
  THEN RAISE EXCEPTION 'Financial revision must extend the current version'; END IF;
  IF NEW.metric='gaap_diluted_eps' AND NEW.methodology IS DISTINCT FROM
     (CASE WHEN (SELECT cik FROM earnings_companies WHERE company_id=NEW.company_id)='0000050863'
       THEN 'gaap_diluted_attributable_to_intel' ELSE 'gaap_diluted' END)
  THEN RAISE EXCEPTION 'EPS attribution conflict'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER earnings_financial_document_guard BEFORE INSERT OR UPDATE OR DELETE
 ON earnings_financial_documents FOR EACH ROW EXECUTE FUNCTION earnings_financial_guard();
CREATE TRIGGER earnings_financial_observation_guard BEFORE INSERT OR UPDATE OR DELETE
 ON earnings_financial_observations FOR EACH ROW EXECUTE FUNCTION earnings_financial_guard();
CREATE TRIGGER earnings_financial_document_truncate BEFORE TRUNCATE
 ON earnings_financial_documents FOR EACH STATEMENT EXECUTE FUNCTION earnings_financial_guard();
CREATE TRIGGER earnings_financial_observation_truncate BEFORE TRUNCATE
 ON earnings_financial_observations FOR EACH STATEMENT EXECUTE FUNCTION earnings_financial_guard();
