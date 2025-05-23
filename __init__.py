# -*- coding: utf-8 -*-
# We need the models module for the app to function correctly
from . import models


def post_init_hook(first_param, registry=None):
    """Post init hook for migrating notification channels
    
    Can be called as either:
    - post_init_hook(cr, registry) - normal Odoo API
    - post_init_hook(env) - some versions/configurations
    """
    import logging
    _logger = logging.getLogger(__name__)
    
    _logger.info("Running post_init_hook for gatewayapi_sms")
    
    # Determine if we got env or cr as first parameter
    if hasattr(first_param, 'cr'):
        # We received env as the first parameter
        env = first_param
        cr = env.cr
    else:
        # We received cr as the first parameter
        cr = first_param
        # Create environment
        from odoo import api, SUPERUSER_ID
        with api.Environment.manage():
            env = api.Environment(cr, SUPERUSER_ID, {})
    
    try:
        # Check for existing accounts with GatewayAPI configuration
        cr.execute("""
            SELECT id FROM iap_account
            WHERE provider = 'sms_api_gatewayapi'
            OR gatewayapi_base_url IS NOT NULL
        """)
        account_ids = [r[0] for r in cr.fetchall()]
        
        if not account_ids:
            _logger.info("No GatewayAPI accounts found, skipping migration")
            return
            
        # First check if notification table exists
        cr.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'gatewayapi_notification'
            );
        """)
        table_exists = cr.fetchone()[0]
        
        if not table_exists:
            _logger.info("gatewayapi_notification table does not exist yet, skipping migration")
            return
        
        # For each account, check if a notification record exists and create if not
        for account_id in account_ids:
            notification = env['gatewayapi.notification'].search([
                ('account_id', '=', account_id)
            ], limit=1)
            
            if not notification:
                # Create notification record
                env['gatewayapi.notification'].create({
                    'account_id': account_id,
                })
                _logger.info(f"Created notification record for account {account_id}")
            else:
                _logger.info(f"Notification record already exists for account {account_id}")
    except Exception as e:
        _logger.error(f"Error in post_init_hook: {e}")
        # Don't propagate the error to prevent installation failure

def uninstall_hook(first_param, registry=None):
    """Cleanup hook to remove GatewayAPI elements from IAP views

    Can be called as either:
    - uninstall_hook(cr, registry) - Odoo <= 16
    - uninstall_hook(env) - Odoo 17+
    """
    import logging
    _logger = logging.getLogger(__name__)

    _logger.info("Running uninstall_hook for gatewayapi_sms")

    try:
        # Determine if we got env or cr as first parameter
        if hasattr(first_param, 'cr'):
            # We received env as the first parameter
            env = first_param
            cr = env.cr
        else:
            # We received cr as the first parameter
            cr = first_param
            # Create environment
            from odoo import api, SUPERUSER_ID
            with api.Environment.manage():
                env = api.Environment(cr, SUPERUSER_ID, {})

        IrModelFields = env['ir.model.fields']
        IrModel = env['ir.model']

        # Define the model and field pattern to check
        model_name = 'iap.account'
        field_pattern = 'gatewayapi_%'

        # Get the model ID
        model = IrModel.search([('model', '=', model_name)])
        if not model:
            _logger.error(f"Model {model_name} not found")
            return

        # Get all fields related to the pattern
        existing_fields = IrModelFields.search([('model_id', '=', model.id), ('name', 'like', field_pattern)])
        existing_field_names = {field.name for field in existing_fields}

        # Define the fields that should exist
        required_fields = [
            'gatewayapi_new_channel_name',
            'gatewayapi_subscribe_current_user',
            'gatewayapi_effective_notification_channel_id',
            # Add other required fields as needed
        ]

        # Create missing fields
        for field_name in required_fields:
            if field_name not in existing_field_names:
                _logger.info(f"Creating missing field: {field_name}")
                IrModelFields.create({
                    'name': field_name,
                    'model_id': model.id,
                    'model': model_name,
                    'field_description': '{"en_US": "Field Description"}',  # Update description as needed
                    'ttype': 'char',  # Update field type as needed
                    'state': 'manual',
                })

        # Run cleanup directly on database
        _logger.info("Cleaning up database views...")

        # Clean up views - handle JSONB format in Odoo 17
        cr.execute("""
            UPDATE ir_ui_view
            SET arch_db = regexp_replace(arch_db::text,
                '<field name="gatewayapi_[^"]*"[^>]*>.*?</field>',
                '', 'g')::jsonb
            WHERE model = 'iap.account'
            AND arch_db::text LIKE '%gatewayapi%';
        """)

        # Clean up view elements containing gatewayapi in groups
        cr.execute("""
            UPDATE ir_ui_view
            SET arch_db = regexp_replace(arch_db::text,
                '<group[^>]*?>.*?gatewayapi.*?</group>',
                '', 'g')::jsonb
            WHERE model = 'iap.account'
            AND arch_db::text LIKE '%gatewayapi%';
        """)

        # Remove field references
        _logger.info("Cleaning up field references...")
        cr.execute("""
            DELETE FROM ir_model_fields
            WHERE model = 'iap.account'
            AND name LIKE 'gatewayapi_%';
        """)

        _logger.info("GatewayAPI uninstall cleanup complete")
    except Exception as e:
        _logger.error(f"Error in uninstall_hook: {e}")

