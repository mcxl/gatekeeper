CREATE TABLE IF NOT EXISTS job_states (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id  TEXT NOT NULL,
    job_type        TEXT NOT NULL,
    -- job_type values: 'swms_generate', 'procore_review', 'render_docx', 'render_pdf'
    state           TEXT NOT NULL,
    -- state values: 'received', 'inference', 'generating', 'rendering',
    --               'complete', 'failed', 'escalated'
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_states_correlation_id
    ON job_states (correlation_id);

CREATE INDEX IF NOT EXISTS idx_job_states_created_at
    ON job_states (created_at DESC);

-- Row-level security: users see only their own jobs
ALTER TABLE job_states ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own jobs"
    ON job_states FOR SELECT
    USING (
        metadata->>'user_id' = auth.uid()::text
        OR metadata->>'api_key_id' IS NOT NULL
    );
