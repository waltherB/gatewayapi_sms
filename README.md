# GatewayAPI SMS Connector for Odoo 17

Send SMS messages directly from Odoo using the GatewayAPI service. This module replaces the default Odoo SMS IAP with a secure, feature-rich GatewayAPI integration.

---

## Features

- **Send SMS via GatewayAPI**: Seamless integration with GatewayAPI for reliable SMS delivery.
- **Secure API Token Management**: Show/hide your API token in the form with a single click.
- **Credit Balance Monitoring**: Set minimum credit thresholds and receive notifications when your balance is low.
- **Per-Account Credit Check Scheduling**: Configure individual credit check intervals (e.g., daily, hourly) for each GatewayAPI account directly on its IAP Account form. Balance checks are performed automatically for all enabled accounts based on their specific schedules.
- **Admin Notifications**: Automatic admin alerts and activities when credits run low.
- **Easy Configuration**: Intuitive form layout and clear help texts.
- **Odoo 17 Compatible**: Built and tested for Odoo 17.

---

## Requirements

- **Odoo Apps**:  
  - `iap_alternative_provider`  
  - `phone_validation`
- **Python Packages**:  
  - `phonenumbers`  
  - `requests`

Install Python dependencies with:
```sh
pip install phonenumbers requests
```

---

## Installation

### From Odoo Apps Store

1. Download the module ZIP from the Odoo Apps Store.
2. Extract the ZIP and place the `gatewayapi_sms` folder in your Odoo `custom addons` directory.
3. Restart your Odoo server.
4. Activate Developer Mode in Odoo.
5. Go to Apps, click 'Update Apps List', then search for **GatewayAPI SMS Connector** and install it.

### From GitHub

1. Clone the repository:
   ```sh
   git clone https://github.com/waltherB/gatewayapi_sms.git
   ```
2. Move the `gatewayapi_sms` folder to your Odoo `addons` or `custom addons` directory.
3. Install the required Python packages (see above).
4. Restart your Odoo server.
5. Activate Developer Mode in Odoo.
6. Go to Apps, click 'Update Apps List', then search for **GatewayAPI SMS Connector** and install it.

---

## Configuration

1. Go to **Settings > Technical > IAP Accounts**.
2. Create a new account or edit an existing one.
3. Set the Provider to "GatewayAPI" in the dropdown.
4. Fill in the required fields:
   - **Name**: Give your account a name (e.g., "GatewayAPI SMS")
   - **Service Name**: Must be `sms`.
   - **GatewayAPI Base URL**: Default is `https://gatewayapi.eu`
   - **Sender Name**: Set your preferred sender name.
   - **API Token**: Obtain from your GatewayAPI dashboard.
   - **Minimum Credits**: Set a threshold for low credit notifications.
   - **Credit Check Interval**: Configure how often to check your balance.
5. Click **Test Connection** to verify your setup. The result will be shown in the *Connection Status* field.
6. Use the eye/eye-slash button to show/hide your API token securely.

### Configuring Notification Channel for Low Credits

For each GatewayAPI IAP account, you can configure how low credit alerts are posted to an Odoo Discuss channel. These settings are found within the "Notification Channel Configuration" section on the IAP Account form:

1.  **Notification Channel Mode**:
    *   **No Channel Notifications**: Select this if you do not want low credit alerts for this account to be posted to any channel. Admin notifications (activities) will still be created.
    *   **Use Existing Channel**: Choose this to select a pre-existing Discuss channel where notifications should be posted.
        *   **Existing Notification Channel**: Appears if "Use Existing Channel" is selected. Pick the desired channel from the list.
    *   **Create New Channel**: Select this to have a new Discuss channel automatically created for this account's notifications.
        *   **New Channel Name**: Appears if "Create New Channel" is selected. You can customize the name for the new channel (default is "GatewayAPI: {Account Name} Notifications").

2.  **Channel Subscriptions** (available if mode is not 'No Channel Notifications'):
    *   **Subscribe Me to Channel**: Check this box (default: enabled) to automatically add yourself as a member to the selected or newly created notification channel.
    *   **Additional Users for Channel**: You can select other Odoo users who should also be added as members to the notification channel.

3.  **Active Notification Channel**:
    *   This read-only field displays the Discuss channel that is currently active for notifications for this IAP account, based on your configuration.

When you save the IAP Account, the system will:
- Link or create the channel as per your selection.
- Subscribe the specified users (current user if checked, and any additional users) to that channel. Note: Users are added, but not automatically removed by unchecking these options later; channel membership can be managed directly in Discuss if needed.

Low credit alerts for this account will then be posted to this "Active Notification Channel" in addition to creating an activity for the admin.

### Important Notes for Odoo 17

In Odoo 17, the SMS provider system has been simplified, but GatewayAPI will still work correctly with this module. When you configure an account with GatewayAPI settings (API token and base URL), the module will automatically:

1. Recognize it as a GatewayAPI-enabled account (shown with blue highlight in the list)
2. Use it for sending SMS instead of the default Odoo SMS gateway
3. Enable all GatewayAPI features like balance monitoring and notifications

You'll find GatewayAPI accounts in the standard IAP Accounts list, highlighted in blue.

---

## Usage

- Send SMS from Odoo using any of your configured GatewayAPI accounts.
- Receive admin notifications when a specific GatewayAPI account's credit balance drops below its set threshold.
- Automated credit balance checks are managed by a system-level scheduled action that runs frequently (e.g., hourly). The actual checking of each GatewayAPI account's balance is determined by the individual "Credit check interval" settings on that account's form. There's no need to manually edit the main "GatewayAPI: Check credit balance" scheduled action.

### Understanding Credit Check Scheduling
The module uses a central scheduled action (`GatewayAPI: Check credit balance`) that runs at a fixed interval (typically hourly). When this action triggers, it reviews all your GatewayAPI IAP accounts that have "Check for minimum credits" enabled.

For each enabled account, the system looks at its individual "Credit check interval" (e.g., every 2 hours, every 1 day) and the "Last Credit Check Time". If the configured interval has passed since the last check for that specific account, its balance will be queried from GatewayAPI, and the "Last Credit Check Time" will be updated.

This ensures that:
- Each GatewayAPI account is checked according to its own preferred frequency.
- All configured and enabled accounts are monitored independently.
- You do not need to adjust the global scheduled action's timing; only the interval settings on each IAP Account form matter for determining check frequency.

---

## Screenshots

| Configuration | Test Connection | Notification | Balance |
|---------------|----------------|--------------|---------|
| ![Configuration Example](static/description/screenshot_01_config.png) | ![Test Connection Example](static/description/screenshot_02_test_connection.png) | ![Notification](static/description/screenshot_03_notification.png) | ![Balance Example](static/description/screenshot_04_balance.png) |

### Example: Low Credits Notification Activity

This is what the admin will see in the Odoo activity stream when credits fall below the minimum threshold:

![Low credits notification activity](static/description/screenshot_05_low_credits_notification.png)

---

## Low Credits Notification

The email notification for low credits is not a traditional email, but rather an Odoo activity that appears in the admin's activity stream. This is configured in your module as follows:

- When your GatewayAPI credits fall below the minimum threshold, the system triggers the server action `model_iap_account_action_low_tokens`.
- This action creates a To-Do activity for the admin user with:
  - **Summary:** "GatewayAPI low on credits"
  - **Note:** "Buy more SMS credits with provider GatewayAPI"

**What the notification looks like:**
- The admin will see a new activity in the Odoo chatter (and in their activity dashboard) with the above summary and note.
- The activity is not a direct email, but Odoo can be configured to send email reminders for pending activities, so the admin may receive an email with the same content if reminders are enabled.

Example:

![Low credits notification activity](static/description/screenshot_05_low_credits_notification.png)

---

## Credits

- Inspired by [smsapisi-odoo/smsapisi_connector](https://github.com/waltherB/smsapisi-odoo/tree/17.0/smsapisi_connector)
- Developed by [Walther Barnett](https://github.com/waltherB)

---

## License

AGPL-3

## Troubleshooting

### The "GatewayAPI" provider option doesn't appear in selection field

After installation, you should see "GatewayAPI" as an option in the provider selection field.
If this doesn't appear, try the following steps:

1. Run the provider field fix script:
   ```
   python odoo-bin shell -c /path/to/odoo.conf -d your_database
   >>> exec(open('/path/to/addons/gatewayapi_sms/scripts/fix_provider_field.py').read())
   ```

2. Update the module:
   ```
   python odoo-bin -c /path/to/odoo.conf -d your_database -u gatewayapi_sms
   ```

3. Restart the Odoo server

### Configuration Testing

If you want to test your GatewayAPI configuration, you can use the diagnostic script:
```
python odoo-bin shell -c /path/to/odoo.conf -d your_database
>>> exec(open('/path/to/addons/gatewayapi_sms/scripts/check_provider_selection.py').read())
```

## Support

For questions and support, please contact the module maintainer.
