CREATE TABLE crawl_jobs (
    id UUID PRIMARY KEY,
    status TEXT NOT NULL,
    max_pages INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pages (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    host TEXT NOT NULL,
    status TEXT NOT NULL,
    http_status INTEGER NULL,
    raw_object_key TEXT NULL,
    text_object_key TEXT NULL,
    discovered_links TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, url)
);

CREATE INDEX idx_pages_job_status ON pages (job_id, status);
