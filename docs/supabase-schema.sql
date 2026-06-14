-- Schema for the Supabase memory backend.
-- Run this in your Supabase project's SQL editor before setting
-- AGENT_MEMORY_BACKEND=supabase.

create table if not exists runs (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  goal        text        not null,
  approved    boolean     not null,
  score       integer,
  attempts    integer
);

-- The Planner reads recent runs ordered by recency.
create index if not exists runs_created_at_idx on runs (created_at desc);
