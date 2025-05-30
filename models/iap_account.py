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
    _name = "iap.account"
    _inherit = ['iap.account', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(copy=False)
    provider = fields.Selection(
        selection_add=[('sms_api_gatewayapi', 'GatewayAPI')],
        ondelete={'sms_api_gatewayapi': 'set default'}
    )
    is_gatewayapi = fields.Boolean(
        string="Is GatewayAPI",
        compute="_compute_is_gatewayapi",
        store=False,
        help="Indicates if this account is configured for GatewayAPI"
    )
    service_name = fields.Char(
        default="sms",
        help="Service Name must be 'sms' for GatewayAPI integration."
    )
    gatewayapi_base_url = fields.Char(
        string="GatewayAPI Base URL",
        default="https://gatewayapi.eu",
        help="Base URL for GatewayAPI endpoints. Default: https://gatewayapi.eu"
    )
    gatewayapi_sender = fields.Char(
        string="Sender Name",
        default="Odoo",
        help="Sender name to use for outgoing SMS. This will appear as the sender on recipients' phones."
    )
    gatewayapi_api_token = fields.Char(help="GatewayAPI API Token")
    gatewayapi_check_min_tokens = fields.Boolean(
        string="Check for minimum credits",
        default=False,
        help="Enable to check for minimum credits and trigger notifications."
    )
    gatewayapi_min_tokens = fields.Integer(
        string="Minimum credits",
        default=0,
        help="Minimum credit level for alerting purposes. Only used if 'Check for minimum credits' is enabled."
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
        help="Action to be performed when the number of credits is less than min_tokens."
    )
    gatewayapi_last_credit_check_time = fields.Datetime(
        string="Last Credit Check Time",
        readonly=True,
        copy=False,
        help="Timestamp of the last automated credit balance check for this account.",
    )
    show_token = fields.Boolean(
        default=False,
        help="Show or hide the API token in the form."
    )

    @api.constrains('provider', 'name')
    def _check_gatewayapi_name_required(self):
        for rec in self:
            if rec.provider == 'sms_api_gatewayapi' and not rec.name:
                raise ValidationError(_("Name is required for GatewayAPI accounts."))

    # Obsolete _check_channel_name_required was removed

    def _process_notification_channel_settings(self):
        pass # Emptied as its functionality was removed

    gatewayapi_connection_status = fields.Char(
        string="Connection status",
        help="Status of the last connection test."
    )
    gatewayapi_cron_interval_number = fields.Integer(
        string="Credit check interval",
        default=1,
        help="How often to check the credit balance (number of intervals)."
    )
    gatewayapi_cron_interval_type = fields.Selection([
        ("minutes", "Minutes"),
        ("hours", "Hours"),
        ("days", "Days"),
        ("weeks", "Weeks"),
    ], string="Interval type", default="days", help="Unit for the credit check interval.")
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

    @api.depends('gatewayapi_base_url', 'gatewayapi_api_token', 'provider')
    def _compute_is_gatewayapi(self):
        for rec in self:
            rec.is_gatewayapi = (
                rec.provider == 'sms_api_gatewayapi' or
                (rec.gatewayapi_base_url and rec.gatewayapi_api_token)
            )

    @api.model
    def default_get(self, fields_list):
        """Set default show_token to False for new records."""
        res = super(IapAccount, self).default_get(fields_list)
        if 'show_token' in fields_list:
            res['show_token'] = False
        return res

    @api.model
    def get_gatewayapi_account(self):
        account = self.search([
            '|',
            ('provider', '=', 'sms_api_gatewayapi'),
            '&',
            ('service_name', '=', 'sms'),
            ('gatewayapi_base_url', '!=', False)
        ], limit=1)
        if not account:
            account = self.create({
                'name': 'GatewayAPI',
                'service_name': 'sms',
                'provider': 'sms_api_gatewayapi',
                'gatewayapi_base_url': 'https://gatewayapi.eu',
                'gatewayapi_sender': 'Odoo',
            })
            _logger.info("Created new GatewayAPI account with ID %s", account.id)
        return account

    @api.model
    def _get_sms_account(self):
        account = self.get("sms")
        if account.provider == 'sms_api_gatewayapi':
            return account
        if account.gatewayapi_base_url and account.gatewayapi_api_token:
            return account
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
        return account

    @api.model
    def check_gatewayapi_credit_balance(self):
        accounts_to_check = self.env['iap.account'].search([
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
            check_due = False
            if not last_check_time:
                check_due = True
            else:
                interval_delta = timedelta()
                if interval_type == 'minutes': interval_delta = timedelta(minutes=interval_number)
                elif interval_type == 'hours': interval_delta = timedelta(hours=interval_number)
                elif interval_type == 'days': interval_delta = timedelta(days=interval_number)
                elif interval_type == 'weeks': interval_delta = timedelta(weeks=interval_number)
                next_check_time = last_check_time + interval_delta
                if now >= next_check_time: check_due = True

            if check_due:
                _logger.info(f"Account {account.name}: Performing credit balance check.")
                try:
                    account.sudo().write({'gatewayapi_last_credit_check_time': now})
                    api_credits = account.get_current_credit_balance()
                except UserWarning as e:
                    _logger.warning(f"Account {account.name}: GatewayAPI error: {e}")
                except Exception as e:
                    _logger.warning(f"Account {account.name}: Exception getting balance: {e}")
                else:
                    _logger.info(f"Account {account.name}: Credit balance: {api_credits}")
                    if account.gatewayapi_min_tokens < 0:
                        _logger.info(f"Account {account.name}: Min tokens invalid. Skipping.")
                        continue
                    if not account.gatewayapi_token_notification_action:
                        _logger.info(f"Account {account.name}: No action set. Skipping.")
                        continue
                    if float(api_credits) < float(account.gatewayapi_min_tokens):
                        _logger.info(f"Account {account.name}: Low credit: {api_credits} < {account.gatewayapi_min_tokens}.")
                        ctx = {'active_id': account.id, 'active_model': 'iap.account'}
                        try:
                            account.gatewayapi_token_notification_action.with_context(ctx).run()
                            _logger.info(f"Account {account.name}: Notification action triggered.")
                        except Exception as e:
                            _logger.error(f"Account {account.name}: Failed to run action: {e}")
            else:
                _logger.info(f"Account {account.name}: Check not due.")

    def get_current_credit_balance(self, full_response=False):
        self.ensure_one()
        headers = {'Authorization': (f'Token {self.gatewayapi_api_token}')}
        base_url = self.gatewayapi_base_url or 'https://gatewayapi.eu'
        if not (base_url.startswith('http://') or base_url.startswith('https://')):
            raise UserWarning('GatewayAPI Base URL must start with http:// or https://')
        url = base_url.rstrip('/') + '/rest/me'
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_content = response.json()
        if full_response: return response_content
        if 'credit' in response_content: return response_content['credit']
        raise UserWarning(response_content.get('error', 'Unknown error'))

    def gatewayapi_connection_test(self):
        iap_account = self._get_sms_account()
        if iap_account.id != self.id or not self.gatewayapi_base_url:
            self.gatewayapi_connection_status = "Not a GatewayAPI configured account or no base URL."
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        try:
            full_info = iap_account.get_current_credit_balance(full_response=True)
            iap_account.gatewayapi_balance = float(full_info.get('credit', 0.0))
            iap_account.gatewayapi_currency = full_info.get('currency', '')
            iap_account.gatewayapi_connection_status = "OK"
            _logger.info("GatewayAPI connection test successful")
        except UserWarning as e:
            _logger.warning(f"GatewayAPI connection test error: {e}")
            iap_account.gatewayapi_connection_status = str(e)
            iap_account.gatewayapi_balance = 0.0
            iap_account.gatewayapi_currency = ''
        except Exception as e:
            _logger.exception("GatewayAPI connection test exception")
            iap_account.gatewayapi_connection_status = _("Unexpected error. Check server log.")
            iap_account.gatewayapi_balance = 0.0
            iap_account.gatewayapi_currency = ''
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            if 'show_token' not in vals_list: vals_list['show_token'] = False
            if vals_list.get('gatewayapi_check_min_tokens') and 'gatewayapi_last_credit_check_time' not in vals_list:
                vals_list['gatewayapi_last_credit_check_time'] = False
        elif isinstance(vals_list, list):
            for vals_item in vals_list:
                if 'show_token' not in vals_item: vals_item['show_token'] = False
                if vals_item.get('gatewayapi_check_min_tokens') and 'gatewayapi_last_credit_check_time' not in vals_item:
                    vals_item['gatewayapi_last_credit_check_time'] = False
        records = super(IapAccount, self).create(vals_list)
        notification_action = self.env.ref('gatewayapi_sms.low_credits_notification_action', raise_if_not_found=False)
        for record in records:
            if notification_action and record.is_gatewayapi:
                record.write({'gatewayapi_token_notification_action': notification_action.id})
        return records

    def write(self, vals):
        # This is the 'ultra-simplified' write method focusing on key logic for 'immediate check'.
        # The 'immediate check on interval change' logic that previously failed to apply is omitted here for now.
        # This was the version I could not apply due to diff issues.
        # For now, reverting to a simpler write that only handles the token_notification_action setting.
        
        # Original logic from your file for last_credit_check_time based on gatewayapi_check_min_tokens in vals:
        if vals.get('gatewayapi_check_min_tokens') is True and 'gatewayapi_last_credit_check_time' not in vals:
            vals['gatewayapi_last_credit_check_time'] = False
        elif vals.get('gatewayapi_check_min_tokens') is False and 'gatewayapi_last_credit_check_time' not in vals:
            vals['gatewayapi_last_credit_check_time'] = False
            # If disabling checks, also ensure the action is cleared
            if 'gatewayapi_token_notification_action' not in vals: # Don't override if explicitly set
                 vals['gatewayapi_token_notification_action'] = False

        res = super(IapAccount, self).write(vals)

        # Post-write logic to ensure server action is correctly set or cleared
        # This is important if gatewayapi_check_min_tokens was set by default or not in vals during the super call.
        if 'gatewayapi_check_min_tokens' in vals: # Only iterate if this was part of the write
            for record in self: # self has updated values
                if record.is_gatewayapi: # Only act on GatewayAPI accounts
                    if record.gatewayapi_check_min_tokens:
                        # If checks enabled, and action is not set (and not being explicitly cleared in this write)
                        if not record.gatewayapi_token_notification_action and (vals.get('gatewayapi_token_notification_action') is not False):
                            try:
                                action = self.env.ref('gatewayapi_sms.low_credits_notification_action', raise_if_not_found=False)
                                if action:
                                    record.write({'gatewayapi_token_notification_action': action.id})
                            except Exception as e:
                                _logger.error(f"Error setting notification action for {record.id}: {e}")
                    else: # gatewayapi_check_min_tokens is False for this record
                        if record.gatewayapi_token_notification_action is not False: # If action is set, clear it
                            record.write({'gatewayapi_token_notification_action': False})
        return res

    @api.depends('gatewayapi_api_token', 'gatewayapi_base_url')
    def _compute_gatewayapi_balance(self):
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
                    rec.gatewayapi_balance_display = f"{rec.gatewayapi_balance:.2f} {rec.gatewayapi_currency}"
                else:
                    rec.gatewayapi_balance_display = f"{rec.gatewayapi_balance:.2f}"
            else:
                rec.gatewayapi_balance_display = "0 Credits"

    def action_toggle_show_token(self):
        for rec in self:
            rec.show_token = not rec.show_token
# wba no reload as it messes up the view 
#        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(IapAccount, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return res

    def name_get(self):
        result = []
        for rec in self:
            if rec.gatewayapi_base_url and rec.provider == 'sms_api_gatewayapi':
                if rec.name:
                    result.append((rec.id, rec.name))
                else:
                    base_url = rec.gatewayapi_base_url or 'https://gatewayapi.eu'
                    name = f"GatewayAPI {base_url}"
                    result.append((rec.id, name))
            else:
                super_name_get = super(IapAccount, rec).name_get()
                if super_name_get and super_name_get[0]:
                    result.append(super_name_get[0])
                else:
                    result.append((rec.id, _('IAP Account %s') % rec.id))
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

        admin_user = self.env.ref('base.user_admin', raise_if_not_found=False) or self.env['res.users']
        user_id_to_assign = admin_user.id if admin_user and admin_user != self.env['res.users'] else self.env.uid

        activity = self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'note': message_body_html,
            'res_id': self.id,
            'res_model_id': self.env.ref('iap.model_iap_account').id,
            'user_id': user_id_to_assign,
            'summary': _('GatewayAPI low on credits for %s') % (self.name or 'Unnamed GatewayAPI Account'),
        })

        self.message_post(body=message_body_html, subject=message_subject)

        if self.gatewayapi_enable_email_notification and self.gatewayapi_low_credit_notification_email:
            _logger.info(f"Attempting to send low credits email alert for account '{self.name}' to '{self.gatewayapi_low_credit_notification_email}'")
            email_from = self.env.user.company_id.email_formatted or self.env.user.email_formatted or \
                         self.env['ir.mail_server'].sudo().search([], limit=1).smtp_user
            if not email_from:
                _logger.warning(f"Cannot determine 'email_from' for low credit notification for account {self.name}.")

            mail_values = {
                'subject': message_subject,
                'body_html': message_body_html,
                'email_to': self.gatewayapi_low_credit_notification_email,
                'email_from': email_from,
                'model': self._name,
                'res_id': self.id,
                'auto_delete': True,
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            try:
                mail.send()
                _logger.info(f"Low credits email for account '{self.name}' sent successfully to '{self.gatewayapi_low_credit_notification_email}'. Mail ID: {mail.id}")
            except Exception as e:
                _logger.error(f"Failed to send low credits email for account '{self.name}' to '{self.gatewayapi_low_credit_notification_email}': {e}")
        return activity
