CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS files (
  id SERIAL PRIMARY KEY,
  path TEXT UNIQUE NOT NULL,
  sha256 TEXT NOT NULL,
  kind TEXT NOT NULL,
  indexed_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
  id SERIAL PRIMARY KEY,
  file_id INT REFERENCES files(id) ON DELETE CASCADE,
  start_line INT NOT NULL,
  end_line INT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(384) NOT NULL
);

CREATE TABLE IF NOT EXISTS queries (
  id UUID PRIMARY KEY,
  question TEXT NOT NULL,
  status TEXT NOT NULL,
  answer_json JSONB,
  trace_json JSONB NOT NULL,
  latency_ms INT,
  tokens_in INT,
  tokens_out INT,
  created_at TIMESTAMPTZ DEFAULT now()
);
