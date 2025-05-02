GatewayAPI SMS Connector
=======================
This module implements the GatewayAPI REST API for SMS, and replaces the Odoo sms IAP with GatewayAPI integration.

Odoo app requirements are: iap_alternative_provider and phone_validation
Python requirements are: phonenumbers and requests

Configuration
=============

Go to: Settings > Technical > IAP > IAP Accounts

When you set the Provider of an IAP account to **GatewayAPI**, the following section will appear.

- Service Name must be *sms*.
- **API Token** is required and is based on your GatewayAPI account. You can find your API token in the GatewayAPI dashboard.

After filling in the required fields, it is recommended to *Test Connection*. The result will be displayed in the *Connection status* field.

**API Token Visibility:**
You can now toggle the visibility of your API Token using the eye (show) and eye-slash (hide) buttons next to the token field. By default, the token is hidden (masked). Clicking the eye icon will reveal the token, and clicking the eye-slash icon will hide it again. This is controlled by the `show_token` field and the `action_toggle_show_token` server action.

If you would like to be notified when your credits/tokens start running low, set a desired minimum amount of tokens. To disable notifications or if you have unlimited credits, set the field to a negative number (e.g. -1). This field is only used for notification purposes. If you decide to fill this field, the *Token notification action* field will appear. This field can accept any server action which will be executed daily (by default) via cron job, if your current token level is lower than the minimum amount you have set.

**Credit Check Interval:**
You can set how often Odoo checks your GatewayAPI credit balance directly in the IAP Account form using the "Check interval" and "Interval type" fields. The scheduled action will automatically update to match your settings.

There's a default notification action that creates an activity for the admin under the SMS IAP, notifying them to "Buy more credits".

This module is strongly inspired by the following module: https://github.com/rokpremrl/smsapisi-odoo

## Installation

### From Odoo Apps Store
1. Download the module ZIP from the Odoo Apps Store.
2. Extract the ZIP and place the `gatewayapi_sms` folder in your Odoo `addons` directory.
3. Restart your Odoo server.
4. Activate Developer Mode in Odoo.
5. Go to Apps, click 'Update Apps List', then search for 'GatewayAPI SMS Connector' and install it.

### From GitHub
1. Clone the repository:
   ```sh
   git clone https://github.com/waltherB/gatewayapi_sms.git
   ```
2. Move the `gatewayapi_sms` folder to your Odoo `addons` directory.
3. Ensure the following Python dependencies are installed:
   - `phonenumbers`
   - `requests`
   You can install them with:
   ```sh
   pip install phonenumbers requests
   ```
4. Restart your Odoo server.
5. Activate Developer Mode in Odoo.
6. Go to Apps, click 'Update Apps List', then search for 'GatewayAPI SMS Connector' and install it.
