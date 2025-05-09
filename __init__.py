# -*- coding: utf-8 -*-

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
