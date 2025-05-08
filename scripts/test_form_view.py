#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
from pprint import pprint

# Adjust these paths based on your Odoo installation
ODOO_PATH = os.path.expanduser("~/odoo")
sys.path.insert(0, ODOO_PATH)

# Load the Odoo environment
import odoo
from odoo.cli.shell import Shell
from odoo.tools import config

def debug_form_view():
    """Debug the IAP account form view for GatewayAPI"""
    # Initialize Odoo environment
    config['addons_path'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    shell = Shell()
    shell.init(config)
    
    with odoo.api.Environment.manage():
        registry = odoo.modules.registry.Registry(shell.env.cr.dbname)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            
            # Get the form view
            form_view = env.ref('gatewayapi_sms.iap_account_view_form', raise_if_not_found=False)
            if not form_view:
                print("Form view not found. Check the external ID.")
                return
                
            print("Form view found:")
            print(f"- ID: {form_view.id}")
            print(f"- Name: {form_view.name}")
            print(f"- Inherit: {form_view.inherit_id.name if form_view.inherit_id else 'None'}")
            
            # Check if we can create a test account
            try:
                test_account = env['iap.account'].with_context(
                    default_name='TEST GatewayAPI',
                    default_service_name='sms',
                    default_provider='sms_api_gatewayapi',
                    default_gatewayapi_base_url='https://gatewayapi.eu',
                    default_gatewayapi_sender='Odoo',
                ).create({
                    'name': 'TEST GatewayAPI',
                    'service_name': 'sms',
                    'provider': 'sms_api_gatewayapi',
                    'gatewayapi_base_url': 'https://gatewayapi.eu',
                    'gatewayapi_sender': 'Odoo',
                })
                
                print(f"Test account created successfully with ID: {test_account.id}")
                # Check notification channel field
                if hasattr(test_account, 'gatewayapi_notification_channel_id'):
                    print("Notification channel field exists on the model")
                else:
                    print("ERROR: Notification channel field does not exist on the model")
                
                # Clean up test account
                test_account.unlink()
                print("Test account deleted")
                
            except Exception as e:
                print(f"Error creating test account: {e}")
                
            # Get fields info
            fields_info = env['iap.account'].fields_get(['name', 'service_name', 'provider', 
                                                       'gatewayapi_notification_channel_id'])
            print("\nFields information:")
            pprint(fields_info)
            
            # Get view architecture
            arch = form_view.arch
            print("\nView architecture excerpt:")
            print(arch[:500] + "..." if len(arch) > 500 else arch)

if __name__ == "__main__":
    debug_form_view() 