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

If you would like to be notified when your credits/tokens start running low, set a desired minimum amount of tokens. To disable notifications or if you have unlimited credits, set the field to a negative number (e.g. -1). This field is only used for notification purposes. If you decide to fill this field, the *Token notification action* field will appear. This field can accept any server action which will be executed daily (by default) via cron job, if your current token level is lower than the minimum amount you have set.

If you would like to change the interval of the credit balance check you can access the action by:

- Settings > Technical > Automation > Scheduled action
- Select the action named “GatewayAPI: Check credit balance”.

There's a default notification action that creates an activity for the admin under the SMS IAP, notifying them to “Buy more credits".

This module is strongly inspired by the following module: https://github.com/rokpremrl/smsapisi-odoo
