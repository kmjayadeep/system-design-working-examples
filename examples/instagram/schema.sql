CREATE TABLE posts (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    caption TEXT NOT NULL,
    media_type TEXT NOT NULL CHECK (media_type IN ('photo', 'video')),
    object_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'published')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX posts_user_id_created_at_idx ON posts(user_id, created_at DESC);

CREATE TABLE follows (
    follower_id TEXT NOT NULL,
    followee_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (follower_id, followee_id)
);

CREATE INDEX follows_follower_id_idx ON follows(follower_id);
