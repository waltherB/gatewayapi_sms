import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """Ensure the notification channel field exists in the database"""
    _logger.info("Running pre-migration for gatewayapi_sms 17.0.2.0.0")
    
    # Check if the field exists
    cr.execute("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'iap_account' 
        AND column_name = 'gatewayapi_notification_channel_id'
    """)
    field_exists = cr.fetchone()
    
    if not field_exists:
        _logger.info("Adding gatewayapi_notification_channel_id field to iap_account table")
        # Add the field to the database
        cr.execute("""
            ALTER TABLE iap_account 
            ADD COLUMN gatewayapi_notification_channel_id INTEGER;
        """)
    else:
        _logger.info("Field gatewayapi_notification_channel_id already exists") 