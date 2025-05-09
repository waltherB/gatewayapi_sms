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
        
        -- Remove GatewayAPI Base URL column
        UPDATE ir_ui_view 
        SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
            '<field name="GatewayAPI Base URL"[^/>]*/?>', 
            '', 
            'g'))
        WHERE id = view_record.id;
        
        -- Remove Gatewayapi Api Token column
        UPDATE ir_ui_view 
        SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
            '<field name="Gatewayapi Api Token"[^/>]*/?>', 
            '', 
            'g'))
        WHERE id = view_record.id;
    END LOOP;
END$$;

-- Show the updated views
SELECT id, name, arch_db::text 
FROM ir_ui_view 
WHERE model = 'iap.account' 
AND type = 'tree';

-- Manually remove field references for the column "GatewayAPI Base URL"
UPDATE ir_ui_view 
SET arch_db = to_jsonb(REPLACE(arch_db::text, 
    'GatewayAPI Base URL', 
    'Removed'))
WHERE model = 'iap.account' 
AND type = 'tree'
AND arch_db::text LIKE '%GatewayAPI Base URL%';

-- Manually remove field references for the column "Gatewayapi Api Token"
UPDATE ir_ui_view 
SET arch_db = to_jsonb(REPLACE(arch_db::text, 
    'Gatewayapi Api Token', 
    'Removed'))
WHERE model = 'iap.account' 
AND type = 'tree'
AND arch_db::text LIKE '%Gatewayapi Api Token%';

-- Directly fix tree view columns - aggressive approach
UPDATE ir_ui_view
SET arch_db = to_jsonb(regexp_replace(arch_db::text, 
    '<field name="[^"]*" invisible="[^"]*"[^/>]*/?>', 
    '', 
    'g'))
WHERE model = 'iap.account' 
AND type = 'tree';

-- Try a very direct XML approach for the main tree view
UPDATE ir_ui_view
SET arch_db = '{"arch": "<tree string=\"IAP Account\"><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></tree>"}'::jsonb
WHERE id IN (
    SELECT id FROM ir_ui_view
    WHERE model = 'iap.account'
    AND type = 'tree'
    AND arch_db::text LIKE '%GatewayAPI Base URL%'
    LIMIT 1
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