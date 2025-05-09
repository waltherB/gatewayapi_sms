-- Force cleanup of GatewayAPI elements from views - JSONB version
-- Run as PostgreSQL superuser or database owner
-- Example: psql -U odoo -d odoo -f force_cleanup_jsonb.sql

-- First rollback any existing transaction
ROLLBACK;

-- Step 1: Remove any GatewayAPI fields from ir_model_fields (this worked fine)
DELETE FROM ir_model_fields 
WHERE model = 'iap.account' 
AND name LIKE 'gatewayapi_%';

-- Step 2: Clean tree views - remove GatewayAPI columns
-- Using conversion to text and back to jsonb
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<field name="gatewayapi_[^"]*"[^/>]*/?>', 
    '', 
    'g'))
WHERE model = 'iap.account'
AND type = 'tree'
AND arch_db::text LIKE '%gatewayapi%';

-- Step 3: Clean decoration attributes in tree views
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    'decoration-info="[^"]*gatewayapi[^"]*"', 
    'decoration-info=""', 
    'g'))
WHERE model = 'iap.account'
AND type = 'tree'
AND arch_db::text LIKE '%decoration-info%' AND arch_db::text LIKE '%gatewayapi%';

-- Step 4: Clean form views - remove GatewayAPI fields
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<field name="gatewayapi_[^"]*"[^/>]*/?>', 
    '', 
    'g'))
WHERE model = 'iap.account'
AND type = 'form'
AND arch_db::text LIKE '%gatewayapi%';

-- Step 5: Clean form views - remove GatewayAPI groups
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<group[^>]*>(<[^>]*>)*[^<]*gatewayapi[^<]*(<[^>]*>)*</group>', 
    '', 
    'g'))
WHERE model = 'iap.account'
AND type = 'form'
AND arch_db::text LIKE '%gatewayapi%';

-- Step 6: More aggressive group cleanup for form views
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<group[^>]*string="GatewayAPI[^"]*"[^>]*>.*?</group>', 
    '', 
    'gs'))
WHERE model = 'iap.account'
AND type = 'form'
AND arch_db::text LIKE '%GatewayAPI%';

-- Step 7: Clean up any search views with GatewayAPI fields
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<field name="gatewayapi_[^"]*"[^/>]*/?>', 
    '', 
    'g'))
WHERE model = 'iap.account'
AND type = 'search'
AND arch_db::text LIKE '%gatewayapi%';

-- Step 8: Clean up domain filters that reference GatewayAPI fields
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    'domain=".*?gatewayapi.*?"', 
    'domain="[]"', 
    'g'))
WHERE arch_db::text LIKE '%domain%' AND arch_db::text LIKE '%gatewayapi%';

-- Step 9: Clean up invisible fields in other views
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<field name="gatewayapi[^"]*" invisible="1"[^/>]*/?>', 
    '', 
    'g'))
WHERE arch_db::text LIKE '%gatewayapi%';

-- Step 10: Clean up nodes that contain gatewayapi attributes
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<[^>]*gatewayapi[^>]*>.*?</[^>]*>', 
    '', 
    'gs'))
WHERE arch_db::text LIKE '%gatewayapi%';

-- Step 11: Delete any ir_model_data entries related to GatewayAPI
DELETE FROM ir_model_data 
WHERE (name LIKE '%gatewayapi%' OR name LIKE '%sms_api_gatewayapi%')
AND model = 'ir.ui.view';

-- Step 12: Force clear view cache - check table structure first
DO $$
BEGIN
  -- Check if view_id column exists in ir_ui_view_custom
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name='ir_ui_view_custom' AND column_name='view_id'
  ) THEN
    -- If view_id exists, use it
    EXECUTE 'DELETE FROM ir_ui_view_custom WHERE view_id IN (SELECT id FROM ir_ui_view WHERE model = ''iap.account'')';
  ELSIF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name='ir_ui_view_custom' AND column_name='ref_id'
  ) THEN
    -- If ref_id exists, use that instead
    EXECUTE 'DELETE FROM ir_ui_view_custom WHERE ref_id IN (SELECT id FROM ir_ui_view WHERE model = ''iap.account'')';
  ELSE
    -- Otherwise, just report that we can't clear the cache
    RAISE NOTICE 'Could not clear view cache - ir_ui_view_custom table structure unknown';
  END IF;
END$$;

-- Step 13: Clean up XML content
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(regexp_replace(arch_db::text, 
    '<xpath[^>]*>.*?</xpath>', 
    '', 
    'gs'), 
    '>\s+<', 
    '><', 
    'g'))
WHERE model = 'iap.account' 
AND arch_db::text LIKE '%gatewayapi%';

-- Step 14: Direct column name removal - this is a last resort approach
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    'GatewayAPI Base URL', 
    '', 
    'g'))
WHERE arch_db::text LIKE '%GatewayAPI Base URL%';

UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    'Gatewayapi Api Token', 
    '', 
    'g'))
WHERE arch_db::text LIKE '%Gatewayapi Api Token%';

-- Commit the changes
COMMIT;

-- Output message
\echo 'Direct cleanup of GatewayAPI elements for JSONB arch_db complete!';
\echo 'Please restart your Odoo server to see the changes.'; 