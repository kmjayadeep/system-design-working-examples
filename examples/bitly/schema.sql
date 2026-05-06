CREATE TABLE IF NOT EXISTS short_urls (
    short_code TEXT PRIMARY KEY,
    long_url TEXT NOT NULL,
    custom_alias BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_short_urls_expires_at
    ON short_urls (expires_at)
    WHERE expires_at IS NOT NULL;
