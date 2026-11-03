-- E2C isolated, explicit timezone extension; no macro objects or data changes.
ALTER TABLE earnings_date_confirmations
 DROP CONSTRAINT earnings_date_confirmations_source_timezone_check;
ALTER TABLE earnings_date_confirmations
 ADD CONSTRAINT earnings_date_confirmations_source_timezone_check CHECK
 (source_timezone IN ('America/New_York','America/Los_Angeles','America/Chicago',
  'America/Denver','America/Toronto','Europe/Amsterdam','Europe/London','Asia/Taipei','Etc/UTC'));
