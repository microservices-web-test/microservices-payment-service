-- V1: initial payment schema + seed data.
-- Applied by the one-shot Flyway "migrate" container, which records it in the
-- flyway_schema_history table so it runs exactly once per database.
CREATE TABLE IF NOT EXISTS transactions (
  id     SERIAL PRIMARY KEY,
  amount NUMERIC(10,2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'success'
);

INSERT INTO transactions (amount, status)
VALUES (9.99, 'success'), (19.95, 'success'), (4.50, 'success');
