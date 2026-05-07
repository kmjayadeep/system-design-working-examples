CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY,
    live_video_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_comments_video_created ON comments (live_video_id, created_at DESC);
