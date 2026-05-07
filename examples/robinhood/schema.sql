CREATE TABLE accounts (
    user_id TEXT PRIMARY KEY,
    cash_cents BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE holdings (
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quantity BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, symbol)
);

CREATE TABLE orders (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity BIGINT NOT NULL,
    price_cents BIGINT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('filled', 'rejected')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO accounts (user_id, cash_cents) VALUES ('alice', 1000000), ('bob', 500000);
INSERT INTO holdings (user_id, symbol, quantity) VALUES ('alice', 'AAPL', 10), ('bob', 'MSFT', 5);

