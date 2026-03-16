-- Scope document library: stores uploaded scope docs and their extractions
-- Run against Supabase SQL editor or via supabase db push

CREATE TABLE scope_documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  file_size_bytes integer,
  document_type text, -- 'scope', 'quote', 'tender_schedule', 'other'
  created_by uuid REFERENCES auth.users(id),
  created_at timestamptz DEFAULT now()
);

CREATE TABLE scope_extractions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid REFERENCES scope_documents(id),
  extracted_fields jsonb NOT NULL,
  user_corrections jsonb DEFAULT '{}',
  extraction_duration_ms integer,
  created_at timestamptz DEFAULT now()
);

-- RLS policies: users can only see their own documents
ALTER TABLE scope_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_extractions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own documents"
  ON scope_documents FOR SELECT
  USING (auth.uid() = created_by);

CREATE POLICY "Users insert own documents"
  ON scope_documents FOR INSERT
  WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Users see own extractions"
  ON scope_extractions FOR SELECT
  USING (document_id IN (
    SELECT id FROM scope_documents WHERE created_by = auth.uid()
  ));

CREATE POLICY "Users insert own extractions"
  ON scope_extractions FOR INSERT
  WITH CHECK (document_id IN (
    SELECT id FROM scope_documents WHERE created_by = auth.uid()
  ));
