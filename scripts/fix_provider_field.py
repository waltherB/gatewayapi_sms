#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to fix provider field integration issues with IAP Alternative Provider
Run this in the Odoo shell with:
    python odoo-bin shell -c /path/to/odoo.conf -d your_database --addons-path=/path/to/addons
Then execute:
    exec(open('scripts/fix_provider_field.py').read())
"""

import logging
_logger = logging.getLogger(__name__)

print("=== Fixing Provider Field Integration ===")

# Get the IAP account model
IapAccount = env['iap.account']

# Find SMS accounts
sms_accounts = IapAccount.search([('service_name', '=', 'sms')])
print(f"Found {len(sms_accounts)} SMS account(s)")

# Find GatewayAPI accounts 
gatewayapi_accounts = IapAccount.search([
    '|',
    ('provider', '=', 'sms_api_gatewayapi'),
    '&',
    ('gatewayapi_base_url', '!=', False),
    ('gatewayapi_api_token', '!=', False)
])
print(f"Found {len(gatewayapi_accounts)} GatewayAPI account(s)")

# Validate/fix each account
fixed_accounts = 0
for account in gatewayapi_accounts:
    if account.provider != 'sms_api_gatewayapi':
        print(f"Fixing account {account.id} ({account.name}): setting provider to 'sms_api_gatewayapi'")
        account.provider = 'sms_api_gatewayapi'
        fixed_accounts += 1
    
    # Make sure service_name is 'sms' for GatewayAPI accounts
    if account.service_name != 'sms':
        print(f"Fixing account {account.id} ({account.name}): setting service_name to 'sms'")
        account.service_name = 'sms'
        fixed_accounts += 1

print(f"Fixed {fixed_accounts} account(s)")

# Check existing provider options to verify the selection field works
provider_field = IapAccount._fields.get('provider')
if provider_field and hasattr(provider_field, 'selection'):
    print("\nProvider field selection values:")
    for value, label in provider_field.selection:
        print(f"  - {value}: {label}")

print("\nDone!") 