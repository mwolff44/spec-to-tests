CREATE TABLE IF NOT EXISTS tariffs (
    id              SERIAL PRIMARY KEY,
    prefix          VARCHAR(20)  NOT NULL,
    rate_per_minute INTEGER      NOT NULL CHECK (rate_per_minute >= 0),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (prefix)
);

CREATE INDEX IF NOT EXISTS tariffs_prefix_idx ON tariffs (prefix);
