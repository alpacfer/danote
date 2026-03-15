ALTER TABLE wordbank_verification_records
ADD COLUMN review_intent TEXT NOT NULL DEFAULT 'general';

ALTER TABLE wordbank_verification_records
ADD COLUMN latest_snapshot_hash TEXT;

ALTER TABLE wordbank_verification_records
ADD COLUMN request_generation INTEGER NOT NULL DEFAULT 0;

ALTER TABLE wordbank_background_jobs
ADD COLUMN rerun_requested INTEGER NOT NULL DEFAULT 0;
