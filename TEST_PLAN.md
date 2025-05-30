# GatewayAPI SMS Connector Test Plan for Odoo 17

This document outlines steps to test and verify the GatewayAPI SMS module functionality in Odoo 17.

## Prerequisites

1. A valid GatewayAPI account with API token
2. Odoo 17 installation with module installed
3. Admin access to Odoo

## Test Procedure

### 1. Configuration Tests

1. **Access GatewayAPI Settings**
   - Go to Settings → Technical → GatewayAPI SMS Accounts
   - Verify the GatewayAPI accounts list view appears
   - Click "Create GatewayAPI Account" to create a new account

2. **Configure GatewayAPI Account**
   - Fill in the following fields:
     - Name: GatewayAPI
     - Service Name: sms (must be exactly this value)
     - GatewayAPI Base URL: https://gatewayapi.eu
     - Sender Name: Your preferred sender name
     - API Token: Your GatewayAPI API token
   - Click "Test Connection" button
   - Verify "Connection status" shows "OK"
   - Verify Balance field shows your current credit balance
   - Note that the account is automatically marked as a GatewayAPI account (shown in blue in the list)

3. **Configure Notification Settings**
   - Enable "Check for minimum credits"
   - Set "Minimum credits" to a value higher than your current balance for testing
   - Set Check interval to something small (e.g. 5 minutes) for testing
   - Save the account

### 2. Functional Tests

1. **Send Test SMS**
   - Go to Settings → Technical → SMS Marketing → SMS
   - Create a new SMS message
   - Enter a valid phone number in E.164 format (e.g. +4712345678)
   - Enter a test message
   - Click Send
   - Verify the SMS status changes to "Sent"
   - Check the recipient phone to confirm receipt

2. **Test Emoji Handling**
   - Create another SMS with emojis in the message (e.g. "Hello 👋 from Odoo 😊")
   - Send to a valid number
   - Verify the SMS is received with emojis intact

3. **Credit Check Test**
   - Wait for the scheduled credit check to run (or trigger manually in debug mode)
   - Verify you receive a notification about low credits
   - Check Activities dashboard for the notification

### 3. Diagnostic Tests

1. **Run Diagnostic Script**
   - Access Odoo shell:
     ```
     python odoo-bin shell -c /path/to/odoo.conf -d your_database --addons-path=/path/to/addons
     ```
   - Execute:
     ```python
     exec(open('scripts/check_gatewayapi_config.py').read())
     ```
   - Verify output shows correct configuration values
   - Verify balance is displayed correctly

2. **Run Account Fix Script (Advanced Diagnostics)**
   - The `scripts/fix_provider_field.py` (previously may have been referred to as `fix_gatewayapi_accounts.py`) is generally no longer needed for initial setup, as the provider field should set automatically when GatewayAPI URL and Token are entered.
   - This script is retained for:
     - Advanced diagnostics of persistent configuration problems.
     - Fixing data integrity issues on existing accounts (e.g., ensuring `service_name` is 'sms').
     - Use with older, unpatched versions of the module.
   - Before running, ensure your module is up-to-date. The script itself contains a warning about its use.
   - If, after ensuring your system is up-to-date and credentials are correctly entered, you still suspect an issue that this script might address:
     ```python
     exec(open('scripts/fix_provider_field.py').read())
     ```
   - The script attempts to ensure that accounts with GatewayAPI credentials are correctly marked with the 'sms_api_gatewayapi' provider and have `service_name` set to 'sms'.
   - Verify its output for any actions taken or accounts checked.

## Troubleshooting

If you encounter issues:

1. **Connection Issues**
   - Verify API token is correct
   - Check internet connectivity
   - Confirm GatewayAPI service is operational

2. **SMS Not Sending**
   - Check IAP account balance
   - Verify phone number format (must be E.164, e.g., +4512345678)
   - Check error messages in SMS record
   - Enable debug/developer mode to see detailed errors

3. **Balance Not Showing**
   - Verify API token
   - Check if service_name is set to "sms"
   - Verify base URL is correct

4. **GatewayAPI Not Being Used**
   - Verify `is_gatewayapi` field is True (or the account is highlighted in blue in the list view) for your account after entering credentials.
   - If the provider field did not set automatically, first check module version, Odoo logs, and ensure correct credential entry.
   - The `fix_provider_field.py` script can be used as a last resort for older versions or complex data issues to ensure the provider and service_name are correctly set.
   - Ensure at least one account has both `gatewayapi_base_url` and `gatewayapi_api_token` set for GatewayAPI functionality.

## Expected Results

- GatewayAPI account properly connects to the API
- SMS messages are successfully sent
- Special characters and emojis are handled correctly
- Credit notifications are displayed when credits are low 