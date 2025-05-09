# -*- coding: utf-8 -*-

def post_init_hook(cr, registry):
    """Clean up IAP account views and records after gatewayapi_sms uninstall"""
    import logging
    _logger = logging.getLogger(__name__)
    
    _logger.info("Running cleanup for gatewayapi_sms")
    
    # Remove any references to the gatewayapi fields in ir.model.fields
    cr.execute("""
        DELETE FROM ir_model_fields 
        WHERE model = 'iap.account' 
        AND name LIKE 'gatewayapi_%'
    """)
    
    # Clean up any view definitions that might reference these fields
    cr.execute("""
        UPDATE ir_ui_view
        SET arch_db = regexp_replace(arch_db, 
            '<field name="gatewayapi_[^"]*"[^>]*>.*?</field>', 
            '', 
            'g')
        WHERE model = 'iap.account'
    """)
    
    # Clean up any view definitions that might have gatewayapi group elements
    cr.execute("""
        UPDATE ir_ui_view
        SET arch_db = regexp_replace(arch_db, 
            '<group[^>]*?>.*?gatewayapi.*?</group>', 
            '', 
            'g')
        WHERE model = 'iap.account'
    """)
    
    _logger.info("Cleanup for gatewayapi_sms complete") 