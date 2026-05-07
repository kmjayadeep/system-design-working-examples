CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    interested_in TEXT NOT NULL,
    min_age INTEGER NOT NULL,
    max_age INTEGER NOT NULL,
    max_distance_km DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_profiles_age ON profiles (age);

CREATE TABLE IF NOT EXISTS swipes (
    swiping_user_id TEXT NOT NULL,
    target_user_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (swiping_user_id, target_user_id)
);
CREATE INDEX IF NOT EXISTS idx_swipes_target ON swipes (target_user_id, swiping_user_id);

CREATE TABLE IF NOT EXISTS matches (
    id UUID PRIMARY KEY,
    user_one TEXT NOT NULL,
    user_two TEXT NOT NULL,
    matched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_one, user_two)
);

INSERT INTO profiles (
    user_id, name, age, gender, interested_in, min_age, max_age,
    max_distance_km, latitude, longitude
) VALUES
    ('alice', 'Alice', 29, 'female', 'male', 24, 38, 15, 37.7749, -122.4194),
    ('bob', 'Bob', 31, 'male', 'female', 24, 38, 15, 37.7755, -122.4189),
    ('carol', 'Carol', 28, 'female', 'male', 24, 40, 10, 37.7840, -122.4090),
    ('dave', 'Dave', 42, 'male', 'female', 35, 55, 30, 37.8044, -122.2712)
ON CONFLICT DO NOTHING;
