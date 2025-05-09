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

# Run diagnostic first to see what we're dealing with
echo "1) Running diagnostics on IAP account views..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$(dirname "$0")/inspect_view.sql"

read -p "Continue with the fix? (y/n) " -n 1 -r
echo    # move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operation canceled by user."
    unset PGPASSWORD
    exit 0
fi

# Run the comprehensive fix for IAP views
echo "2) Completely recreating IAP views (the most reliable fix)..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$(dirname "$0")/recreate_iap_views.sql"

echo "3) Running additional cleanup..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$(dirname "$0")/fix_iap_views.sql"

# Clear the password from environment
unset PGPASSWORD

echo ""
echo "Cleanup complete!"
echo "Please restart your Odoo server immediately to see the changes."
echo ""
echo "If you still encounter issues after restarting, try these emergency options:"
echo "  1. Emergency view fix (tries to fix broken views):"
echo "     psql -h \"$DB_HOST\" -p \"$DB_PORT\" -U \"$DB_USER\" -d \"$DB_NAME\" -f \"$(dirname "$0")/fix_broken_view.sql\""
echo "  2. Run diagnostics to see what might be wrong:"
echo "     psql -h \"$DB_HOST\" -p \"$DB_PORT\" -U \"$DB_USER\" -d \"$DB_NAME\" -f \"$(dirname "$0")/inspect_view.sql\""

exit 0 