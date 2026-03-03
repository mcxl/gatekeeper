#!/usr/bin/env python3
import os
import sqlite3

_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_dir, 'gatekeeper.db')
SCHEMA_PATH = os.path.join(_dir, 'schema.sql')

with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
    schema = f.read()

conn = sqlite3.connect(DB_PATH)
conn.executescript(schema)
conn.commit()
conn.close()

print("Database initialised")
