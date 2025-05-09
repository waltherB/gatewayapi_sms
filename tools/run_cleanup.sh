#!/bin/bash

# Script to clean up GatewayAPI references from IAP account views

echo "GatewayAPI Force Cleanup Tool"
echo "============================"

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "Error: psql command not found. Please install PostgreSQL client tools."
    exit 1
fi

# Default values
DB_NAME="odoo"
DB_USER="odoo"
DB_HOST="localhost"
DB_PORT="5432"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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

# Check if DB_PASSWORD is set
if [ -z "$DB_PASSWORD" ]; then
    echo "Please enter the database password:"
    read -s DB_PASSWORD
fi

echo "Running SQL cleanup on database $DB_NAME@$DB_HOST:$DB_PORT"

# Use PGPASSWORD environment variable to pass password to psql
export PGPASSWORD="$DB_PASSWORD"

# Run the comprehensive fix for IAP views
echo "Running comprehensive fix for IAP views..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$(dirname "$0")/fix_iap_views.sql"

# Provide fallback options if the user still has issues
echo ""
echo "If you still encounter issues, you can try these additional fixes:"
echo "1. For any remaining XML issues:"
echo "   psql -h \"$DB_HOST\" -p \"$DB_PORT\" -U \"$DB_USER\" -d \"$DB_NAME\" -f \"$(dirname "$0")/fix_empty_tree_view.sql\""
echo "2. For more aggressive cleanup:"
echo "   psql -h \"$DB_HOST\" -p \"$DB_PORT\" -U \"$DB_USER\" -d \"$DB_NAME\" -f \"$(dirname "$0")/force_cleanup_jsonb.sql\""
echo "3. For direct patching of tree views:"
echo "   psql -h \"$DB_HOST\" -p \"$DB_PORT\" -U \"$DB_USER\" -d \"$DB_NAME\" -f \"$(dirname "$0")/patch_iap_tree.sql\""

# Clear the password from environment
unset PGPASSWORD

echo ""
echo "Cleanup complete!"
echo "Please restart your Odoo server to see the changes."

exit 0 