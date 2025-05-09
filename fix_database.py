#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
import argparse
import sys


def fix_database(db_name, db_user, db_password, db_host='localhost', db_port=5432):
    """Fix database after uninstalling gatewayapi_sms module"""
    print(f"Connecting to database: {db_name} on {db_host}:{db_port}")
    
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        conn.autocommit = True  # Set autocommit to True
        cursor = conn.cursor()
        
        # Clean up transaction issues first
        print("Rolling back any pending transactions...")
        cursor.execute("ROLLBACK;")
        
        # 1. Remove gatewayapi fields from ir_model_fields
        print("Removing gatewayapi fields from ir_model_fields...")
        cursor.execute("""
            DELETE FROM ir_model_fields 
            WHERE model = 'iap.account' 
            AND name LIKE 'gatewayapi_%';
        """)
        print(f"Removed {cursor.rowcount} fields")
        
        # 2. Fix views by removing field references
        print("Fixing views by removing field references...")
        cursor.execute("""
            SELECT id, arch_db FROM ir_ui_view 
            WHERE model = 'iap.account' 
            AND arch_db LIKE '%gatewayapi%';
        """)
        views = cursor.fetchall()
        
        for view_id, arch_db in views:
            print(f"Checking view ID {view_id}")
            if 'gatewayapi' in arch_db:
                # Replace field references
                cursor.execute("""
                    UPDATE ir_ui_view
                    SET arch_db = regexp_replace(arch_db, 
                        '<field name="gatewayapi_[^"]*"[^>]*>.*?</field>', 
                        '', 
                        'g')
                    WHERE id = %s;
                """, (view_id,))
                
                # Replace group elements containing gatewayapi
                cursor.execute("""
                    UPDATE ir_ui_view
                    SET arch_db = regexp_replace(arch_db, 
                        '<group[^>]*>.*?gatewayapi.*?</group>', 
                        '', 
                        'g')
                    WHERE id = %s;
                """, (view_id,))
                
                print(f"Fixed view ID {view_id}")
        
        # 3. Add any other cleaning steps here
        
        print("Database fix completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fix Odoo database after uninstalling gatewayapi_sms')
    parser.add_argument('--db-name', required=True, help='Database name')
    parser.add_argument('--db-user', required=True, help='Database user')
    parser.add_argument('--db-password', required=True, help='Database password')
    parser.add_argument('--db-host', default='localhost', help='Database host')
    parser.add_argument('--db-port', default=5432, type=int, help='Database port')
    
    args = parser.parse_args()
    
    fix_database(
        args.db_name,
        args.db_user,
        args.db_password,
        args.db_host,
        args.db_port
    ) 