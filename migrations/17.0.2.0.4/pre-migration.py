import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Ensure proper database schema for fresh install"""
    _logger.info("Running pre-migration for gatewayapi_sms 17.0.2.0.4")
    
    # Safety - check if iap_account exists
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
        
    # Ensure the gatewayapi_notification table creation proceeds safely
    cr.execute("""
        CREATE TABLE IF NOT EXISTS gatewayapi_notification (
            id serial NOT NULL,
            create_uid integer,
            create_date timestamp without time zone,
            write_uid integer,
            write_date timestamp without time zone,
            account_id integer NOT NULL,
            channel_id integer,
            PRIMARY KEY(id)
        );
        
        COMMENT ON TABLE gatewayapi_notification IS 'GatewayAPI Notification Settings';
    """)
    
    # Create index on account_id
    cr.execute("""
        CREATE INDEX IF NOT EXISTS gatewayapi_notification_account_id_idx
        ON gatewayapi_notification (account_id);
    """)
    
    # Create foreign key constraints if possible
    try:
        cr.execute("""
            ALTER TABLE gatewayapi_notification 
            ADD CONSTRAINT gatewayapi_notification_account_id_fkey
            FOREIGN KEY (account_id) REFERENCES iap_account(id)
            ON DELETE CASCADE;
        """)
    except Exception as e:
        _logger.warning(f"Could not create foreign key constraint: {e}")
        
    try:
        cr.execute("""
            ALTER TABLE gatewayapi_notification 
            ADD CONSTRAINT gatewayapi_notification_channel_id_fkey
            FOREIGN KEY (channel_id) REFERENCES mail_channel(id)
            ON DELETE SET NULL;
        """)
    except Exception as e:
        _logger.warning(f"Could not create foreign key constraint: {e}")
        
    _logger.info("Database schema preparation complete") 