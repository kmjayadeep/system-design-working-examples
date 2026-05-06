CREATE TABLE videos (
    id UUID PRIMARY KEY,
    uploader_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    original_object_key TEXT NOT NULL UNIQUE,
    manifest_object_key TEXT NULL,
    status TEXT NOT NULL,
    upload_id TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE video_parts (
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    part_number INTEGER NOT NULL,
    size BIGINT NOT NULL,
    status TEXT NOT NULL,
    etag TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (video_id, part_number)
);

CREATE TABLE video_segments (
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    rendition TEXT NOT NULL,
    segment_number INTEGER NOT NULL,
    object_key TEXT NOT NULL UNIQUE,
    duration_seconds INTEGER NOT NULL,
    PRIMARY KEY (video_id, rendition, segment_number)
);
