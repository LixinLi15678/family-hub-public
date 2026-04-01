-- Initial database setup for Family Hub
-- This script runs when the PostgreSQL container is first created

-- Enable UUID extension (if needed in future)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Insert default currencies
INSERT INTO currencies (code, name, symbol) VALUES
    ('USD', 'US Dollar', '$'),
    ('CNY', 'Chinese Yuan', '¥'),
    ('HKD', 'Hong Kong Dollar', 'HK$'),
    ('CAD', 'Canadian Dollar', 'C$'),
    ('JPY', 'Japanese Yen', '¥')
ON CONFLICT (code) DO NOTHING;

-- Insert default exchange rates (relative to USD)
-- These will be updated by the scheduled job
INSERT INTO exchange_rates (from_currency_id, to_currency_id, rate) VALUES
    ((SELECT id FROM currencies WHERE code = 'USD'), (SELECT id FROM currencies WHERE code = 'CNY'), 7.20),
    ((SELECT id FROM currencies WHERE code = 'USD'), (SELECT id FROM currencies WHERE code = 'HKD'), 7.80),
    ((SELECT id FROM currencies WHERE code = 'USD'), (SELECT id FROM currencies WHERE code = 'CAD'), 1.35),
    ((SELECT id FROM currencies WHERE code = 'USD'), (SELECT id FROM currencies WHERE code = 'JPY'), 149.00)
ON CONFLICT DO NOTHING;

