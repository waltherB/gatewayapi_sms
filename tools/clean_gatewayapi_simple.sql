-- Simple cleanup script for GatewayAPI module uninstallation issues
-- Run as PostgreSQL superuser or database owner
-- Example: psql -U odoo -d your_database -f clean_gatewayapi_simple.sql

-- First rollback any existing transaction
ROLLBACK;

-- Start a new transaction
BEGIN;

-- 1. Clean up the specific field with ID 19221 that's causing the error
DELETE FROM ir_model_data
WHERE model = 'ir.model.fields' AND res_id = 19221;

DELETE FROM ir_model_fields
WHERE id = 19221;

-- 2. Clean up all GatewayAPI fields (more thorough approach)
DELETE FROM ir_model_data
WHERE model = 'ir.model.fields' 
AND res_id IN (
    SELECT id FROM ir_model_fields
    WHERE name LIKE 'gatewayapi_%'
);

DELETE FROM ir_model_fields
WHERE name LIKE 'gatewayapi_%';

-- 3. Clean up any broken constraints
DELETE FROM ir_model_constraint
WHERE model NOT IN (SELECT id FROM ir_model);

-- 4. Clean up any broken relations
DELETE FROM ir_model_relation
WHERE model NOT IN (SELECT id FROM ir_model);

-- Commit the changes
COMMIT;

-- Output message
\echo 'GatewayAPI database cleanup complete!';
\echo 'Please restart your Odoo server to see the changes.'; 