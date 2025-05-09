-- Force cleanup of GatewayAPI elements from views
-- Run as PostgreSQL superuser or database owner
-- Example: psql -U odoo -d odoo -f force_cleanup.sql

-- First rollback any existing transaction
ROLLBACK;

-- Step 1: Remove any GatewayAPI fields from ir_model_fields
DELETE FROM ir_model_fields 
WHERE model = 'iap.account' 
AND name LIKE 'gatewayapi_%';

-- Step 2: Clean tree views - remove GatewayAPI columns
UPDATE ir_ui_view
SET arch_db = regexp_replace(arch_db, 
    '<field name="gatewayapi_[^"]*"[^/>]*/?>', 
    '', 
    'g')
WHERE model = 'iap.account'
AND type = 'tree';

-- Step 3: Clean decoration attributes in tree views
UPDATE ir_ui_view
SET arch_db = regexp_replace(arch_db, 
    'decoration-info="[^"]*gatewayapi[^"]*"', 
    'decoration-info=""', 
    'g')
WHERE model = 'iap.account'
AND type = 'tree';

-- Step 4: Clean form views - remove GatewayAPI fields
UPDATE ir_ui_view
SET arch_db = regexp_replace(arch_db, 
    '<field name="gatewayapi_[^"]*"[^/>]*/?>', 
    '', 
    'g')
WHERE model = 'iap.account'
AND type = 'form';

-- Step 5: Clean form views - remove GatewayAPI groups
-- This is trickier since we need to match balanced tags, but we'll try a basic approach
UPDATE ir_ui_view
SET arch_db = regexp_replace(arch_db, 
    '<group[^>]*>(<[^>]*>)*[^<]*gatewayapi[^<]*(<[^>]*>)*</group>', 
    '', 
    'g')
WHERE model = 'iap.account'
AND type = 'form';

-- Step 6: More aggressive group cleanup for form views
UPDATE ir_ui_view
SET arch_db = regexp_replace(arch_db, 
    '<group[^>]*string="GatewayAPI[^"]*"[^>]*>.*?</group>', 
    '', 
    'gs')
WHERE model = 'iap.account'
AND type = 'form';

-- Step 7: Clean up any search views with GatewayAPI fields
UPDATE ir_ui_view
SET arch_db = regexp_replace(arch_db, 
    '<field name="gatewayapi_[^"]*"[^/>]*/?>', 
    '', 
    'g')
WHERE model = 'iap.account'
AND type = 'search';

-- Step 8: Clean up domain filters that reference GatewayAPI fields
UPDATE ir_ui_view
SET arch_db = regexp_replace(arch_db, 
    'domain=".*?gatewayapi.*?"', 
    'domain="[]"', 
    'g')
WHERE arch_db LIKE '%domain=%gatewayapi%';

-- Step 9: Clean up invisible fields in other views
UPDATE ir_ui_view
SET arch_db = regexp_replace(arch_db, 
    '<field name="gatewayapi[^"]*" invisible="1"[^/>]*/?>', 
    '', 
    'g')
WHERE arch_db LIKE '%gatewayapi%';

-- Step 10: Delete any ir_model_data entries related to GatewayAPI
DELETE FROM ir_model_data 
WHERE (name LIKE '%gatewayapi%' OR name LIKE '%sms_api_gatewayapi%') 
AND model = 'ir.ui.view';

-- Commit the changes
COMMIT;

-- Output message
\echo 'Direct cleanup of GatewayAPI elements complete!'; 