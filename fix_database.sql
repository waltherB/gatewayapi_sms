-- Fix database after uninstalling GatewayAPI SMS module
-- Run this as the database user with access to the Odoo database
-- Example: psql -U odoo -d your_database_name -f fix_database.sql

-- First rollback any pending transactions
ROLLBACK;

-- Remove gatewayapi fields from ir_model_fields
DELETE FROM ir_model_fields 
WHERE model = 'iap.account' 
AND name LIKE 'gatewayapi_%';

-- Fix views by removing field references
UPDATE ir_ui_view
SET arch_db = regexp_replace(arch_db, 
    '<field name="gatewayapi_[^"]*"[^>]*>.*?</field>', 
    '', 
    'g')
WHERE model = 'iap.account'
AND arch_db LIKE '%gatewayapi%';

-- Replace group elements containing gatewayapi
UPDATE ir_ui_view
SET arch_db = regexp_replace(arch_db, 
    '<group[^>]*>.*?gatewayapi.*?</group>', 
    '', 
    'g')
WHERE model = 'iap.account'
AND arch_db LIKE '%gatewayapi%';

-- Clean up any server actions related to gatewayapi
DELETE FROM ir_actions 
WHERE name LIKE '%GatewayAPI%';

-- Fix model_data entries
DELETE FROM ir_model_data
WHERE name LIKE 'gatewayapi%' 
OR name LIKE '%gatewayapi%'
OR module = 'gatewayapi_sms';

-- Commit changes
COMMIT;

-- Output message
\echo 'Database cleanup completed. Please restart your Odoo server.' 