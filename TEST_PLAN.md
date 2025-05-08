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

2. **Run Account Fix Script if Needed**
   - If you encounter issues with GatewayAPI not being selected:
     ```python
     exec(open('scripts/fix_gatewayapi_accounts.py').read())
     ```
   - This will check all accounts, fix any configuration issues, and create a default GatewayAPI account if none exists
   - Verify the script output shows that at least one GatewayAPI account is available

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
   - Verify is_gatewayapi field is True for your account
   - Run the fix_gatewayapi_accounts.py script to repair any configuration issues
   - Ensure at least one account has both gatewayapi_base_url and gatewayapi_api_token set

## Expected Results

- GatewayAPI account properly connects to the API
- SMS messages are successfully sent
- Special characters and emojis are handled correctly
- Credit notifications are displayed when credits are low 