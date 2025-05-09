-- Direct fix for broken IAP Account view
-- Run as PostgreSQL superuser or database owner
-- Example: psql -U odoo -d odoo -f fix_broken_view.sql

\echo '-------------------------------------------------';
\echo 'EMERGENCY FIX FOR BROKEN IAP ACCOUNT VIEWS';
\echo '-------------------------------------------------';

-- Display the current views for iap.account
\echo 'Current iap.account views:';
SELECT id, name, type, arch_db::text AS arch_content
FROM ir_ui_view 
WHERE model = 'iap.account';

-- First attempt: Replace all views with empty content
\echo 'Fixing views with empty content:';
UPDATE ir_ui_view
SET arch_db = '{"arch": "<tree string=\"IAP Account\"><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></tree>"}'::jsonb
WHERE model = 'iap.account'
AND type = 'tree'
AND (
    arch_db IS NULL 
    OR arch_db::text = '{}'
    OR arch_db::text = '{"arch": ""}'
    OR arch_db::text = '"arch": ""'
    OR arch_db::text NOT LIKE '%<tree%'
    OR TRIM(arch_db::text) = ''
);

-- Force delete and recreate the tree view - more aggressive approach
\echo 'Aggressive fix: Deleting and recreating main tree view:';
DELETE FROM ir_ui_view
WHERE model = 'iap.account' 
AND type = 'tree';

-- Insert a new clean tree view
INSERT INTO ir_ui_view (name, model, type, priority, active, arch_db)
VALUES ('iap.account.tree.fixed', 'iap.account', 'tree', 16, true, 
        '{"arch": "<tree string=\"IAP Account\"><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></tree>"}'::jsonb);

-- Check results
\echo 'Views after fixes:';
SELECT id, name, type, arch_db::text AS arch_content
FROM ir_ui_view 
WHERE model = 'iap.account';

-- Clear server caches
\echo 'Clearing server caches:';
UPDATE ir_model_data
SET noupdate = false
WHERE model = 'ir.ui.view' 
AND res_id IN (SELECT id FROM ir_ui_view WHERE model = 'iap.account');

\echo '-------------------------------------------------';
\echo 'COMPLETED EMERGENCY VIEW FIX';
\echo '-------------------------------------------------';
\echo 'Please restart your Odoo server now!'; 