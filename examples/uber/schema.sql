CREATE TABLE drivers (
    id TEXT PRIMARY KEY,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('available', 'requested', 'busy', 'offline')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE rides (
    id UUID PRIMARY KEY,
    rider_id TEXT NOT NULL,
    driver_id TEXT REFERENCES drivers(id),
    start_lat DOUBLE PRECISION NOT NULL,
    start_lng DOUBLE PRECISION NOT NULL,
    dest_lat DOUBLE PRECISION NOT NULL,
    dest_lng DOUBLE PRECISION NOT NULL,
    estimated_fare DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('requested', 'accepted', 'declined', 'completed', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX drivers_status_idx ON drivers(status);
CREATE INDEX rides_rider_id_idx ON rides(rider_id);
