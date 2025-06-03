# -*- coding: utf-8 -*-
# We need the models module for the app to function correctly
from . import models
from . import controllers


def post_init_hook(first_param, registry=None):
    """Post init hook for migrating notification channels
    
    Can be called as either:
    - post_init_hook(cr, registry) - normal Odoo API
    - post_init_hook(env) - some versions/configurations
    """
    import logging
    _logger = logging.getLogger(__name__)
    
    _logger.info("Running post_init_hook for gatewayapi_sms (now simplified)")
    
    # Determine if we got env or cr as first parameter (this logic should be preserved)
    if hasattr(first_param, 'cr'):
        env = first_param
        cr = env.cr
    else:
        cr = first_param
        from odoo import api, SUPERUSER_ID
        with api.Environment.manage():
            env = api.Environment(cr, SUPERUSER_ID, {})
    
    # The main try-except block related to gatewayapi_notification has been removed.
    # Add any other generic post-init logic here if needed in the future.
    _logger.info("post_init_hook for gatewayapi_sms has completed its current tasks.")

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

