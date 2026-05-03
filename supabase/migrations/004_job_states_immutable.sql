-- ============================================================
-- Migration 004: job_states immutability + retention fields
-- Uses trigger-based protection instead of REVOKE
-- Allows audit_admin role for archival operations
-- ============================================================

-- Add retention and archival fields
ALTER TABLE job_states
    ADD COLUMN IF NOT EXISTS archived_at
        TIMESTAMPTZ DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS retention_days
        INTEGER DEFAULT 90;

-- Trigger function: prevent UPDATE and DELETE
-- for non-admin roles
CREATE OR REPLACE FUNCTION prevent_job_state_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF current_user NOT IN ('audit_admin', 'postgres') THEN
        RAISE EXCEPTION
            'job_states is append-only. Mutations not permitted.';
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Attach trigger for DELETE
DROP TRIGGER IF EXISTS no_delete_job_states
    ON job_states;
CREATE TRIGGER no_delete_job_states
    BEFORE DELETE ON job_states
    FOR EACH ROW EXECUTE FUNCTION
        prevent_job_state_mutation();

-- Attach trigger for UPDATE
DROP TRIGGER IF EXISTS no_update_job_states
    ON job_states;
CREATE TRIGGER no_update_job_states
    BEFORE UPDATE ON job_states
    FOR EACH ROW EXECUTE FUNCTION
        prevent_job_state_mutation();

-- Index on archived_at for future archival queries
CREATE INDEX IF NOT EXISTS idx_job_states_archived_at
    ON job_states (archived_at)
    WHERE archived_at IS NULL;
