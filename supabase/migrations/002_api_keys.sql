create table if not exists api_keys (
  id uuid primary key default gen_random_uuid(),
  key text unique not null,
  name text not null,
  user_id uuid references auth.users(id),
  active boolean default true,
  created_at timestamptz default now()
);

create table if not exists api_key_usage (
  id uuid primary key default gen_random_uuid(),
  key_id uuid references api_keys(id),
  endpoint text,
  description_length int,
  duration_ms int,
  success boolean,
  created_at timestamptz default now()
);

create index on api_key_usage (key_id, created_at desc);
