CREATE TABLE distribution_centers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    region_id TEXT NOT NULL
);

CREATE TABLE items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE inventory (
    dc_id TEXT NOT NULL REFERENCES distribution_centers(id),
    item_id TEXT NOT NULL REFERENCES items(id),
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (dc_id, item_id)
);

CREATE INDEX idx_inventory_item_id ON inventory (item_id);

CREATE TABLE orders (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    dc_id TEXT NOT NULL REFERENCES distribution_centers(id),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL REFERENCES items(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (order_id, item_id)
);

INSERT INTO distribution_centers (id, name, latitude, longitude, region_id) VALUES
    ('dc-sf-1', 'San Francisco SoMa DC', 37.7749, -122.4194, '941'),
    ('dc-sf-2', 'Oakland DC', 37.8044, -122.2712, '946'),
    ('dc-nyc-1', 'Manhattan DC', 40.7128, -74.0060, '100')
ON CONFLICT DO NOTHING;

INSERT INTO items (id, name, description) VALUES
    ('cheetos', 'Cheetos', 'Crunchy cheese snacks'),
    ('sparkling-water', 'Sparkling Water', 'Eight pack of sparkling water'),
    ('battery-aa', 'AA Batteries', 'Four pack of AA batteries')
ON CONFLICT DO NOTHING;

INSERT INTO inventory (dc_id, item_id, quantity) VALUES
    ('dc-sf-1', 'cheetos', 5),
    ('dc-sf-1', 'sparkling-water', 12),
    ('dc-sf-1', 'battery-aa', 2),
    ('dc-sf-2', 'cheetos', 3),
    ('dc-sf-2', 'sparkling-water', 4),
    ('dc-nyc-1', 'cheetos', 9),
    ('dc-nyc-1', 'battery-aa', 5)
ON CONFLICT DO NOTHING;
