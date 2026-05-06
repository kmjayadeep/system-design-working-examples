CREATE TABLE publishers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE articles (
    id UUID PRIMARY KEY,
    publisher_id TEXT NOT NULL REFERENCES publishers(id),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    category TEXT NOT NULL,
    publisher_url TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_articles_feed ON articles (published_at DESC, id DESC);
CREATE INDEX idx_articles_category_feed ON articles (category, published_at DESC, id DESC);

INSERT INTO publishers (id, name) VALUES
    ('daily-planet', 'Daily Planet'),
    ('tech-wire', 'Tech Wire')
ON CONFLICT DO NOTHING;

INSERT INTO articles (id, publisher_id, title, summary, category, publisher_url, published_at) VALUES
    ('00000000-0000-0000-0000-000000000001', 'daily-planet', 'Markets Open Higher', 'Stocks rose in early trading.', 'business', 'https://publisher.example/markets', '2026-05-06T10:00:00Z'),
    ('00000000-0000-0000-0000-000000000002', 'tech-wire', 'New Database Released', 'A new distributed database was announced.', 'technology', 'https://publisher.example/database', '2026-05-06T10:01:00Z'),
    ('00000000-0000-0000-0000-000000000003', 'daily-planet', 'Local Team Wins', 'The local team won their final match.', 'sports', 'https://publisher.example/sports', '2026-05-06T10:02:00Z')
ON CONFLICT DO NOTHING;
