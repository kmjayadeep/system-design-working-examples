CREATE TABLE IF NOT EXISTS venues (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS performers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    venue_id TEXT NOT NULL REFERENCES venues(id),
    performer_id TEXT NOT NULL REFERENCES performers(id),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_category_starts_at ON events (category, starts_at);

CREATE TABLE IF NOT EXISTS reservations (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_id TEXT NOT NULL REFERENCES events(id),
    status TEXT NOT NULL,
    total_price NUMERIC(12, 2) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(id),
    section TEXT NOT NULL,
    seat_row TEXT NOT NULL,
    seat_number INTEGER NOT NULL,
    price NUMERIC(12, 2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    reservation_id UUID NULL REFERENCES reservations(id),
    reserved_until TIMESTAMPTZ NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_event_status ON tickets (event_id, status);

CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY,
    reservation_id UUID NOT NULL REFERENCES reservations(id),
    user_id TEXT NOT NULL,
    event_id TEXT NOT NULL REFERENCES events(id),
    total_price NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO venues (id, name, city) VALUES
    ('venue-sf', 'Civic Hall', 'San Francisco'),
    ('venue-nyc', 'North Arena', 'New York')
ON CONFLICT DO NOTHING;

INSERT INTO performers (id, name) VALUES
    ('perf-jazz', 'The Distributed Jazz Quartet'),
    ('perf-rock', 'Replica Rock')
ON CONFLICT DO NOTHING;

INSERT INTO events (id, venue_id, performer_id, name, category, starts_at) VALUES
    ('evt-jazz', 'venue-sf', 'perf-jazz', 'Distributed Jazz Night', 'concert', now() + interval '14 days'),
    ('evt-rock', 'venue-nyc', 'perf-rock', 'Replica Rock Live', 'concert', now() + interval '21 days')
ON CONFLICT DO NOTHING;

INSERT INTO tickets (id, event_id, section, seat_row, seat_number, price) VALUES
    ('t-jazz-a1', 'evt-jazz', 'A', '1', 1, 125.00),
    ('t-jazz-a2', 'evt-jazz', 'A', '1', 2, 125.00),
    ('t-jazz-b1', 'evt-jazz', 'B', '4', 1, 80.00),
    ('t-rock-a1', 'evt-rock', 'A', '1', 1, 95.00)
ON CONFLICT DO NOTHING;
