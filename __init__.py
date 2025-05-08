# -*- coding: utf-8 -*-

from . import models

def post_init_hook(cr, registry):
    """Post init hook for ensuring the notification channel field exists"""
    import logging
    _logger = logging.getLogger(__name__)
    
    _logger.info("Running post_init_hook for gatewayapi_sms")
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'iap_account' 
            AND column_name = 'gatewayapi_notification_channel_id'
        );
    """)
    field_exists = cr.fetchone()[0]
    
    if not field_exists:
        _logger.info("Adding gatewayapi_notification_channel_id field to iap_account table")
        try:
            cr.execute("""
                ALTER TABLE iap_account 
                ADD COLUMN gatewayapi_notification_channel_id INTEGER;
            """)
        except Exception as e:
            _logger.error(f"Failed to add column: {e}")
