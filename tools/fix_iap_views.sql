-- Comprehensive fix for IAP account views
-- Run as PostgreSQL superuser or database owner
-- Example: psql -U odoo -d odoo -f fix_iap_views.sql

-- First rollback any existing transaction
ROLLBACK;

-- Show all iap.account views before any changes
SELECT id, name, type, arch_db::text
FROM ir_ui_view
WHERE model = 'iap.account';

-- Step 1: Remove GatewayAPI fields from ir_model_fields
DELETE FROM ir_model_fields 
WHERE model = 'iap.account' 
AND name LIKE 'gatewayapi_%';

-- Step 2: Fix any invalid or empty tree views first
UPDATE ir_ui_view
SET arch_db = '{"arch": "<tree string=\"IAP Account\"><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></tree>"}'::jsonb
WHERE model = 'iap.account'
AND type = 'tree'
AND (
    arch_db IS NULL 
    OR arch_db::text = '{}' 
    OR arch_db::text = '{"arch": ""}' 
    OR arch_db::text NOT LIKE '%<tree%'
    OR arch_db::text NOT LIKE '%</tree>%'
);

-- Step 3: Fix any invalid or empty form views
UPDATE ir_ui_view
SET arch_db = '{"arch": "<form string=\"IAP Account\"><sheet><group><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></group></sheet></form>"}'::jsonb
WHERE model = 'iap.account'
AND type = 'form'
AND (
    arch_db IS NULL 
    OR arch_db::text = '{}' 
    OR arch_db::text = '{"arch": ""}' 
    OR arch_db::text NOT LIKE '%<form%'
    OR arch_db::text NOT LIKE '%</form>%'
);

-- Step 4: Fix valid tree views - remove GatewayAPI fields
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<field name="gatewayapi_[^"]*"[^/>]*/?>', 
    '', 
    'g'))
WHERE model = 'iap.account'
AND type = 'tree'
AND arch_db IS NOT NULL
AND arch_db::text LIKE '%<tree%'
AND arch_db::text LIKE '%</tree>%'
AND arch_db::text LIKE '%gatewayapi%';

-- Step 5: Fix valid form views - remove GatewayAPI fields
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<field name="gatewayapi_[^"]*"[^/>]*/?>', 
    '', 
    'g'))
WHERE model = 'iap.account'
AND type = 'form'
AND arch_db IS NOT NULL
AND arch_db::text LIKE '%<form%'
AND arch_db::text LIKE '%</form>%'
AND arch_db::text LIKE '%gatewayapi%';

-- Step 6: Fix form views - remove GatewayAPI groups
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<group[^>]*>(<[^>]*>)*[^<]*gatewayapi[^<]*(<[^>]*>)*</group>', 
    '', 
    'g'))
WHERE model = 'iap.account'
AND type = 'form'
AND arch_db IS NOT NULL
AND arch_db::text LIKE '%<form%'
AND arch_db::text LIKE '%</form>%'
AND arch_db::text LIKE '%gatewayapi%';

-- Step 7: More aggressive group cleanup for form views
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<group[^>]*string="GatewayAPI[^"]*"[^>]*>.*?</group>', 
    '', 
    'gs'))
WHERE model = 'iap.account'
AND type = 'form'
AND arch_db IS NOT NULL
AND arch_db::text LIKE '%<form%'
AND arch_db::text LIKE '%</form>%'
AND arch_db::text LIKE '%GatewayAPI%';

-- Step 8: Delete any ir_model_data entries related to GatewayAPI
DELETE FROM ir_model_data 
WHERE (name LIKE '%gatewayapi%' OR name LIKE '%sms_api_gatewayapi%')
AND model = 'ir.ui.view';

-- Step 9: Force clear view cache - check table structure first
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

-- Step 10: Clear server-side caches
UPDATE ir_model_data
SET noupdate = false
WHERE model = 'ir.ui.view' 
AND res_id IN (SELECT id FROM ir_ui_view WHERE model = 'iap.account');

-- Verify all views are now valid
SELECT id, name, type, arch_db::text
FROM ir_ui_view
WHERE model = 'iap.account';

-- Commit the changes
COMMIT;

-- Output message
\echo 'Comprehensive fix of IAP account views complete!';
\echo 'Please restart your Odoo server to see the changes.'; 