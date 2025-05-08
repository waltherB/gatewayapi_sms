#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to inspect IAP account model in Odoo 17
Run this in the Odoo shell with:
    python odoo-bin shell -c /path/to/odoo.conf -d your_database --addons-path=/path/to/addons
Then execute:
    exec(open('scripts/inspect_iap_account.py').read())
"""

import inspect
from pprint import pprint

print('=== IAP Account Model Inspection ===')

# Get the IAP account model
IapAccount = env['iap.account']

# Show model attributes
print('\nModel attributes:')
model_attrs = [attr for attr in dir(IapAccount) if not attr.startswith('_')]
pprint(model_attrs)

# Show field definitions
print('\nField definitions:')
fields = env['iap.account']._fields
for field_name, field in fields.items():
    print(f'{field_name}: {field.type} {getattr(field, "selection", None)}')

# Check for provider field
print('\nProvider field details:')
if 'provider' in fields:
    provider_field = fields['provider']
    print(f'Type: {provider_field.type}')
    print(f'Selection: {getattr(provider_field, "selection", None)}')
    print(f'Default: {getattr(provider_field, "default", None)}')
    
    # Show existing values in the database
    print('\nExisting provider values in database:')
    providers = env['iap.account'].search([]).mapped('provider')
    print(f'Unique provider values: {set(providers)}')
else:
    print('Provider field not found in the model')

# Check selection field type
print('\nSelection field details:')
selection_fields = {name: field for name, field in fields.items() 
                   if field.type == 'selection'}
for name, field in selection_fields.items():
    print(f'{name}: {getattr(field, "selection", None)}')

print('\nDone!') 