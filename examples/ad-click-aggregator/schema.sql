CREATE TABLE ads (
    id TEXT PRIMARY KEY,
    advertiser_id TEXT NOT NULL,
    target_url TEXT NOT NULL
);

CREATE TABLE click_events (
    click_id TEXT PRIMARY KEY,
    ad_id TEXT NOT NULL REFERENCES ads(id),
    user_id TEXT NOT NULL,
    clicked_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE click_aggregates (
    ad_id TEXT NOT NULL REFERENCES ads(id),
    minute_bucket TIMESTAMPTZ NOT NULL,
    click_count INTEGER NOT NULL,
    unique_users INTEGER NOT NULL,
    PRIMARY KEY (ad_id, minute_bucket)
);

INSERT INTO ads (id, advertiser_id, target_url) VALUES
    ('ad-1', 'advertiser-1', 'https://advertiser.example/landing'),
    ('ad-2', 'advertiser-1', 'https://advertiser.example/sale')
ON CONFLICT DO NOTHING;
