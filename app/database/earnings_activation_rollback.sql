-- Recovery plan only. Never run automatically. Requires separate confirmation.
-- Only appropriate for undoing this E2A activation before later Earnings stages.
-- No CASCADE: unexpected external dependencies must stop recovery for review.
BEGIN;
SET LOCAL lock_timeout TO '5s';
SELECT pg_advisory_xact_lock(726530019);
SELECT pg_advisory_xact_lock(726530020);
DROP TABLE public.earnings_date_confirmations, public.earnings_source_evidence,
 public.earnings_events, public.earnings_periods, public.earnings_company_aliases,
 public.earnings_companies;
DROP FUNCTION public.earnings_confirmation_transition();
DROP FUNCTION public.earnings_immutable();
COMMIT;
