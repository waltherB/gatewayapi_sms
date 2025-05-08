#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to check GatewayAPI configuration and account settings in Odoo 17
Run this in the Odoo shell with:
    python odoo-bin shell -c /path/to/odoo.conf -d your_database --addons-path=/path/to/addons
Then execute:
    exec(open('scripts/check_gatewayapi_config.py').read())
"""

print("=== GatewayAPI Configuration Check ===")

# Find the SMS IAP account
sms_account = env['iap.account'].get('sms')
print(f"SMS account found: ID={sms_account.id}, Name={sms_account.name or 'Unnamed'}")

# Check for provider field (should be 'odoo' in Odoo 17)
if hasattr(sms_account, 'provider'):
    provider = sms_account.provider
    print(f"Provider: {provider}")
else:
    print("Provider field not found (this is normal in some Odoo 17 configurations)")

# Check GatewayAPI configuration
print("\nGatewayAPI Configuration:")
for field in dir(sms_account):
    if field.startswith('gatewayapi_') and not field.startswith('_'):
        try:
            value = getattr(sms_account, field)
            # Mask token for security
            if field == 'gatewayapi_api_token' and value:
                print(f"  - {field}: ****{value[-4:] if value else ''}")
            else:
                print(f"  - {field}: {value}")
        except Exception as e:
            print(f"  - {field}: Error: {e}")

# Check balance
try:
    if sms_account.gatewayapi_api_token and sms_account.gatewayapi_base_url:
        balance = sms_account.get_current_credit_balance()
        print(f"\nCurrent balance: {balance}")
    else:
        print("\nCannot check balance: API token or base URL missing")
except Exception as e:
    print(f"\nError checking balance: {e}")

# Check for notification settings
print("\nNotification settings:")
print(f"  - Check min tokens: {sms_account.gatewayapi_check_min_tokens}")
print(f"  - Min tokens: {sms_account.gatewayapi_min_tokens}")

if sms_account.gatewayapi_token_notification_action:
    print(f"  - Notification action: {sms_account.gatewayapi_token_notification_action.name}")
else:
    print("  - No notification action configured")

print("\nDone!") 