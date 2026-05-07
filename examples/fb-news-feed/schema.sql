CREATE TABLE IF NOT EXISTS follows (
    follower_id TEXT NOT NULL,
    followed_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, followed_id)
);
CREATE INDEX IF NOT EXISTS idx_follows_followed ON follows (followed_id, follower_id);

CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY,
    author_id TEXT NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_posts_author_created ON posts (author_id, created_at DESC);

CREATE TABLE IF NOT EXISTS feed_items (
    user_id TEXT NOT NULL,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, post_id)
);
CREATE INDEX IF NOT EXISTS idx_feed_items_user_created ON feed_items (user_id, created_at DESC);

INSERT INTO follows (follower_id, followed_id) VALUES
    ('alice', 'bob'),
    ('alice', 'carol'),
    ('dave', 'bob')
ON CONFLICT DO NOTHING;
