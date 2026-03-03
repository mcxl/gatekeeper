CREATE TABLE IF NOT EXISTS Tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    scope TEXT,
    version TEXT DEFAULT '1.0',
    status TEXT DEFAULT 'draft',        -- draft / approved / archived
    risk_pre TEXT,
    risk_post TEXT,
    ccvs_code TEXT,
    wah_applicable INTEGER DEFAULT 0,   -- 0/1 boolean
    source TEXT DEFAULT 'library',      -- library / ai-generated
    approved INTEGER DEFAULT 0,
    approved_by TEXT,
    approved_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES Tasks(id),
    control_type TEXT,                  -- hold_point / control / stop_work / admin / ppe
    content TEXT NOT NULL,
    order_index INTEGER DEFAULT 0,
    is_ai_generated INTEGER DEFAULT 0,
    reviewed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Responsibility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES Tasks(id),
    role TEXT,                          -- SUP / WKR / SUB / PM / OP
    obligation TEXT
);

CREATE TABLE IF NOT EXISTS AuditLog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT,                    -- GENERATED/APPROVED/RENDERED/VALIDATION_FAILED/
                                        -- LIBRARY_HIT/LIBRARY_MISS
    task_id INTEGER,
    user TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    inputs TEXT,
    output_hash TEXT,
    ai_unapproved INTEGER DEFAULT 0
);
