#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script fixes missing or corrupted ir.model.fields records that prevent
module uninstallation in Odoo.
"""

import os
import sys
import argparse
import psycopg2
from getpass import getpass

def fix_missing_field_record(conn, field_id):
    """Check and fix the specific field record"""
    cursor = conn.cursor()
    
    # First check if the record exists
    cursor.execute("SELECT id, name, model FROM ir_model_fields WHERE id = %s", (field_id,))
    field_data = cursor.fetchone()
    
    if field_data:
        print(f"Field record exists: ID={field_data[0]}, Name={field_data[1]}, Model={field_data[2]}")
        print("Checking for issues...")
        
        # Check if this field is a GatewayAPI field
        if field_data[1] and field_data[1].startswith('gatewayapi_'):
            print(f"This is a GatewayAPI field ({field_data[1]}). Will mark it for deletion.")
            
            # Check if there are any constraints or dependencies
            cursor.execute("""
                SELECT COUNT(*) FROM ir_model_constraint
                WHERE model = %s
            """, (field_data[2],))
            constraints = cursor.fetchone()[0]
            
            if constraints > 0:
                print(f"Found {constraints} constraints on the model. Will try to clean up...")
                
                # Try to delete constraints related to this field
                cursor.execute("""
                    DELETE FROM ir_model_constraint
                    WHERE model = %s
                """, (field_data[2],))
                print(f"Removed constraints for model {field_data[2]}")
            
            # Finally delete the field record
            cursor.execute("DELETE FROM ir_model_fields WHERE id = %s", (field_id,))
            print(f"Deleted field record with ID {field_id}")
        else:
            print("This is not a GatewayAPI field. Not safe to delete automatically.")
            return False
    else:
        print(f"Field record with ID {field_id} does not exist.")
        print("Checking for references to this non-existent record...")
        
        # Check for references in ir_model_data
        cursor.execute("""
            SELECT id, name, module FROM ir_model_data
            WHERE model = 'ir.model.fields' AND res_id = %s
        """, (field_id,))
        model_data = cursor.fetchall()
        
        if model_data:
            print(f"Found {len(model_data)} references in ir_model_data. Will delete them...")
            for record in model_data:
                print(f"  - ID={record[0]}, Name={record[1]}, Module={record[2]}")
            
            cursor.execute("""
                DELETE FROM ir_model_data
                WHERE model = 'ir.model.fields' AND res_id = %s
            """, (field_id,))
            print(f"Deleted {len(model_data)} references to the missing field.")
        else:
            print("No references found in ir_model_data.")
            
            # Clean up any references in deleted models
            print("Cleaning up references in ir_model_constraint...")
            cursor.execute("""
                DELETE FROM ir_model_constraint
                WHERE id IN (
                    SELECT c.id FROM ir_model_constraint c
                    LEFT JOIN ir_model m ON c.model = m.id
                    WHERE m.id IS NULL
                )
            """)
            
            print("Cleaning up references in ir_model_relation...")
            cursor.execute("""
                DELETE FROM ir_model_relation
                WHERE id IN (
                    SELECT r.id FROM ir_model_relation r
                    LEFT JOIN ir_model m ON r.model = m.id
                    WHERE m.id IS NULL
                )
            """)
    
    cursor.close()
    return True

def cleanup_gatewayapi_fields(conn):
    """Clean up all GatewayAPI related fields"""
    cursor = conn.cursor()
    
    # Find all GatewayAPI fields
    cursor.execute("""
        SELECT id, name, model FROM ir_model_fields
        WHERE name LIKE 'gatewayapi_%'
    """)
    
    gatewayapi_fields = cursor.fetchall()
    
    if not gatewayapi_fields:
        print("No GatewayAPI fields found in the database.")
        cursor.close()
        return
    
    print(f"Found {len(gatewayapi_fields)} GatewayAPI fields to clean up:")
    for field in gatewayapi_fields:
        print(f"  - ID={field[0]}, Name={field[1]}, Model={field[2]}")
    
    confirm = input("Do you want to delete all these fields? (y/N): ")
    if confirm.lower() != 'y':
        print("Operation canceled.")
        cursor.close()
        return
    
    # Delete all GatewayAPI fields
    cursor.execute("""
        DELETE FROM ir_model_fields
        WHERE name LIKE 'gatewayapi_%'
    """)
    
    print(f"Deleted {len(gatewayapi_fields)} GatewayAPI fields.")
    cursor.close()

def main():
    parser = argparse.ArgumentParser(description='Fix missing field records in Odoo database')
    parser.add_argument('--db-name', required=True, help='Database name')
    parser.add_argument('--db-user', default='odoo', help='Database user')
    parser.add_argument('--db-host', default='localhost', help='Database host')
    parser.add_argument('--db-port', default=5432, type=int, help='Database port')
    parser.add_argument('--field-id', type=int, help='ID of the field to fix')
    parser.add_argument('--cleanup-all', action='store_true', 
                        help='Clean up all GatewayAPI related fields')
    args = parser.parse_args()
    
    # Ask for password
    db_password = getpass(f"Enter password for user {args.db_user}: ")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname=args.db_name,
            user=args.db_user,
            password=db_password,
            host=args.db_host,
            port=args.db_port
        )
        conn.autocommit = False
        
        print(f"Connected to database {args.db_name}")
        
        if args.cleanup_all:
            cleanup_gatewayapi_fields(conn)
        elif args.field_id:
            if fix_missing_field_record(conn, args.field_id):
                print("Field record fixed successfully!")
        else:
            parser.print_help()
            sys.exit(1)
        
        # Commit the changes
        conn.commit()
        print("Changes committed to database.")
        
        conn.close()
        print("Database connection closed.")
        print("\nPlease restart your Odoo server for the changes to take effect.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 