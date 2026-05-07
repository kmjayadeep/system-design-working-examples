CREATE TABLE IF NOT EXISTS activities (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    status TEXT NOT NULL,
    distance_km DOUBLE PRECISION NOT NULL DEFAULT 0,
    elapsed_seconds INTEGER NOT NULL DEFAULT 0,
    point_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS idx_activities_user_ended_at ON activities (user_id, ended_at DESC);

CREATE TABLE IF NOT EXISTS activity_points (
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (activity_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS friendships (
    user_id TEXT NOT NULL,
    friend_id TEXT NOT NULL,
    PRIMARY KEY (user_id, friend_id)
);

INSERT INTO friendships (user_id, friend_id) VALUES
    ('alice', 'bob'),
    ('bob', 'alice')
ON CONFLICT DO NOTHING;
