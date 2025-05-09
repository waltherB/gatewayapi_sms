-- Fix empty tree view for iap.account
-- Run as PostgreSQL superuser or database owner
-- Example: psql -U odoo -d odoo -f fix_empty_tree_view.sql

-- First rollback any existing transaction
ROLLBACK;

-- Check for any empty tree views
SELECT id, name, arch_db::text
FROM ir_ui_view 
WHERE model = 'iap.account' 
AND type = 'tree'
AND (arch_db IS NULL OR arch_db::text = '' OR arch_db::text = '{}' OR arch_db::text = '{"arch": ""}');

-- Fix any tree views with empty arch_db
UPDATE ir_ui_view
SET arch_db = '{"arch": "<tree string=\"IAP Account\"><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></tree>"}'::jsonb
WHERE model = 'iap.account'
AND type = 'tree'
AND (arch_db IS NULL OR arch_db::text = '' OR arch_db::text = '{}' OR arch_db::text = '{"arch": ""}');

-- Fix any malformed JSON in tree views (this converts invalid JSON to valid)
UPDATE ir_ui_view
SET arch_db = '{"arch": "<tree string=\"IAP Account\"><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></tree>"}'::jsonb
WHERE model = 'iap.account'
AND type = 'tree'
AND arch_db IS NOT NULL
AND arch_db::text NOT LIKE '%<tree%';

-- Check the fixed views
SELECT id, name, arch_db::text
FROM ir_ui_view 
WHERE model = 'iap.account' 
AND type = 'tree';

-- Rebuild all tree views (alternative approach)
DO $$
DECLARE
    view_record RECORD;
BEGIN
    -- For every potentially problematic tree view
    FOR view_record IN SELECT id FROM ir_ui_view 
                      WHERE model = 'iap.account' 
                      AND type = 'tree'
    LOOP
        RAISE NOTICE 'Rebuilding view id %', view_record.id;
        
        -- Reset to default tree view
        UPDATE ir_ui_view 
        SET arch_db = '{"arch": "<tree string=\"IAP Account\"><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></tree>"}'::jsonb
        WHERE id = view_record.id;
    END LOOP;
END$$;

-- Force clear view cache
DELETE FROM ir_ui_view_custom
WHERE view_id IN (
    SELECT id FROM ir_ui_view WHERE model = 'iap.account'
);

-- Commit the changes
COMMIT;

-- Output message
\echo 'Fixed empty tree view for iap.account';
\echo 'Please restart your Odoo server to see the changes.'; 