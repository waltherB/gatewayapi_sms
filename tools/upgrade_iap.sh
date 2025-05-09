#!/bin/bash

# Script to upgrade the IAP module to recreate views
# This uses the Odoo command line interface

echo "IAP Module Upgrade Tool"
echo "======================="

# Default values
ODOO_BIN="/opt/odoo/odoo/odoo-bin"
DB_NAME="odoo"
DB_USER="odoo" 
DB_PASSWORD=""
DB_HOST="localhost"
DB_PORT="5432"
ODOO_CONF="/etc/odoo/odoo.conf"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --odoo-bin)
            ODOO_BIN="$2"
            shift 2
            ;;
        --odoo-conf)
            ODOO_CONF="$2"
            shift 2
            ;;
        --db-name)
            DB_NAME="$2"
            shift 2
            ;;
        --db-user)
            DB_USER="$2"
            shift 2
            ;;
        --db-password)
            DB_PASSWORD="$2"
            shift 2
            ;;
        --db-host)
            DB_HOST="$2"
            shift 2
            ;;
        --db-port)
            DB_PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# Check if Odoo binary exists
if [ ! -f "$ODOO_BIN" ]; then
    echo "Error: Odoo binary not found at $ODOO_BIN"
    echo "Specify the path with --odoo-bin parameter"
    exit 1
fi

# Ask for DB password if not provided
if [ -z "$DB_PASSWORD" ]; then
    echo "Please enter the database password:"
    read -s DB_PASSWORD
fi

# Use a temporary odoo config file with the password
TEMP_CONF=$(mktemp)
echo "Creating temporary config file at $TEMP_CONF"

# Start with the existing config file if it exists
if [ -f "$ODOO_CONF" ]; then
    cp "$ODOO_CONF" "$TEMP_CONF"
else
    # Create a minimal config
    cat > "$TEMP_CONF" << EOF
[options]
db_host = $DB_HOST
db_port = $DB_PORT
db_user = $DB_USER
db_password = $DB_PASSWORD
EOF
fi

# Make sure the database options are set in the config
sed -i -e "s/db_host = .*/db_host = $DB_HOST/" "$TEMP_CONF"
sed -i -e "s/db_port = .*/db_port = $DB_PORT/" "$TEMP_CONF"
sed -i -e "s/db_user = .*/db_user = $DB_USER/" "$TEMP_CONF"
sed -i -e "s/db_password = .*/db_password = $DB_PASSWORD/" "$TEMP_CONF"

echo "Running IAP module upgrade..."
echo "This will recreate the IAP views from scratch."

# Run the upgrade
"$ODOO_BIN" -c "$TEMP_CONF" --stop-after-init -d "$DB_NAME" -u iap

# Clean up the temporary config file
rm "$TEMP_CONF"

echo ""
echo "IAP module upgrade complete!"
echo "This should have recreated all IAP views from their original definitions."
echo "Please start your Odoo server normally and check if the issue is resolved."

exit 0 