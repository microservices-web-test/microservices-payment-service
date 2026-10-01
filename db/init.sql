-- Payment service database schema + seed data.
-- Runs automatically the first time the payment-db container is created.
CREATE TABLE IF NOT EXISTS transactions (
  id     SERIAL PRIMARY KEY,
  amount NUMERIC(10,2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'success'
);

INSERT INTO transactions (amount, status)
VALUES (9.99, 'success'), (19.95, 'success'), (4.50, 'success');
