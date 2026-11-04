-- Separate dated issuer-equity snapshots; never earnings or macro observations.
CREATE TABLE earnings_market_cap_snapshots (
 snapshot_id uuid PRIMARY KEY,
 company_id uuid NOT NULL REFERENCES earnings_companies(company_id),
 cik text NOT NULL CHECK (cik ~ '^[0-9]{10}$'),
 market_cap_usd numeric NOT NULL CHECK (market_cap_usd>0 AND market_cap_usd<'Infinity'::numeric),
 currency text NOT NULL CHECK (currency='USD'),
 as_of date NOT NULL,
 measured_at timestamptz,
 source_url text NOT NULL CHECK (source_url ~ '^https://'),
 source_id text NOT NULL CHECK (length(btrim(source_id))>0),
 source_version text NOT NULL CHECK (length(btrim(source_version))>0),
 method text NOT NULL CHECK (method='provider_reported_issuer_equity'),
 issuer_scope text NOT NULL CHECK (issuer_scope='whole_issuer_all_classes'),
 basis_evidence text NOT NULL CHECK (length(btrim(basis_evidence))>0),
 access_evidence text NOT NULL CHECK (length(btrim(access_evidence))>0),
 verified_on date NOT NULL CHECK (verified_on>=as_of),
 fingerprint text NOT NULL UNIQUE CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
 captured_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK (measured_at IS NULL OR (measured_at AT TIME ZONE 'UTC')::date=as_of),
 UNIQUE(company_id,source_id,as_of,source_version)
);
CREATE INDEX earnings_market_cap_latest ON earnings_market_cap_snapshots(company_id,as_of DESC,measured_at DESC);
CREATE FUNCTION earnings_market_cap_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'Market cap snapshots are append-only'; END IF;
 IF NOT EXISTS (SELECT 1 FROM earnings_companies WHERE company_id=NEW.company_id AND cik=NEW.cik)
 THEN RAISE EXCEPTION 'Market cap issuer mismatch'; END IF;
 IF NEW.verified_on>CURRENT_DATE OR NEW.measured_at>clock_timestamp()
 THEN RAISE EXCEPTION 'Future market cap evidence'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER earnings_market_cap_insert BEFORE INSERT ON earnings_market_cap_snapshots FOR EACH ROW EXECUTE FUNCTION earnings_market_cap_guard();
CREATE TRIGGER earnings_market_cap_immutable BEFORE UPDATE OR DELETE ON earnings_market_cap_snapshots FOR EACH ROW EXECUTE FUNCTION earnings_market_cap_guard();
CREATE TRIGGER earnings_market_cap_no_truncate BEFORE TRUNCATE ON earnings_market_cap_snapshots FOR EACH STATEMENT EXECUTE FUNCTION earnings_market_cap_guard();
