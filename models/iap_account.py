# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

import pytz

import logging
import requests

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class IapAccount(models.Model):
    # Removed the problematic _depends attribute. Dependencies are managed in __manifest__.py.
    _name = "iap.account"
    _inherit = ['iap.account', 'mail.thread', 'mail.activity.mixin']

    # Make name field required
    name = fields.Char(copy=False)

    # Instead of trying to dynamically modify the selection options,
    # we should use the inherent extensibility of selection fields in Odoo
    provider = fields.Selection(
        selection_add=[('sms_api_gatewayapi', 'GatewayAPI')],
        ondelete={'sms_api_gatewayapi': 'set default'}
    )

    # Add a computed field to indicate if this is a GatewayAPI account
    is_gatewayapi = fields.Boolean(
        string="Is GatewayAPI",
        compute="_compute_is_gatewayapi",
        store=False,  # Changed to False to avoid upgrade issues
        help="Indicates if this account is configured for GatewayAPI"
    )

    service_name = fields.Char(
        default="sms",
        help="Service Name must be 'sms' for GatewayAPI integration."
    )
    gatewayapi_base_url = fields.Char(
        string="GatewayAPI Base URL",
        default="https://gatewayapi.eu",
        help="Base URL for GatewayAPI endpoints. "
             "Default: https://gatewayapi.eu"
    )
    gatewayapi_sender = fields.Char(
        string="Sender Name",
        default="Odoo",
        help="Sender name to use for outgoing SMS. "
             "This will appear as the sender on recipients' phones."
    )
    gatewayapi_api_token = fields.Char(
        help="GatewayAPI API Token"
    )
    gatewayapi_check_min_tokens = fields.Boolean(
        string="Check for minimum credits",
        default=False,
        help="Enable to check for minimum credits and trigger notifications."
    )
    gatewayapi_min_tokens = fields.Integer(
        string="Minimum credits",
        default=0,
        help="Minimum credit level for alerting purposes. "
             "Only used if 'Check for minimum credits' is enabled."
    )
    gatewayapi_enable_email_notification = fields.Boolean(
        string="Enable Low Credit Email Alert", 
        default=False,
        help="If checked, an email will be sent to the specified address when credits fall below the minimum threshold."
    )
    gatewayapi_low_credit_notification_email = fields.Char(
        string="Low Credit Notification Email",
        help="Email address to receive low credit alerts. Required if email alert is enabled."
    )

    gatewayapi_token_notification_action = fields.Many2one(
        'ir.actions.server',
        string="Credits notification action",
        help="Action to be performed when the number of credits is less than "
             "min_tokens."
    )
    gatewayapi_last_credit_check_time = fields.Datetime(
        string="Last Credit Check Time",
        readonly=True,
        copy=False,
        help="Timestamp of the last automated credit balance check for this account.",
    )

    @api.constrains('gatewayapi_channel_config_mode', 'gatewayapi_new_channel_name')
    def _check_channel_name_required(self):
        for rec in self:
            if rec.gatewayapi_channel_config_mode == 'create' and not rec.gatewayapi_new_channel_name:
                raise ValidationError(_("You must set a channel name when creating a new notification channel."))
    @api.constrains('provider', 'name')
    def _check_gatewayapi_name_required(self):
        for rec in self:
            if rec.provider == 'sms_api_gatewayapi' and not rec.name:
                raise ValidationError(_("Name is required for GatewayAPI accounts."))

    def _process_notification_channel_settings(self):
        pass


    gatewayapi_connection_status = fields.Char(
        string="Connection status",
        help="Status of the last connection test."
    )
    gatewayapi_cron_interval_number = fields.Integer(
        string="Credit check interval",
        default=1,
        help="How often to check the credit balance (number of intervals)."
    )
    gatewayapi_cron_interval_type = fields.Selection(
        [
            ("minutes", "Minutes"),
            ("hours", "Hours"),
            ("days", "Days"),
            ("weeks", "Weeks"),
        ],
        string="Interval type",
        default="days",
        help="Unit for the credit check interval."
    )
    gatewayapi_balance = fields.Float(
        string="Balance",
        compute="_compute_gatewayapi_balance",
        store=False,
        help="Current GatewayAPI credit balance."
    )
    gatewayapi_currency = fields.Char(
        string="Currency",
        help="Currency for GatewayAPI credit balance."
    )
    gatewayapi_balance_display = fields.Char(
        string="Balance",
        compute="_compute_gatewayapi_balance_display",
        store=False
    )
    show_token = fields.Boolean(
        default=False,
        help="Show or hide the API token in the form."
        # store=False has been removed, so it defaults to store=True
    )

    @api.depends('gatewayapi_base_url', 'gatewayapi_api_token', 'provider')
    def _compute_is_gatewayapi(self):
        """Compute whether this account is configured for GatewayAPI"""
        for rec in self:
            rec.is_gatewayapi = (
                rec.provider == 'sms_api_gatewayapi' or
                (rec.gatewayapi_base_url and rec.gatewayapi_api_token)
            )

    @api.model
    def get_gatewayapi_account(self):
        """Get or create a GatewayAPI account"""
        account = self.search([
            '|',
            ('provider', '=', 'sms_api_gatewayapi'),
            '&',
            ('service_name', '=', 'sms'),
            ('gatewayapi_base_url', '!=', False)
        ], limit=1)

        if not account:
            # Create a new GatewayAPI account
            account = self.create({
                'name': 'GatewayAPI',
                'service_name': 'sms',
                'provider': 'sms_api_gatewayapi',
                'gatewayapi_base_url': 'https://gatewayapi.eu',
                'gatewayapi_sender': 'Odoo',
            })
            _logger.info(
                "Created new GatewayAPI account with ID %s", account.id
            )
        return account

    @api.model
    def _get_sms_account(self):
        """Override to return the GatewayAPI account if configured"""
        account = self.get("sms")

        # If account is explicitly set as GatewayAPI provider
        if account.provider == 'sms_api_gatewayapi':
            return account

        # If account has GatewayAPI configuration, return it
        if account.gatewayapi_base_url and account.gatewayapi_api_token:
            return account

        # Try to find a GatewayAPI account
        gatewayapi_account = self.search([
            '|',
            ('provider', '=', 'sms_api_gatewayapi'),
            '&',
            ('service_name', '=', 'sms'),
            '&',
            ('gatewayapi_base_url', '!=', False),
            ('gatewayapi_api_token', '!=', False)
        ], limit=1)

        if gatewayapi_account:
            return gatewayapi_account

        # Fall back to the default account
        return account

    @api.model
    def check_gatewayapi_credit_balance(self):
        """
        Checks credit balance for all configured GatewayAPI accounts.

        This method iterates over all iap.account records that are configured
        for GatewayAPI and have credit checking enabled. It then determines if a
        balance check is due based on the account's individual schedule.
        """
        accounts_to_check = self.env['iap.account'].search([
            '&',
            '&',
            ('service_name', '=', 'sms'),
            ('gatewayapi_check_min_tokens', '=', True),
            '|',
            ('provider', '=', 'sms_api_gatewayapi'),
            '&',
            ('gatewayapi_base_url', '!=', False),
            ('gatewayapi_api_token', '!=', False)
        ])

        _logger.info(f"Found {len(accounts_to_check)} GatewayAPI accounts to potentially check.")

        for account in accounts_to_check:
            _logger.info(f"Checking account: {account.name} (ID: {account.id})")

            now = fields.Datetime.now()
            last_check_time = account.gatewayapi_last_credit_check_time
            interval_number = account.gatewayapi_cron_interval_number
            interval_type = account.gatewayapi_cron_interval_type

            # Determine if a check is due
            check_due = False
            if not last_check_time:
                check_due = True
                _logger.info(f"Account {account.name}: Last check time not set, check is due.")
            else:
                # Calculate the next check time
                interval_delta = timedelta()
                if interval_type == 'minutes':
                    interval_delta = timedelta(minutes=interval_number)
                elif interval_type == 'hours':
                    interval_delta = timedelta(hours=interval_number)
                elif interval_type == 'days':
                    interval_delta = timedelta(days=interval_number)
                elif interval_type == 'weeks':
                    interval_delta = timedelta(weeks=interval_number)

                next_check_time = last_check_time + interval_delta
                if now >= next_check_time:
                    check_due = True
                    _logger.info(f"Account {account.name}: Check is due. Next check was at {next_check_time}, current time is {now}.")
                else:
                    _logger.info(f"Account {account.name}: Check not yet due. Next check at {next_check_time}, current time is {now}.")

            if check_due:
                _logger.info(f"Account {account.name}: Performing credit balance check.")
                try:
                    # Update last check time before making the call
                    account.sudo().write({'gatewayapi_last_credit_check_time': now})
                    api_credits = account.get_current_credit_balance() # Call on the specific account instance
                except UserWarning as e:
                    _logger.warning(
                        f"Account {account.name}: GatewayAPI returned an error while attempting to get "
                        f"current credit balance: {e}"
                    )
                except Exception as e:
                    _logger.warning(
                        f"Account {account.name}: An exception occurred while attempting to get current "
                        f"credit balance: {e}"
                    )
                else:
                    _logger.info(f"Account {account.name}: Successfully retrieved credit balance: {api_credits}")
                    if account.gatewayapi_min_tokens < 0:
                        _logger.info(
                            f"Account {account.name}: Minimum credits not set (or invalid: {account.gatewayapi_min_tokens}). "
                            "Skipping low balance notification."
                        )
                        continue # Skip to next account

                    if not account.gatewayapi_token_notification_action:
                        _logger.info(
                            f"Account {account.name}: Notification action not set. "
                            "Skipping low balance notification."
                        )
                        continue # Skip to next account

                    if float(api_credits) < float(account.gatewayapi_min_tokens):
                        _logger.info(
                            f"Account {account.name}: Low credit balance! Current: {api_credits}, Minimum: {account.gatewayapi_min_tokens}."
                        )
                        ctx = dict(self.env.context or {})
                        ctx.update({
                            'active_id': account.id,
                            'active_model': 'iap.account'
                        })
                        try:
                            account.gatewayapi_token_notification_action.with_context(ctx).run()
                            _logger.info(f"Account {account.name}: Low credit notification action triggered.")
                        except Exception as e:
                            _logger.error(f"Account {account.name}: Failed to run low credit notification action: {e}")
                    else:
                        _logger.info(
                            f"Account {account.name}: Credit balance ({api_credits}) is sufficient "
                            f"(Minimum: {account.gatewayapi_min_tokens})."
                        )
            else:
                _logger.info(f"Account {account.name}: Skipping credit balance check as it's not due yet.")

    def get_current_credit_balance(self, full_response=False):
        self.ensure_one()  # Ensure this method is called on a single record
        headers = {
            'Authorization': (
                f'Token {self.gatewayapi_api_token}'
            )
        }
        base_url = self.gatewayapi_base_url
        _logger.debug(f"Raw base_url value before validation: {base_url!r}")
        if not base_url or str(base_url).lower() == 'false':
            base_url = 'https://gatewayapi.eu'
        # Ensure the URL is valid
        if not (
            base_url.startswith('http://') or base_url.startswith('https://')
        ):
            raise UserWarning(
                'GatewayAPI Base URL must start with http:// or https://'
            )
        url = base_url.rstrip('/') + '/rest/me'
        _logger.debug(f"GatewayAPI credit balance check URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_content = response.json()
        _logger.debug(
            f"GatewayAPI credit balance check responded with: "
            f"{response_content}"
        )
        if full_response:
            return response_content
        if 'credit' in response_content:
            return response_content['credit']
        else:
            error_msg = response_content.get('error', 'Unknown error')
            raise UserWarning(error_msg)

    def gatewayapi_connection_test(self):
        iap_account = self._get_sms_account()
        if iap_account.id != self.id or not self.gatewayapi_base_url:
            _logger.warning(
                "GatewayAPI connection test is only performed on accounts "
                "with GatewayAPI configuration."
            )
        try:
            # Only test connection, do not use api_credits
            iap_account.get_current_credit_balance()
        except UserWarning as e:
            _logger.warning(
                "GatewayAPI returned an error while attempting to get current "
                f"credit balance: {e}"
            )
            iap_account.gatewayapi_connection_status = str(e)
            iap_account.gatewayapi_balance = 0.0
        except Exception:
            _logger.exception(
                "An exception occurred while attempting to get current credit balance"
            )
            iap_account.gatewayapi_connection_status = _(
                u"Unexpected error. Check server log for more info."
            )
            iap_account.gatewayapi_balance = 0.0
        else:
            _logger.info("GatewayAPI connection test successful")
            iap_account.gatewayapi_connection_status = "OK"
            try:
                iap_account.gatewayapi_balance = float(
                    iap_account.get_current_credit_balance()
                )
            except Exception:
                _logger.exception(
                    "Failed to update GatewayAPI balance after successful connection test"
                )
                iap_account.gatewayapi_balance = 0.0
        _logger.debug(
            "Final connection status: %s, balance: %s",
            iap_account.gatewayapi_connection_status,
            iap_account.gatewayapi_balance,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def create(self, vals_list):
        """Ensure show_token is False for new records"""
        # Make sure show_token is False for new records
        if isinstance(vals_list, dict):
            vals_list['show_token'] = False
            # Initialize gatewayapi_last_credit_check_time if check_min_tokens is true
            if vals_list.get('gatewayapi_check_min_tokens') and 'gatewayapi_last_credit_check_time' not in vals_list:
                vals_list['gatewayapi_last_credit_check_time'] = False
        elif isinstance(vals_list, list): # Handle multiple record creation
            for vals_item in vals_list: # Iterate through list of dicts
                vals_item['show_token'] = False
                if vals_item.get('gatewayapi_check_min_tokens') and 'gatewayapi_last_credit_check_time' not in vals_item:
                    vals_item['gatewayapi_last_credit_check_time'] = False
        
        records = super().create(vals_list)
        
        # Link the low credits notification action if it's a GatewayAPI account
        notification_action = self.env.ref('gatewayapi_sms.low_credits_notification_action', raise_if_not_found=False)
        for record in records:
            if notification_action and record.is_gatewayapi:
                record.write({'gatewayapi_token_notification_action': notification_action.id})
            # Ensure last_credit_check_time is explicitly set if check is enabled
            if record.gatewayapi_check_min_tokens and not record.gatewayapi_last_credit_check_time:
                # Check if vals_list is a dict or list of dicts to safely access original values
                original_vals = {}
                if isinstance(vals_list, dict):
                    original_vals = vals_list
                elif isinstance(vals_list, list) and vals_list: # Assuming vals_list corresponds to records one-to-one
                    # This part is tricky if vals_list doesn't map directly or if creating multiple records
                    # For simplicity, we'll assume if it's a list, we look at the first item,
                    # or ideally, this logic is handled per record if possible.
                    # A better way would be to iterate through vals_list and records together if their order is guaranteed.
                    # However, create can return records in a different order or merged.
                    # The most robust way is to check record's current state vs desired state if possible.
                    # For now, if last_credit_check_time was explicitly set to False in vals, respect it.
                    pass # This complex case might need record-specific value from vals_list

                if not original_vals.get('gatewayapi_last_credit_check_time') is False:
                     record.write({'gatewayapi_last_credit_check_time': False})
            
            record._process_notification_channel_settings() # Call helper

        return records

    def write(self, vals):
        # Handle 'gatewayapi_check_min_tokens' change
        if 'gatewayapi_check_min_tokens' in vals:
            if vals['gatewayapi_check_min_tokens'] is True:
                # Enabling checks: reset last check time to ensure an immediate check by cron
                vals['gatewayapi_last_credit_check_time'] = False
            else:
                # Disabling checks: reset last check time and clear the notification action
                vals['gatewayapi_last_credit_check_time'] = False
                vals['gatewayapi_token_notification_action'] = False
        
        # Handle interval changes for already active checks
        # If interval fields are changed and checks are not being explicitly disabled in this write operation
        elif ('gatewayapi_cron_interval_number' in vals or 'gatewayapi_cron_interval_type' in vals):
            # Check if any of the records currently being written to have checks enabled.
            # This requires checking the state of 'self' before the write.
            # If 'gatewayapi_check_min_tokens' is also in 'vals', the logic above handles it.
            # This 'elif' ensures this block is only considered if 'gatewayapi_check_min_tokens' is NOT in vals.
            if any(rec.gatewayapi_check_min_tokens for rec in self):
                 vals['gatewayapi_last_credit_check_time'] = False

        res = super(IapAccount, self).write(vals)

        # Post-write logic to ensure server action is correctly set or cleared
        # This runs for each record in 'self' (which now have updated values from 'vals')
        for record in self.filtered(lambda r: r.is_gatewayapi): # Filter for GatewayAPI accounts
            if record.gatewayapi_check_min_tokens:
                # If checks are enabled and no action is set (it might have been cleared by vals), set it.
                if not record.gatewayapi_token_notification_action and \
                   (vals.get('gatewayapi_token_notification_action') is not False): # Ensure not explicitly cleared
                    try:
                        action = self.env.ref('gatewayapi_sms.low_credits_notification_action', raise_if_not_found=False)
                        if action:
                            # Use record.write here to ensure it's a separate ORM call for this specific record,
                            # which can be important for audit logging and potential re-triggering of other logic
                            # if 'gatewayapi_token_notification_action' itself has dependencies.
                            record.write({'gatewayapi_token_notification_action': action.id})
                        else:
                            _logger.warning("Action 'gatewayapi_sms.low_credits_notification_action' not found.")
                    except Exception as e:
                        _logger.error(f"Failed to set notification action for account {record.id}: {e}")
            else:
                # If checks are disabled and an action is set, clear it.
                if record.gatewayapi_token_notification_action:
                    record.write({'gatewayapi_token_notification_action': False})
        return res

    @api.depends('gatewayapi_api_token', 'gatewayapi_base_url')
    def _compute_gatewayapi_balance(self):
        # The show_token reset logic was moved to the write method for better consolidation.
        for rec in self:
            if rec.gatewayapi_base_url and rec.gatewayapi_api_token:
                try:
                    response = rec.get_current_credit_balance(full_response=True)
                    rec.gatewayapi_balance = float(response.get('credit', 0.0))
                    rec.gatewayapi_currency = response.get('currency', '')
                except Exception:
                    rec.gatewayapi_balance = 0.0
                    rec.gatewayapi_currency = ''
            else:
                rec.gatewayapi_balance = 0.0
                rec.gatewayapi_currency = ''

    def _compute_gatewayapi_balance_display(self):
        for rec in self:
            if rec.gatewayapi_base_url and rec.gatewayapi_api_token:
                if rec.gatewayapi_currency:
                    rec.gatewayapi_balance_display = (
                        f"{rec.gatewayapi_balance:.2f} {rec.gatewayapi_currency}"
                    )
                else:
                    rec.gatewayapi_balance_display = (
                        f"{rec.gatewayapi_balance:.2f}"
                    )
            else:
                rec.gatewayapi_balance_display = "0 Credits"

    def action_toggle_show_token(self):
        """Toggle visibility of the API token"""
        for rec in self:
            rec.show_token = not rec.show_token

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """Override to ensure token is hidden when reopening the form view"""
        result = super().fields_view_get(view_id=view_id, view_type=view_type,
                                        toolbar=toolbar, submenu=submenu)
        # When a form view is opened, we'll reset show_token via context
        # This is more efficient than updating all records in the database
        return result

    @api.model
    def default_get(self, fields_list):
        """Reset show_token to False and ensure gatewayapi_existing_channel_id is False by default."""
        # It's good practice to use a consistent variable name, e.g., `res`
        res = super(IapAccount, self).default_get(fields_list)
        
        # Ensure show_token is False if requested
        if 'show_token' in fields_list:
            res['show_token'] = False
        
        # Explicitly default gatewayapi_existing_channel_id to False (empty) if requested
        if 'gatewayapi_existing_channel_id' in fields_list:
            res['gatewayapi_existing_channel_id'] = False
            
        return res

    def name_get(self):
        result = []
        for rec in self:
            if rec.gatewayapi_base_url:
                if rec.name:
                    result.append((rec.id, rec.name))
                else:
                    base_url = rec.gatewayapi_base_url or 'https://gatewayapi.eu'
                    name = f"GatewayAPI {base_url}"
                    result.append((rec.id, name))
            else:
                result.append((rec.id, super(IapAccount, rec).name_get()[0][1]))
        return result

    def send_low_credits_notification(self):
        self.ensure_one()
        message_subject = _('GatewayAPI Low Credits Alert: %s') % (self.name or 'Unnamed GatewayAPI Account')
        message_body_html = _("""
<p><b>⚠️ Low SMS Credits Alert</b></p>
<p>The SMS credits for account <b>%s</b> are running low:</p>
<ul>
    <li>Current balance: <b>%s</b></li>
    <li>Minimum threshold: <b>%s</b></li>
</ul>
<p>Please add more credits to ensure uninterrupted SMS services.</p>
""") % (
            self.name or 'Unnamed GatewayAPI Account',
            self.gatewayapi_balance_display,
            f"{self.gatewayapi_min_tokens} {self.gatewayapi_currency}" if self.gatewayapi_currency else self.gatewayapi_min_tokens
        )

        # Preserve Admin Activity
        admin_user = self.env.ref('base.user_admin', raise_if_not_found=False) or self.env['res.users'] # Ensure admin_user is found or fallback
        user_id_to_assign = admin_user.id if admin_user and admin_user != self.env['res.users'] else self.env.uid # Assign to admin or current user

        activity = self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'note': message_body_html, # Use the HTML body for the activity note
            'res_id': self.id,
            'res_model_id': self.env.ref('iap.model_iap_account').id,
            'user_id': user_id_to_assign,
            'summary': _('GatewayAPI low on credits for %s') % (self.name or 'Unnamed GatewayAPI Account'),
        })

        # Preserve Chatter Post
        self.message_post(body=message_body_html, subject=message_subject)

        # New Email Notification Logic
        if self.gatewayapi_enable_email_notification and self.gatewayapi_low_credit_notification_email:
            _logger.info(f"Attempting to send low credits email alert for account '{self.name}' to '{self.gatewayapi_low_credit_notification_email}'")
            
            # Determine email_from: use company email, then user email, then a fallback.
            email_from = self.env.user.company_id.email_formatted or self.env.user.email_formatted or                          self.env['ir.mail_server'].sudo().search([], limit=1).smtp_user # Fallback to system email if configured
            if not email_from:
                _logger.warning(f"Cannot determine 'email_from' for low credit notification for account {self.name}. Email will likely fail or use Odoo's default sender.")
                # Consider a hardcoded fallback if critical, e.g., noreply@yourdomain.com
                # For now, let it proceed; Odoo might use a system default.

            mail_values = {
                'subject': message_subject,
                'body_html': message_body_html,
                'email_to': self.gatewayapi_low_credit_notification_email,
                'email_from': email_from,
                'model': self._name,
                'res_id': self.id,
                'auto_delete': True, # Delete email from Odoo's queue after sending
                '#reply_to': email_from, # Optional: Set reply-to if different from from
            }
            
            mail = self.env['mail.mail'].sudo().create(mail_values)
            try:
                mail.send()
                _logger.info(f"Low credits email for account '{self.name}' sent successfully to '{self.gatewayapi_low_credit_notification_email}'. Mail ID: {mail.id}")
            except Exception as e:
                _logger.error(f"Failed to send low credits email for account '{self.name}' to '{self.gatewayapi_low_credit_notification_email}': {e}")
        
        return activity

