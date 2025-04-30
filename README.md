PlaySMS Connector
=================
This module implements the PlaySMS webservices api, and replaces the Odoo sms IAP.

Odoo app requirements are: iap_alternative_provider and phone_validation
Python requirements are: phonenumbers and requests

Configuration
=============

Go to: Settings > Technical > IAP > IAP Accounts

When you set the Provider of an IAP account to PlaySMS, the following
section will appear.
![IAP PlaySMS form](https://github.com/user-attachments/assets/18219aff-5c89-4e06-ab32-50c0c1fa776e)

- Service Name must be *sms*.

- **Url of PlaySMS server**,  **Username**, **Webtoken** and **From** fields
  are required, and are based on your `PlaySMS` account.The URL should be e.g.:
  **https://playsms.example.com/index.php?op=ws**

- After filling in the required fields, it is recommended to *Test
  Connection*. Result will be displayed in the *Connection status*
  field.

If you would like to be notified when your credits/tokens start running
low, set a desired minumum ammount of tokens. To disable notifications or if you have unlimited credits
set the field to a negative number e.g. -1. 
This field is only used for notification purposes. If you decide to fill this field *Token
notification action* field will appear. This field can accept any server
action which will be executed daily(by default) via cron job, if your
current token level is lower than the minumum amount you have set.

If you would like to change the interval of the credit balance check
you can access the action by:

- Settings > Technical > Automation > Scheduled action
- Select the action named “PlaySMS: Check credit balance”.

There's a default notification action that creates an activity
for the admin under the SMS IAP, notifying him to “Buy more credits".

This module is strongly inspired by the  following module https://github.com/rokpremrl/smsapisi-odoo
