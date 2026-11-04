-- E2E: financial snapshots without synthetic periods/events. Isolated only.
CREATE TABLE earnings_historical_reports (
 document_id uuid PRIMARY KEY,
 company_id uuid NOT NULL REFERENCES earnings_companies(company_id),
 cik text NOT NULL CHECK (cik ~ '^[0-9]{10}$'),
 fiscal_year integer NOT NULL CHECK (fiscal_year BETWEEN 1900 AND 2200),
 fiscal_quarter integer NOT NULL CHECK (fiscal_quarter BETWEEN 1 AND 4),
 version integer NOT NULL CHECK (version > 0),
 supersedes_id uuid UNIQUE REFERENCES earnings_historical_reports(document_id),
 correction_reason text,
 record_fingerprint text NOT NULL UNIQUE CHECK (record_fingerprint ~ '^[0-9a-f]{64}$'),
 payload jsonb NOT NULL CHECK (jsonb_typeof(payload)='object'),
 captured_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(company_id,fiscal_year,fiscal_quarter,version),
 CHECK ((version=1 AND supersedes_id IS NULL AND correction_reason IS NULL) OR
        (version>1 AND supersedes_id IS NOT NULL AND length(btrim(correction_reason))>0))
);
CREATE FUNCTION earnings_history_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE prior earnings_historical_reports; item jsonb; expected numeric; seen text[] := ARRAY[]::text[];
BEGIN
 IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'Historical reports are append-only'; END IF;
 PERFORM 1 FROM earnings_companies WHERE company_id=NEW.company_id AND cik=NEW.cik FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Historical issuer mismatch'; END IF;
 SELECT * INTO prior FROM earnings_historical_reports WHERE company_id=NEW.company_id
  AND fiscal_year=NEW.fiscal_year AND fiscal_quarter=NEW.fiscal_quarter ORDER BY version DESC LIMIT 1;
 IF (prior.document_id IS NULL AND NEW.version<>1) OR
    (prior.document_id IS NOT NULL AND (NEW.version<>prior.version+1 OR NEW.supersedes_id IS DISTINCT FROM prior.document_id))
 THEN RAISE EXCEPTION 'Exact historical predecessor required'; END IF;
 IF NOT (NEW.payload ?& ARRAY['cik','fiscal_year','fiscal_quarter','document_type','reporting_standard','currency','source_url','release_date','verified_on','observations']) OR
    NEW.payload->>'cik' IS DISTINCT FROM NEW.cik OR
    (NEW.payload->>'fiscal_year')::integer IS DISTINCT FROM NEW.fiscal_year OR
    (NEW.payload->>'fiscal_quarter')::integer IS DISTINCT FROM NEW.fiscal_quarter OR
    NEW.payload->>'document_type' IS DISTINCT FROM 'earnings_release' OR
    coalesce(NEW.payload->>'reporting_standard','') NOT IN ('US_GAAP','IFRS') OR
    coalesce(NEW.payload->>'currency','') NOT IN ('USD','EUR','TWD') OR
    coalesce(NEW.payload->>'source_url','') !~ '^https://' OR
    NEW.payload->>'release_date' IS NULL OR NEW.payload->>'verified_on' IS NULL OR
    (NEW.payload->>'verified_on')::date > CURRENT_DATE OR
    (NEW.payload->>'release_date')::date > (NEW.payload->>'verified_on')::date OR
    (NEW.payload->>'period_end')::date > (NEW.payload->>'release_date')::date OR
    jsonb_typeof(NEW.payload->'observations') IS DISTINCT FROM 'array' OR
    jsonb_array_length(NEW.payload->'observations') NOT BETWEEN 1 AND 2
 THEN RAISE EXCEPTION 'Invalid historical provenance'; END IF;
 FOR item IN SELECT * FROM jsonb_array_elements(NEW.payload->'observations') LOOP
  IF NOT (item ?& ARRAY['metric','source_value','source_unit','actual','currency','reporting_standard','methodology','share_basis','decimal_places']) OR
     coalesce(item->>'metric','') NOT IN ('revenue','reported_diluted_eps') OR item->>'metric'=ANY(seen) OR
     item->>'currency' IS DISTINCT FROM NEW.payload->>'currency' OR
     item->>'reporting_standard' IS DISTINCT FROM NEW.payload->>'reporting_standard' OR
     coalesce(item->>'source_value','') !~ '^-?[0-9]+(\.[0-9]+)?$' OR
     coalesce(item->>'decimal_places','') !~ '^[0-6]$' OR
     scale((item->>'source_value')::numeric) > (item->>'decimal_places')::integer
  THEN RAISE EXCEPTION 'Invalid historical metric'; END IF;
  seen:=array_append(seen,item->>'metric');
  IF item->>'metric'='revenue' THEN
   expected:=(item->>'source_value')::numeric * CASE item->>'source_unit'
    WHEN 'units' THEN 1 WHEN 'thousands' THEN 1000 WHEN 'millions' THEN 1000000 WHEN 'billions' THEN 1000000000 ELSE NULL END;
   IF expected IS NULL OR expected<0 OR item->>'methodology' IS DISTINCT FROM 'consolidated_revenue'
    OR item->>'share_basis' IS DISTINCT FROM 'not_applicable' THEN RAISE EXCEPTION 'Invalid historical revenue'; END IF;
  ELSE
   expected:=(item->>'source_value')::numeric;
   IF item->>'source_unit' IS DISTINCT FROM 'per_share' OR item->>'methodology' IS DISTINCT FROM 'reported_diluted_total_eps'
    OR coalesce(item->>'share_basis','') NOT IN ('common_share','ordinary_share') THEN RAISE EXCEPTION 'Invalid historical EPS'; END IF;
  END IF;
  IF (item->>'actual')::numeric IS DISTINCT FROM expected THEN RAISE EXCEPTION 'Historical scaling mismatch'; END IF;
 END LOOP;
 RETURN NEW;
END $$;
CREATE TRIGGER earnings_history_insert BEFORE INSERT ON earnings_historical_reports FOR EACH ROW EXECUTE FUNCTION earnings_history_guard();
CREATE TRIGGER earnings_history_immutable BEFORE UPDATE OR DELETE ON earnings_historical_reports FOR EACH ROW EXECUTE FUNCTION earnings_history_guard();
CREATE TRIGGER earnings_history_no_truncate BEFORE TRUNCATE ON earnings_historical_reports FOR EACH STATEMENT EXECUTE FUNCTION earnings_history_guard();
