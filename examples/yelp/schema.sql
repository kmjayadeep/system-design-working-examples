CREATE TABLE businesses (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    review_count INTEGER NOT NULL DEFAULT 0,
    average_rating DOUBLE PRECISION NOT NULL DEFAULT 0
);

CREATE INDEX idx_businesses_category ON businesses (category);
CREATE INDEX idx_businesses_name_lower ON businesses (lower(name));

CREATE TABLE reviews (
    id UUID PRIMARY KEY,
    business_id TEXT NOT NULL REFERENCES businesses(id),
    user_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (business_id, user_id)
);

INSERT INTO businesses (id, name, category, latitude, longitude, review_count, average_rating) VALUES
    ('biz-1', 'Soma Tacos', 'restaurants', 37.7750, -122.4183, 2, 4.5),
    ('biz-2', 'Mission Coffee', 'cafes', 37.7599, -122.4148, 1, 4.0),
    ('biz-3', 'Oakland Bikes', 'shopping', 37.8044, -122.2711, 0, 0)
ON CONFLICT DO NOTHING;

INSERT INTO reviews (id, business_id, user_id, rating, text) VALUES
    ('00000000-0000-0000-0000-000000000001', 'biz-1', 'alice', 5, 'Great tacos.'),
    ('00000000-0000-0000-0000-000000000002', 'biz-1', 'bob', 4, 'Fast service.'),
    ('00000000-0000-0000-0000-000000000003', 'biz-2', 'carol', 4, 'Good espresso.')
ON CONFLICT DO NOTHING;
