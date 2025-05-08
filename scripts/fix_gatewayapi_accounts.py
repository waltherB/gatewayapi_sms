#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GatewayAPI Account Fixup for Odoo 17
Run this in the Odoo shell with:
    python odoo-bin shell -c /path/to/odoo.conf -d your_database --addons-path=/path/to/addons
Then execute:
    exec(open('scripts/fix_gatewayapi_accounts.py').read())

This script will:
1. Verify all IAP accounts that could be GatewayAPI accounts
2. Apply fixes if needed
3. Create a default GatewayAPI account if none exists
"""

import logging
_logger = logging.getLogger(__name__)

print("=== GatewayAPI Account Fixup for Odoo 17 ===")

# Get all IAP accounts that might be GatewayAPI accounts
iap_accounts = env['iap.account'].search([
    '|',
    ('service_name', '=', 'sms'),
    ('gatewayapi_api_token', '!=', False)
])

print(f"\nFound {len(iap_accounts)} potential IAP accounts")

# Count of GatewayAPI accounts
gatewayapi_count = 0

# Check each account
for account in iap_accounts:
    is_gatewayapi = bool(account.gatewayapi_base_url and account.gatewayapi_api_token)
    
    print(f"\nAccount #{account.id}: {account.name or 'Unnamed'}")
    print(f"  Service name: {account.service_name}")
    print(f"  Base URL: {account.gatewayapi_base_url or 'Not set'}")
    print(f"  API Token: {'Set' if account.gatewayapi_api_token else 'Not set'}")
    print(f"  Is GatewayAPI: {is_gatewayapi}")
    
    # If it has GatewayAPI config but service_name is not 'sms', fix it
    if is_gatewayapi and account.service_name != 'sms':
        print(f"  FIXING: Setting service_name to 'sms' (was '{account.service_name}')")
        account.service_name = 'sms'
    
    # Ensure the is_gatewayapi field is computed correctly (this should happen automatically)
    account._compute_is_gatewayapi()
    
    if account.is_gatewayapi:
        gatewayapi_count += 1

# If no GatewayAPI accounts found, create one
if gatewayapi_count == 0:
    print("\nNo GatewayAPI accounts found. Creating a default one...")
    new_account = env['iap.account'].create({
        'name': 'GatewayAPI',
        'service_name': 'sms',
        'gatewayapi_base_url': 'https://gatewayapi.eu',
        'gatewayapi_sender': 'Odoo',
    })
    print(f"Created new GatewayAPI account with ID {new_account.id}")
    gatewayapi_count = 1

# Find the default SMS account
sms_account = env['iap.account'].get('sms')
print(f"\nDefault SMS Account: #{sms_account.id} {sms_account.name or 'Unnamed'}")
print(f"  Is GatewayAPI: {sms_account.is_gatewayapi}")

# Test the SMS handling
test_sms_account = env['iap.account']._get_sms_account()
print(f"\nAccount used for sending SMS: #{test_sms_account.id} {test_sms_account.name or 'Unnamed'}")
print(f"  Is GatewayAPI: {test_sms_account.is_gatewayapi}")

# Commit changes if any
env.cr.commit()
print(f"\nDone! Found/fixed {gatewayapi_count} GatewayAPI accounts.") 