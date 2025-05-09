-- Complete rebuild of IAP Account views
-- Run as PostgreSQL superuser or database owner
-- Example: psql -U odoo -d odoo -f recreate_iap_views.sql

\echo '-------------------------------------------------';
\echo 'COMPLETE REBUILD OF IAP ACCOUNT VIEWS';
\echo '-------------------------------------------------';

-- Backup current views (just in case)
\echo 'Backing up current views...';
CREATE TEMPORARY TABLE backup_iap_views AS
SELECT * FROM ir_ui_view WHERE model = 'iap.account';

-- Remove all view translations
\echo 'Removing view translations...';
DELETE FROM ir_translation 
WHERE name LIKE 'ir.ui.view,arch_db' 
AND res_id IN (SELECT id FROM ir_ui_view WHERE model = 'iap.account');

-- Remove ir_model_data references to views
\echo 'Removing model data references...';
DELETE FROM ir_model_data
WHERE model = 'ir.ui.view'
AND res_id IN (SELECT id FROM ir_ui_view WHERE model = 'iap.account');

-- Remove all existing views
\echo 'Removing all existing iap.account views...';
DELETE FROM ir_ui_view WHERE model = 'iap.account';

-- Insert standard views
\echo 'Creating new views...';

-- Tree view
INSERT INTO ir_ui_view (name, model, type, priority, mode, active, arch_db)
VALUES (
    'iap.account.tree', 
    'iap.account', 
    'tree', 
    16, 
    'primary',
    true, 
    '{"arch": "<tree string=\"IAP Account\"><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></tree>"}'::jsonb
);

-- Form view
INSERT INTO ir_ui_view (name, model, type, priority, mode, active, arch_db)
VALUES (
    'iap.account.form', 
    'iap.account', 
    'form', 
    16, 
    'primary',
    true, 
    '{"arch": "<form string=\"IAP Account\"><sheet><group><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/><field name=\"account_token\"/><field name=\"balance\"/></group></sheet></form>"}'::jsonb
);

-- Search view
INSERT INTO ir_ui_view (name, model, type, priority, mode, active, arch_db)
VALUES (
    'iap.account.search', 
    'iap.account', 
    'search', 
    16, 
    'primary',
    true, 
    '{"arch": "<search string=\"IAP Account\"><field name=\"name\"/><field name=\"provider\"/><field name=\"service_name\"/><field name=\"company_id\"/></search>"}'::jsonb
);

-- Create model data entries for views
\echo 'Creating model data entries...';

INSERT INTO ir_model_data (name, model, module, res_id, noupdate)
SELECT 
    REPLACE(name, '.', '_') AS name,
    'ir.ui.view' AS model,
    'iap' AS module,
    id AS res_id,
    false AS noupdate
FROM ir_ui_view
WHERE model = 'iap.account';

-- Verify the newly created views
\echo 'Newly created views:';
SELECT id, name, type, priority, arch_db::text
FROM ir_ui_view
WHERE model = 'iap.account';

\echo '-------------------------------------------------';
\echo 'IAP ACCOUNT VIEWS RECREATED SUCCESSFULLY';
\echo '-------------------------------------------------';
\echo 'Please restart your Odoo server now!'; 