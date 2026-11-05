-- Controlled activation only. Never executed by GET or application startup.
ALTER TABLE earnings_report_documents
 DROP CONSTRAINT earnings_report_documents_verification_method_check;
ALTER TABLE earnings_report_documents
 ADD CONSTRAINT earnings_report_documents_verification_method_check
 CHECK(verification_method IN ('manual_official_report_review','automated_official_report_validation'));

CREATE TABLE earnings_monitor_policy (
 id integer PRIMARY KEY CHECK(id=1),
 approved_plan_sha256 text NOT NULL CHECK(approved_plan_sha256 ~ '^[0-9a-f]{64}$'),
 target jsonb NOT NULL, artifacts jsonb NOT NULL,
 schema_sha256 text NOT NULL CHECK(schema_sha256 ~ '^[0-9a-f]{64}$'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE earnings_report_checks (
 check_id uuid NOT NULL, phase text NOT NULL CHECK(phase IN ('started','result')),
 event_id uuid NOT NULL REFERENCES earnings_events(event_id),
 scheduled_for timestamptz NOT NULL, attempted_at timestamptz NOT NULL,
 finished_at timestamptz, status text NOT NULL
 CHECK(status IN ('started','not_found','imported','review_required','http_retry','blocked','interrupted')),
 retry_after timestamptz, detail jsonb NOT NULL,
 PRIMARY KEY(check_id,phase), UNIQUE(event_id,scheduled_for,phase),
 CHECK((phase='started' AND status='started' AND finished_at IS NULL)
    OR (phase='result' AND status<>'started' AND finished_at IS NOT NULL))
);
CREATE INDEX earnings_report_checks_event ON earnings_report_checks(event_id,scheduled_for DESC);
CREATE FUNCTION earnings_monitor_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Earnings monitor policy and audit are append-only'; END $$;
CREATE TRIGGER earnings_monitor_policy_immutable BEFORE UPDATE OR DELETE OR TRUNCATE
 ON earnings_monitor_policy FOR EACH STATEMENT EXECUTE FUNCTION earnings_monitor_immutable();
CREATE TRIGGER earnings_report_checks_immutable BEFORE UPDATE OR DELETE OR TRUNCATE
 ON earnings_report_checks FOR EACH STATEMENT EXECUTE FUNCTION earnings_monitor_immutable();
