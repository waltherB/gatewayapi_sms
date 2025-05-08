#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Adjust these paths based on your Odoo installation
ODOO_PATH = os.path.expanduser("~/odoo")
sys.path.insert(0, ODOO_PATH)

# Load the Odoo environment
import odoo
from odoo.cli.shell import Shell
from odoo.tools import config

def verify_fields():
    """Verify if the notification channel field exists in the database"""
    # Initialize Odoo environment
    config['addons_path'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    shell = Shell()
    shell.init(config)
    
    with odoo.api.Environment.manage():
        registry = odoo.modules.registry.Registry(shell.env.cr.dbname)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            
            # Get the model's fields from the database
            model_obj = env['ir.model']
            iap_account_model = model_obj.search([('model', '=', 'iap.account')], limit=1)
            
            if not iap_account_model:
                print("ERROR: iap.account model not found in the database")
                return
                
            # Get fields for the model
            field_obj = env['ir.model.fields']
            fields = field_obj.search([
                ('model_id', '=', iap_account_model.id),
            ])
            
            # Check if our field exists
            channel_field = field_obj.search([
                ('model_id', '=', iap_account_model.id),
                ('name', '=', 'gatewayapi_notification_channel_id'),
            ], limit=1)
            
            if channel_field:
                print("SUCCESS: gatewayapi_notification_channel_id field exists in the database")
                print(f"Field ID: {channel_field.id}")
                print(f"Field ttype: {channel_field.ttype}")
                print(f"Field relation: {channel_field.relation}")
            else:
                print("ERROR: gatewayapi_notification_channel_id field NOT FOUND in the database")
                
            # List all fields with gatewayapi prefix
            gatewayapi_fields = field_obj.search([
                ('model_id', '=', iap_account_model.id),
                ('name', 'like', 'gatewayapi_%'),
            ])
            
            print("\nAll gatewayapi fields in the model:")
            for field in gatewayapi_fields:
                print(f"- {field.name} (type: {field.ttype})")

if __name__ == "__main__":
    verify_fields() 