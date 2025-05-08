import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Ensure the notification channel field exists in the database"""
    _logger.info("Running pre-migration for gatewayapi_sms 17.0.2.0.3")
    
    # Check if the table exists
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'iap_account'
        );
    """)
    
    table_exists = cr.fetchone()[0]
    if not table_exists:
        _logger.info("Table iap_account does not exist yet, skipping migration")
        return
    
    # Check if the field exists
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
        # Add the field to the database
        try:
            cr.execute("""
                ALTER TABLE iap_account 
                ADD COLUMN gatewayapi_notification_channel_id INTEGER;
            """)
            _logger.info("Successfully added column gatewayapi_notification_channel_id")
        except Exception as e:
            _logger.error(f"Failed to add column: {e}")
    else:
        _logger.info("Field gatewayapi_notification_channel_id already exists") 