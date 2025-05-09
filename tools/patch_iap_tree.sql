-- Direct patch for IAP account tree view
-- Run as PostgreSQL superuser or database owner
-- Example: psql -U odoo -d odoo -f patch_iap_tree.sql

-- First rollback any existing transaction
ROLLBACK;

-- Get all tree views for iap.account
SELECT id, name, arch_db::text 
FROM ir_ui_view 
WHERE model = 'iap.account' 
AND type = 'tree';

-- Fix the main tree view
DO $$
DECLARE
    view_record RECORD;
BEGIN
    -- For every tree view
    FOR view_record IN SELECT id, arch_db FROM ir_ui_view 
                      WHERE model = 'iap.account' 
                      AND type = 'tree'
    LOOP
        RAISE NOTICE 'Processing view id %', view_record.id;
        
        -- Check if arch_db is valid JSON with non-empty arch
        IF view_record.arch_db IS NULL OR view_record.arch_db::text = '{}' OR view_record.arch_db::text = '{"arch": ""}' OR view_record.arch_db::text NOT LIKE '%<tree%' THEN
            -- If invalid, replace with default tree view
            UPDATE ir_ui_view 
            SET arch_db = '{"arch": "<tree string=\"IAP Account\"><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></tree>"}'::jsonb
            WHERE id = view_record.id;
            
            RAISE NOTICE 'View % was invalid, replaced with default tree view', view_record.id;
        ELSE
            -- Remove GatewayAPI Base URL column
            UPDATE ir_ui_view 
            SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
                '<field name="gatewayapi_[^"]*"[^/>]*/?>', 
                '', 
                'g'))
            WHERE id = view_record.id;
        END IF;
    END LOOP;
END$$;

-- Show the updated views
SELECT id, name, arch_db::text 
FROM ir_ui_view 
WHERE model = 'iap.account' 
AND type = 'tree';

-- Manually remove field references for any remaining GatewayAPI columns
UPDATE ir_ui_view 
SET arch_db = to_jsonb(REPLACE(arch_db::text, 
    'GatewayAPI Base URL', 
    'Removed'))
WHERE model = 'iap.account' 
AND type = 'tree'
AND arch_db::text LIKE '%GatewayAPI Base URL%';

UPDATE ir_ui_view 
SET arch_db = to_jsonb(REPLACE(arch_db::text, 
    'Gatewayapi Api Token', 
    'Removed'))
WHERE model = 'iap.account' 
AND type = 'tree'
AND arch_db::text LIKE '%Gatewayapi Api Token%';

-- Ensure all tree views have valid XML structure
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

-- Force clear view cache
DELETE FROM ir_ui_view_custom
WHERE view_id IN (
    SELECT id FROM ir_ui_view WHERE model = 'iap.account'
);

-- Commit the changes
COMMIT;

-- Output message
\echo 'Direct patch of IAP account tree view complete!';
\echo 'Please restart your Odoo server to see the changes.'; 