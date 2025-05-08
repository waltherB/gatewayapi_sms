#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to check IAP form view provider field
Run this in the Odoo shell with:
    python odoo-bin shell -c /path/to/odoo.conf -d your_database --addons-path=/path/to/addons
Then execute:
    exec(open('scripts/check_provider_form.py').read())
"""

import logging
from pprint import pprint
_logger = logging.getLogger(__name__)

print("=== Checking IAP Form View Provider Field ===")

# Get the base IAP form view
form_view = env.ref('iap.iap_account_view_form', raise_if_not_found=False)
if not form_view:
    print("IAP account form view not found!")
else:
    print(f"Found IAP account form view: {form_view.name}")
    # Print the arch to see the XML structure
    print("\nForm view arch:")
    print(form_view.arch)

# Check if there are other views inheriting from the base view
inheriting_views = env['ir.ui.view'].search([
    ('inherit_id', '=', form_view.id if form_view else False)
])
print(f"\nFound {len(inheriting_views)} view(s) inheriting from the base IAP form view:")
for view in inheriting_views:
    print(f"  - {view.name} ({view.model}) in module {view.xml_id.split('.')[0] if '.' in view.xml_id else 'unknown'}")

# Check the IAP Alternative Provider module form view
alt_provider_view = env.ref('iap_alternative_provider.iap_account_view_form', raise_if_not_found=False)
if not alt_provider_view:
    print("\nIAP Alternative Provider form view not found!")
else:
    print(f"\nFound IAP Alternative Provider form view: {alt_provider_view.name}")
    print("\nForm view arch:")
    print(alt_provider_view.arch)

# Check if the provider field is in the view
if form_view and "<field name=\"provider\"" in form_view.arch:
    print("\nProvider field found in the base IAP form view!")
else:
    print("\nProvider field NOT found in the base IAP form view.")

# Check if our module has a view that adds the provider field to the form
gatewayapi_view = env.ref('gatewayapi_sms.iap_account_view_form', raise_if_not_found=False)
if gatewayapi_view:
    print(f"\nFound GatewayAPI form view: {gatewayapi_view.name}")
    if "<field name=\"provider\"" in gatewayapi_view.arch:
        print("Provider field found in the GatewayAPI form view!")
    else:
        print("Provider field NOT found in the GatewayAPI form view.")

print("\nDone!") 