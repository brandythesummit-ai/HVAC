-- Seed data for testing the HVAC Lead Generation platform
-- Run this after all migrations are complete

-- Clear existing data (for development/testing only)
TRUNCATE TABLE leads, permits, sync_config, counties, agencies CASCADE;

-- Insert test agency
INSERT INTO agencies (id, name, summit_api_key, summit_location_id)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Test HVAC Agency',
    'test_summit_api_key_12345',  -- This would be encrypted by backend
    'summit_location_12345'
);

-- Insert two test counties
INSERT INTO counties (id, agency_id, name, accela_environment, accela_app_id, accela_app_secret, status, is_active)
VALUES
(
    '00000000-0000-0000-0000-000000000101',
    '00000000-0000-0000-0000-000000000001',
    'Orange County',
    'PROD',
    'test_app_id_orange',
    'test_app_secret_orange',  -- This would be encrypted by backend
    'connected',
    true
),
(
    '00000000-0000-0000-0000-000000000102',
    '00000000-0000-0000-0000-000000000001',
    'Los Angeles County',
    'PROD',
    'test_app_id_la',
    'test_app_secret_la',  -- This would be encrypted by backend
    'disconnected',
    true
);

-- Insert sample permits for Orange County
INSERT INTO permits (
    id,
    county_id,
    accela_record_id,
    raw_data,
    permit_type,
    description,
    opened_date,
    status,
    job_value,
    property_address,
    year_built,
    square_footage,
    property_value,
    bedrooms,
    bathrooms,
    lot_size,
    owner_name,
    owner_phone,
    owner_email
)
VALUES
(
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000101',
    'MECH-2024-00001',
    '{"recordId": "MECH-2024-00001", "type": "Mechanical", "module": "Building", "status": "Finaled"}',
    'Mechanical',
    'HVAC Replacement - Full System',
    '2024-01-15',
    'Finaled',
    15000.00,
    '123 Main St, Irvine, CA 92602',
    1995,
    2400,
    850000.00,
    4,
    2.5,
    7500.00,
    'John Smith',
    '(949) 555-0101',
    'john.smith@email.com'
),
(
    '00000000-0000-0000-0000-000000000202',
    '00000000-0000-0000-0000-000000000101',
    'MECH-2024-00002',
    '{"recordId": "MECH-2024-00002", "type": "Mechanical", "module": "Building", "status": "Finaled"}',
    'Mechanical',
    'AC Unit Installation',
    '2024-02-20',
    'Finaled',
    8500.00,
    '456 Oak Ave, Santa Ana, CA 92701',
    1988,
    1800,
    625000.00,
    3,
    2.0,
    6000.00,
    'Maria Garcia',
    '(714) 555-0202',
    'maria.garcia@email.com'
),
(
    '00000000-0000-0000-0000-000000000203',
    '00000000-0000-0000-0000-000000000101',
    'MECH-2024-00003',
    '{"recordId": "MECH-2024-00003", "type": "Mechanical", "module": "Building", "status": "Issued"}',
    'Mechanical',
    'Furnace Replacement',
    '2024-03-10',
    'Issued',
    5500.00,
    '789 Elm Dr, Costa Mesa, CA 92626',
    2005,
    2100,
    725000.00,
    3,
    2.0,
    5500.00,
    'Robert Johnson',
    '(949) 555-0303',
    NULL  -- No email available
),
(
    '00000000-0000-0000-0000-000000000204',
    '00000000-0000-0000-0000-000000000101',
    'MECH-2024-00004',
    '{"recordId": "MECH-2024-00004", "type": "Mechanical", "module": "Building", "status": "Finaled"}',
    'Mechanical',
    'HVAC System Upgrade',
    '2024-04-05',
    'Finaled',
    22000.00,
    '321 Beach Blvd, Newport Beach, CA 92660',
    2010,
    3200,
    1450000.00,
    5,
    3.5,
    9000.00,
    'Sarah Williams',
    '(949) 555-0404',
    'sarah.w@email.com'
);

-- Insert sample permits for LA County
INSERT INTO permits (
    id,
    county_id,
    accela_record_id,
    raw_data,
    permit_type,
    description,
    opened_date,
    status,
    job_value,
    property_address,
    year_built,
    square_footage,
    property_value,
    bedrooms,
    bathrooms,
    lot_size,
    owner_name,
    owner_phone,
    owner_email
)
VALUES
(
    '00000000-0000-0000-0000-000000000205',
    '00000000-0000-0000-0000-000000000102',
    'MECH-2024-10001',
    '{"recordId": "MECH-2024-10001", "type": "Mechanical", "module": "Building", "status": "Finaled"}',
    'Mechanical',
    'Central AC Installation',
    '2024-01-25',
    'Finaled',
    12000.00,
    '555 Hollywood Blvd, Los Angeles, CA 90028',
    1975,
    2000,
    950000.00,
    3,
    2.0,
    5000.00,
    'David Lee',
    '(323) 555-0505',
    'david.lee@email.com'
);

-- Create leads from some permits
INSERT INTO leads (id, permit_id, county_id, summit_sync_status, summit_contact_id, summit_synced_at, notes)
VALUES
(
    '00000000-0000-0000-0000-000000000301',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000101',
    'synced',
    'summit_contact_abc123',
    NOW() - INTERVAL '2 days',
    'High value customer - successful sync'
),
(
    '00000000-0000-0000-0000-000000000302',
    '00000000-0000-0000-0000-000000000202',
    '00000000-0000-0000-0000-000000000101',
    'pending',
    NULL,
    NULL,
    'Ready to sync'
),
(
    '00000000-0000-0000-0000-000000000303',
    '00000000-0000-0000-0000-000000000203',
    '00000000-0000-0000-0000-000000000101',
    'failed',
    NULL,
    NULL,
    'Sync failed - missing email address'
),
(
    '00000000-0000-0000-0000-000000000304',
    '00000000-0000-0000-0000-000000000204',
    '00000000-0000-0000-0000-000000000101',
    'pending',
    NULL,
    NULL,
    'Premium property - prioritize'
),
(
    '00000000-0000-0000-0000-000000000305',
    '00000000-0000-0000-0000-000000000205',
    '00000000-0000-0000-0000-000000000102',
    'synced',
    'summit_contact_xyz789',
    NOW() - INTERVAL '5 days',
    'LA County lead - synced successfully'
);

-- Create sync configuration for the test agency
INSERT INTO sync_config (agency_id, sync_mode, schedule_cron, is_active)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'manual',
    NULL,  -- No schedule for manual mode
    true
);

-- Display summary
SELECT 'Database seeded successfully!' AS status;
SELECT 'Agencies:', COUNT(*) FROM agencies;
SELECT 'Counties:', COUNT(*) FROM counties;
SELECT 'Permits:', COUNT(*) FROM permits;
SELECT 'Leads:', COUNT(*) FROM leads;
SELECT 'Sync Configs:', COUNT(*) FROM sync_config;
