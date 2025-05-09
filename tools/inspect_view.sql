-- Diagnostic script to inspect problematic views
-- Run as PostgreSQL superuser or database owner
-- Example: psql -U odoo -d odoo -f inspect_view.sql

\echo '-------------------------------------------------';
\echo 'DIAGNOSTICS FOR IAP ACCOUNT VIEWS';
\echo '-------------------------------------------------';

-- Show all views for iap.account with detailed structure
\echo 'All iap.account views:';
SELECT 
    id, 
    name, 
    type, 
    priority,
    active,
    arch_db::text AS arch_content,
    LENGTH(arch_db::text) AS content_length,
    CASE 
        WHEN arch_db IS NULL THEN 'NULL'
        WHEN arch_db::text = '{}' THEN 'EMPTY_JSON'
        WHEN arch_db::text = '{"arch": ""}' THEN 'EMPTY_ARCH'
        WHEN arch_db::text NOT LIKE '%<tree%' AND type = 'tree' THEN 'MISSING_TREE_TAG'
        WHEN arch_db::text NOT LIKE '%</tree>%' AND type = 'tree' THEN 'MISSING_TREE_CLOSE_TAG'
        WHEN arch_db::text NOT LIKE '%<form%' AND type = 'form' THEN 'MISSING_FORM_TAG'
        WHEN arch_db::text NOT LIKE '%</form>%' AND type = 'form' THEN 'MISSING_FORM_CLOSE_TAG'
        ELSE 'OK'
    END AS diagnosis
FROM ir_ui_view 
WHERE model = 'iap.account'
ORDER BY type, priority;

-- Check for inherited views that might cause issues
\echo 'Inherited views for iap.account:';
SELECT 
    iv.id,
    iv.name,
    iv.type,
    iv.inherit_id,
    pv.name AS parent_name,
    iv.arch_db::text AS arch_content
FROM ir_ui_view iv
LEFT JOIN ir_ui_view pv ON iv.inherit_id = pv.id
WHERE iv.model = 'iap.account' 
AND iv.inherit_id IS NOT NULL;

-- Check for model data entries that might be causing issues
\echo 'Model data entries for iap.account views:';
SELECT 
    imd.name AS xml_id,
    imd.module,
    imd.model,
    imd.res_id,
    imd.noupdate,
    iv.name AS view_name,
    iv.type AS view_type
FROM ir_model_data imd
JOIN ir_ui_view iv ON imd.res_id = iv.id
WHERE imd.model = 'ir.ui.view'
AND iv.model = 'iap.account';

-- Check for any ir_translation entries that might be causing issues
\echo 'Translation entries for iap.account views:';
SELECT 
    it.lang,
    it.src,
    it.value,
    it.state,
    it.name,
    it.type
FROM ir_translation it
WHERE it.name LIKE 'ir.ui.view,arch_db'
AND it.res_id IN (SELECT id FROM ir_ui_view WHERE model = 'iap.account');

\echo '-------------------------------------------------';
\echo 'DIAGNOSTICS COMPLETE';
\echo '-------------------------------------------------'; 