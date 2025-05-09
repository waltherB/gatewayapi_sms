#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
import argparse
import sys
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_database(conn_params):
    """Force clean GatewayAPI elements from IAP account views"""
    logger.info("Starting force cleanup of GatewayAPI elements")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = False  # Use transaction
        cursor = conn.cursor()
        
        # Step 1: Clean up the tree view columns
        logger.info("Cleaning tree view columns...")
        
        # First, get the ID of tree views for iap.account
        cursor.execute("""
            SELECT id, arch_db FROM ir_ui_view 
            WHERE model = 'iap.account' 
            AND type = 'tree'
        """)
        tree_views = cursor.fetchall()
        
        for view_id, arch_db in tree_views:
            logger.info(f"Processing tree view ID {view_id}")
            
            # Remove gatewayapi fields
            new_arch = re.sub(r'<field name="gatewayapi_[^"]*"[^/>]*/?>', '', arch_db)
            
            # Remove decoration attributes related to gatewayapi
            new_arch = re.sub(r'decoration-info="[^"]*gatewayapi[^"]*"', 'decoration-info=""', new_arch)
            
            # Update the view
            if new_arch != arch_db:
                cursor.execute("""
                    UPDATE ir_ui_view SET arch_db = %s WHERE id = %s
                """, (new_arch, view_id))
                logger.info(f"Updated tree view ID {view_id}")
        
        # Step 2: Clean up form views
        logger.info("Cleaning form views...")
        cursor.execute("""
            SELECT id, arch_db FROM ir_ui_view 
            WHERE model = 'iap.account' 
            AND type = 'form'
        """)
        form_views = cursor.fetchall()
        
        for view_id, arch_db in form_views:
            logger.info(f"Processing form view ID {view_id}")
            
            # Remove gatewayapi fields
            new_arch = re.sub(r'<field name="gatewayapi_[^"]*"[^/>]*/?>', '', arch_db)
            
            # Try to remove entire GatewayAPI group sections
            new_arch = re.sub(
                r'<group[^>]*string="GatewayAPI[^"]*"[^>]*>.*?</group>',
                '',
                new_arch,
                flags=re.DOTALL
            )
            
            # Update the view
            if new_arch != arch_db:
                cursor.execute("""
                    UPDATE ir_ui_view SET arch_db = %s WHERE id = %s
                """, (new_arch, view_id))
                logger.info(f"Updated form view ID {view_id}")
        
        # Step 3: Remove field definitions
        logger.info("Removing field definitions...")
        cursor.execute("""
            DELETE FROM ir_model_fields 
            WHERE model = 'iap.account' 
            AND name LIKE 'gatewayapi_%'
        """)
        logger.info(f"Removed {cursor.rowcount} field definitions")
        
        # Step 4: Clean up ir_model_data entries
        logger.info("Cleaning up ir_model_data entries...")
        cursor.execute("""
            DELETE FROM ir_model_data 
            WHERE (name LIKE '%gatewayapi%' OR name LIKE '%sms_api_gatewayapi%') 
            AND model = 'ir.ui.view'
        """)
        logger.info(f"Removed {cursor.rowcount} ir_model_data entries")
        
        # Step 5: Force clear view cache
        logger.info("Clearing view cache...")
        cursor.execute("""
            DELETE FROM ir_ui_view_custom
            WHERE view_id IN (
                SELECT id FROM ir_ui_view WHERE model = 'iap.account'
            )
        """)
        
        # Commit all changes
        conn.commit()
        logger.info("All changes committed successfully")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Force cleanup GatewayAPI elements from Odoo database')
    parser.add_argument('--db-name', required=True, help='Database name')
    parser.add_argument('--db-user', required=True, help='Database user')
    parser.add_argument('--db-password', required=True, help='Database password')
    parser.add_argument('--db-host', default='localhost', help='Database host')
    parser.add_argument('--db-port', default=5432, type=int, help='Database port')
    
    args = parser.parse_args()
    
    conn_params = {
        'dbname': args.db_name,
        'user': args.db_user,
        'password': args.db_password,
        'host': args.db_host,
        'port': args.db_port
    }
    
    success = clean_database(conn_params)
    sys.exit(0 if success else 1) 