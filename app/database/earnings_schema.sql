-- E2A opt-in schema. Applied only by init_earnings_db to an owned test database.
CREATE TABLE IF NOT EXISTS earnings_companies (
 company_id UUID PRIMARY KEY, cik CHAR(10) NOT NULL UNIQUE CHECK(cik ~ '^[0-9]{10}$'),
 name TEXT NOT NULL, ticker TEXT NOT NULL, UNIQUE(company_id,cik)
);
CREATE TABLE IF NOT EXISTS earnings_company_aliases (
 company_id UUID NOT NULL REFERENCES earnings_companies(company_id), ticker TEXT NOT NULL,
 PRIMARY KEY(company_id,ticker)
);
CREATE TABLE IF NOT EXISTS earnings_periods (
 period_id UUID PRIMARY KEY, company_id UUID NOT NULL REFERENCES earnings_companies(company_id),
 fiscal_year INT NOT NULL CHECK(fiscal_year BETWEEN 1900 AND 2200),
 fiscal_quarter INT NOT NULL CHECK(fiscal_quarter BETWEEN 1 AND 4),
 period_kind TEXT NOT NULL CHECK(period_kind='quarter'), period_label TEXT NOT NULL, period_end DATE,
 UNIQUE(company_id,fiscal_year,fiscal_quarter,period_kind), UNIQUE(period_id,company_id)
);
CREATE TABLE IF NOT EXISTS earnings_events (
 event_id UUID PRIMARY KEY, period_id UUID NOT NULL UNIQUE, company_id UUID NOT NULL,
 publication_status TEXT NOT NULL DEFAULT 'unconfirmed' CHECK(publication_status='unconfirmed'),
 FOREIGN KEY(period_id,company_id) REFERENCES earnings_periods(period_id,company_id),
 UNIQUE(event_id,company_id)
);
CREATE TABLE IF NOT EXISTS earnings_source_evidence (
 evidence_id UUID PRIMARY KEY, event_id UUID NOT NULL, company_id UUID NOT NULL,
 source_url TEXT NOT NULL CHECK(source_url LIKE 'https://%'),
 source_kind TEXT NOT NULL CHECK(source_kind='official_announcement'),
 verification_method TEXT NOT NULL CHECK(verification_method='manually_verified_official_source'),
 verified_on DATE NOT NULL, facts TEXT NOT NULL, content_fingerprint CHAR(64) NOT NULL,
 FOREIGN KEY(event_id,company_id) REFERENCES earnings_events(event_id,company_id),
 UNIQUE(event_id,content_fingerprint), UNIQUE(evidence_id,event_id,company_id)
);
CREATE TABLE IF NOT EXISTS earnings_date_confirmations (
 confirmation_id UUID PRIMARY KEY, event_id UUID NOT NULL, company_id UUID NOT NULL,
 component TEXT NOT NULL CHECK(component IN ('release','call')),
 sequence INT NOT NULL CHECK(sequence>0),
 date_status TEXT NOT NULL CHECK(date_status IN ('unknown','confirmed','changed','cancelled')),
 precision TEXT NOT NULL CHECK(precision IN ('exact','approximate','after_close','before_open','date_only','unknown')),
 source_local_date DATE, source_local_time TIME,
 source_timezone TEXT CHECK(source_timezone IN ('America/New_York','America/Los_Angeles')),
 timezone_label_raw TEXT, scheduled_at_utc TIMESTAMPTZ, expected_time_utc TIMESTAMPTZ,
 evidence_id UUID, supersedes_id UUID,
 FOREIGN KEY(event_id,company_id) REFERENCES earnings_events(event_id,company_id),
 FOREIGN KEY(evidence_id,event_id,company_id) REFERENCES earnings_source_evidence(evidence_id,event_id,company_id),
 UNIQUE(event_id,component,sequence), UNIQUE(confirmation_id,event_id,component),
 FOREIGN KEY(supersedes_id,event_id,component) REFERENCES earnings_date_confirmations(confirmation_id,event_id,component),
 CHECK((sequence=1 AND supersedes_id IS NULL) OR (sequence>1 AND supersedes_id IS NOT NULL)),
 CHECK((date_status='unknown' AND precision='unknown' AND source_local_date IS NULL AND evidence_id IS NULL)
    OR (date_status<>'unknown' AND precision<>'unknown' AND source_local_date IS NOT NULL AND evidence_id IS NOT NULL)),
 CHECK((precision='exact' AND source_local_time IS NOT NULL AND source_timezone IS NOT NULL AND timezone_label_raw IS NOT NULL AND scheduled_at_utc IS NOT NULL AND expected_time_utc IS NULL)
    OR (precision='approximate' AND source_local_time IS NOT NULL AND source_timezone IS NOT NULL AND timezone_label_raw IS NOT NULL AND scheduled_at_utc IS NULL AND expected_time_utc IS NOT NULL)
    OR (precision IN ('after_close','before_open','date_only','unknown') AND source_local_time IS NULL AND scheduled_at_utc IS NULL AND expected_time_utc IS NULL))
);
CREATE INDEX IF NOT EXISTS earnings_confirmation_date ON earnings_date_confirmations(source_local_date);
CREATE OR REPLACE FUNCTION earnings_confirmation_transition() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prior earnings_date_confirmations;
BEGIN
 PERFORM 1 FROM earnings_events WHERE event_id=NEW.event_id FOR UPDATE;
 SELECT * INTO prior FROM earnings_date_confirmations WHERE event_id=NEW.event_id AND component=NEW.component ORDER BY sequence DESC LIMIT 1;
 IF prior.confirmation_id IS NOT NULL THEN
  IF NEW.sequence<>prior.sequence+1 OR NEW.supersedes_id IS DISTINCT FROM prior.confirmation_id
     OR NEW.date_status='unknown' OR (prior.date_status<>'unknown' AND NEW.date_status NOT IN ('changed','cancelled')) THEN
   RAISE EXCEPTION 'Invalid earnings confirmation transition';
  END IF;
 ELSIF NEW.sequence<>1 OR NEW.supersedes_id IS NOT NULL THEN
  RAISE EXCEPTION 'First earnings confirmation must have sequence one';
 END IF;
 IF NEW.precision='exact' AND NEW.scheduled_at_utc IS DISTINCT FROM ((NEW.source_local_date+NEW.source_local_time) AT TIME ZONE NEW.source_timezone) THEN
  RAISE EXCEPTION 'Exact time conflicts with source timezone';
 END IF;
 IF NEW.precision='approximate' AND NEW.expected_time_utc IS DISTINCT FROM ((NEW.source_local_date+NEW.source_local_time) AT TIME ZONE NEW.source_timezone) THEN
  RAISE EXCEPTION 'Approximate time conflicts with source timezone';
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS earnings_confirmation_transition ON earnings_date_confirmations;
CREATE TRIGGER earnings_confirmation_transition BEFORE INSERT ON earnings_date_confirmations FOR EACH ROW EXECUTE FUNCTION earnings_confirmation_transition();
CREATE OR REPLACE FUNCTION earnings_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Earnings evidence and confirmations are append-only'; END $$;
DROP TRIGGER IF EXISTS earnings_evidence_immutable ON earnings_source_evidence;
CREATE TRIGGER earnings_evidence_immutable BEFORE UPDATE OR DELETE ON earnings_source_evidence FOR EACH ROW EXECUTE FUNCTION earnings_immutable();
DROP TRIGGER IF EXISTS earnings_confirmation_immutable ON earnings_date_confirmations;
CREATE TRIGGER earnings_confirmation_immutable BEFORE UPDATE OR DELETE ON earnings_date_confirmations FOR EACH ROW EXECUTE FUNCTION earnings_immutable();
