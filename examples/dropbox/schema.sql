CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    size BIGINT NOT NULL,
    mime_type TEXT NOT NULL,
    object_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    upload_id TEXT NULL,
    fingerprint TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_files_owner_id ON files (owner_id);

CREATE TABLE IF NOT EXISTS file_parts (
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    part_number INTEGER NOT NULL,
    size BIGINT NOT NULL,
    status TEXT NOT NULL,
    etag TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (file_id, part_number)
);

CREATE TABLE IF NOT EXISTS file_shares (
    user_id TEXT NOT NULL,
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    shared_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, file_id)
);

CREATE INDEX IF NOT EXISTS idx_file_shares_file_id ON file_shares (file_id);

CREATE TABLE IF NOT EXISTS change_events (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    file_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_change_events_user_id_id ON change_events (user_id, id);
