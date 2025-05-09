-- Fix missing or corrupted ir.model.fields records that prevent module uninstallation
-- Run as PostgreSQL superuser or database owner
-- Example: psql -U odoo -d your_database -f fix_missing_fields.sql

-- Start transaction to make it safer
BEGIN;

-- Display the specific field (19221)
SELECT 'Field record information for ID 19221:' AS info;
SELECT id, name, model, ttype, state, modules
FROM ir_model_fields
WHERE id = 19221;

-- Display reference to this field in ir_model_data
SELECT 'References in ir_model_data:' AS info;
SELECT id, name, module, model, res_id
FROM ir_model_data
WHERE model = 'ir.model.fields' AND res_id = 19221;

-- Check if there are any GatewayAPI fields
SELECT 'GatewayAPI fields in database:' AS info;
SELECT id, name, model
FROM ir_model_fields
WHERE name LIKE 'gatewayapi_%'
LIMIT 10;

-- 1. Clean up the specific field with ID 19221
DELETE FROM ir_model_data
WHERE model = 'ir.model.fields' AND res_id = 19221;

DELETE FROM ir_model_fields
WHERE id = 19221;

-- 2. Clean up all gatewayapi fields
DELETE FROM ir_model_data
WHERE model = 'ir.model.fields' 
AND res_id IN (
    SELECT id FROM ir_model_fields
    WHERE name LIKE 'gatewayapi_%'
);

DELETE FROM ir_model_fields
WHERE name LIKE 'gatewayapi_%';

-- 3. Clean up orphaned constraints
DELETE FROM ir_model_constraint
WHERE id IN (
    SELECT c.id FROM ir_model_constraint c
    LEFT JOIN ir_model m ON c.model = m.id
    WHERE m.id IS NULL
);

-- 4. Clean up orphaned relations
DELETE FROM ir_model_relation
WHERE id IN (
    SELECT r.id FROM ir_model_relation r
    LEFT JOIN ir_model m ON r.model = m.id
    WHERE m.id IS NULL
);

-- Verify the cleanup
SELECT 'Remaining GatewayAPI fields after cleanup:' AS info;
SELECT COUNT(*) FROM ir_model_fields
WHERE name LIKE 'gatewayapi_%';

SELECT 'Remaining references in ir_model_data after cleanup:' AS info;
SELECT COUNT(*) FROM ir_model_data
WHERE model = 'ir.model.fields' AND res_id = 19221;

-- Commit the changes - Comment this line if you want to review the changes first
COMMIT;

\echo 'Database cleanup complete!';
\echo 'Please restart your Odoo server for the changes to take effect.'; 