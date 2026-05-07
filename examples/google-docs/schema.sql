CREATE TABLE documents (
    id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_shares (
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    permission TEXT NOT NULL CHECK (permission IN ('read', 'write')),
    PRIMARY KEY (document_id, user_id)
);

CREATE TABLE document_operations (
    id BIGSERIAL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    base_version BIGINT NOT NULL,
    new_version BIGINT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX document_operations_document_id_id_idx ON document_operations(document_id, id);
