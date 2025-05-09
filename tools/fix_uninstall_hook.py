#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script directly patches the gatewayapi_sms module's __init__.py file
to fix the uninstall_hook signature for Odoo 17 compatibility.
"""

import os
import sys
import re
import shutil
import argparse
from datetime import datetime

def find_module_path(base_path, module_name):
    """Find the module path in the Odoo addons directories"""
    print(f"Searching for {module_name} in {base_path}")
    
    # Handle the direct case where module is directly in the path
    direct_path = os.path.join(base_path, module_name)
    init_file = os.path.join(direct_path, '__init__.py')
    if os.path.exists(init_file):
        print(f"Found module directly at {direct_path}")
        return direct_path
    
    # Search subdirectories
    for root, dirs, files in os.walk(base_path):
        if os.path.basename(root) == module_name and '__init__.py' in files:
            print(f"Found module at {root}")
            return root
    
    print(f"Module not found in {base_path}")
    return None

def backup_file(file_path):
    """Create a backup of the file"""
    backup_path = f"{file_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")
    return backup_path

def patch_uninstall_hook(file_path):
    """Patch the uninstall_hook function to work with Odoo 17"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if the file already has the fixed uninstall_hook
    if "def uninstall_hook(first_param, registry=None)" in content:
        print("File already has the fixed uninstall_hook signature.")
        return False
    
    # Replace the function signature and add parameter handling
    pattern = r"def uninstall_hook\(cr, registry\):"
    replacement = """def uninstall_hook(first_param, registry=None):
    \"\"\"Cleanup hook to remove GatewayAPI elements from IAP views
    
    Can be called as either:
    - uninstall_hook(cr, registry) - Odoo <= 16 
    - uninstall_hook(env) - Odoo 17+
    \"\"\"
    import logging
    _logger = logging.getLogger(__name__)
    
    _logger.info("Running uninstall_hook for gatewayapi_sms")
    
    try:
        # Determine if we got env or cr as first parameter
        if hasattr(first_param, 'cr'):
            # We received env as the first parameter
            env = first_param
            cr = env.cr
        else:
            # We received cr as the first parameter
            cr = first_param
            # Create environment"""
    
    if not re.search(pattern, content):
        print("Could not find the uninstall_hook function signature.")
        return False
    
    patched_content = re.sub(pattern, replacement, content)
    
    # Update the SQL to handle JSONB format
    patched_content = patched_content.replace(
        "UPDATE ir_ui_view\n                SET arch_db = regexp_replace(arch_db,",
        "UPDATE ir_ui_view\n                SET arch_db = regexp_replace(arch_db::text,"
    )
    patched_content = patched_content.replace(
        "'g')\n                WHERE model = 'iap.account'\n                AND arch_db LIKE '%gatewayapi%';",
        "'g')::jsonb\n                WHERE model = 'iap.account'\n                AND arch_db::text LIKE '%gatewayapi%';"
    )
    
    with open(file_path, 'w') as f:
        f.write(patched_content)
    
    print(f"Successfully patched {file_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Fix the uninstall_hook in gatewayapi_sms module')
    parser.add_argument('--odoo-path', default='/opt/odoo/odoo', 
                       help='Path(s) to search for the module. Separate multiple paths with semicolons.')
    args = parser.parse_args()
    
    # Parse paths
    search_paths = args.odoo_path.split(';')
    print(f"Will search in the following paths: {search_paths}")
    
    # Add some standard paths
    standard_paths = [
        '/usr/lib/python3/dist-packages/odoo/addons',
        '/opt/odoo/custom/addons',
        '/mnt/extra-addons'
    ]
    for path in standard_paths:
        if path not in search_paths and os.path.exists(path):
            search_paths.append(path)
    
    # Try to find the module in the specified paths
    module_path = None
    for base_path in search_paths:
        if not os.path.exists(base_path):
            print(f"Path {base_path} does not exist, skipping")
            continue
            
        # Check if module is directly in this path
        found_path = find_module_path(base_path, 'gatewayapi_sms')
        if found_path:
            module_path = found_path
            break
            
        # Check if there are any addons directories
        addons_dirs = ['addons', 'odoo/addons', 'custom/addons']
        for addon_dir in addons_dirs:
            addon_path = os.path.join(base_path, addon_dir)
            if os.path.exists(addon_path):
                found_path = find_module_path(addon_path, 'gatewayapi_sms')
                if found_path:
                    module_path = found_path
                    break
        
        if module_path:
            break
    
    if not module_path:
        print("\nCould not find the gatewayapi_sms module. Let's try a manual approach.")
        print("Please enter the full path to the gatewayapi_sms module directory:")
        manual_path = input("> ").strip()
        
        if os.path.exists(manual_path) and os.path.exists(os.path.join(manual_path, '__init__.py')):
            module_path = manual_path
        else:
            print("Invalid path or __init__.py not found in the specified directory.")
            sys.exit(1)
    
    init_file = os.path.join(module_path, '__init__.py')
    if not os.path.exists(init_file):
        print(f"Could not find __init__.py in {module_path}")
        sys.exit(1)
    
    # Backup and patch the file
    print(f"Found gatewayapi_sms module at {module_path}")
    backup_file(init_file)
    if patch_uninstall_hook(init_file):
        print("\nSuccessfully patched the uninstall_hook function.")
        print("You should now be able to uninstall the module.")
        print("\nFor the changes to take effect, you need to restart the Odoo server.")
    else:
        print("\nNo changes were made to the file.")

if __name__ == "__main__":
    main() 