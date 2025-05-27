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

    # Add a helper field to check if notification channel field exists
    field_exists = fields.Boolean(
        string="Field Exists",
        compute="_compute_field_exists",
        store=False,
        help="Technical field to check if notification channel field exists"
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
        help="Minimum credit level for alerting purposes. Only used if 'Check for minimum credits' is enabled."
    )

    # Rather than a direct reference, use a computed field
    notification_id = fields.One2many(
        'gatewayapi.notification',
        'account_id',
        string="Notification Settings"
    )

    gatewayapi_channel_config_mode = fields.Selection([
        ('none', 'No Channel Notifications'),
        ('existing', 'Use Existing Channel'),
        ('create', 'Create New Channel'),
    ], string="Notification Channel Mode", default='create', copy=False)

    gatewayapi_existing_channel_id = fields.Many2one(
        'mail.channel', string="Existing Notification Channel",
        help="Select an existing channel for notifications.", copy=False, ondelete='set null'
    )

    gatewayapi_new_channel_name = fields.Char(
        string="New Channel Name", copy=False,
        help="Name for the new channel to be created for notifications. Default: 'GatewayAPI: {Account Name} Notifications'"
    )

    gatewayapi_subscribe_current_user = fields.Boolean(
        string="Subscribe Me to Channel", default=True, copy=False,
        help="Check this to automatically subscribe yourself to the notification channel."
    )

    gatewayapi_additional_subscribers_user_ids = fields.Many2many(
        'res.users', 'iap_account_notification_res_users_rel',
        'iap_account_id', 'user_id', string="Additional Users for Channel", copy=False,
        help="Select other users to subscribe to the notification channel."
    )

    gatewayapi_effective_notification_channel_id = fields.Many2one(
        'mail.channel', string="Effective Notification Channel",
        compute="_compute_effective_notification_channel", store=True, readonly=True,
        help="The channel currently used for notifications for this account."
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

    # Changed: store=False removed to make it store=True by default
    show_token = fields.Boolean(
        default=False,
        help="Show or hide the API token in the form."
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

    # Changed: Restored to robust version
    @api.depends('notification_id', 'notification_id.channel_id')
    def _compute_effective_notification_channel(self):
        for rec in self:
            effective_channel = None
            if rec.notification_id:
                for notif_setting in rec.notification_id:
                    if notif_setting.channel_id and isinstance(notif_setting.channel_id, models.BaseModel) and notif_setting.channel_id._name == 'mail.channel':
                        effective_channel = notif_setting.channel_id
                        break # Found a suitable channel
            rec.gatewayapi_effective_notification_channel_id = effective_channel

    @api.onchange('name', 'gatewayapi_channel_config_mode')
    def _onchange_iap_account_name_for_channel(self):
        if self.gatewayapi_channel_config_mode == 'create' and self.name and not self.gatewayapi_new_channel_name:
            self.gatewayapi_new_channel_name = f"GatewayAPI: {self.name} Notifications"

    def _create_gatewayapi_new_channel(self, channel_name):
        # self here is a single iap.account record
        if not channel_name:
            channel_name = f"GatewayAPI: {self.name or 'Unnamed Account'} Notifications"
        
        channel_vals = {
            'name': channel_name,
            'channel_type': 'channel',
            'description': f"Notifications for GatewayAPI Account: {self.name}",
            'group_public_id': None,
        }
        new_channel = self.env['mail.channel'].create(channel_vals)
        _logger.info(f"Created new mail.channel '{new_channel.name}' (ID: {new_channel.id}) for IAP account {self.name}")
        return new_channel

    def _process_notification_channel_settings(self):
        for record in self:
            notif_config_record = self.env['gatewayapi.notification'].search([('account_id', '=', record.id)], limit=1)
            if not notif_config_record:
                notif_config_record = self.env['gatewayapi.notification'].create({'account_id': record.id})

            target_channel = False
            if record.gatewayapi_channel_config_mode == 'existing':
                target_channel = record.gatewayapi_existing_channel_id
            elif record.gatewayapi_channel_config_mode == 'create':
                channel_name_to_create = record.gatewayapi_new_channel_name
                if not channel_name_to_create and record.name: # Default if empty
                    channel_name_to_create = f"GatewayAPI: {record.name} Notifications"
                elif not channel_name_to_create: # Fallback if name is also empty
                    channel_name_to_create = "GatewayAPI: Unnamed Account Notifications"
                
                target_channel = record._create_gatewayapi_new_channel(channel_name_to_create)

            notif_config_record.sudo().write({'channel_id': target_channel.id if target_channel else False})

            user_ids_to_subscribe = []
            if record.gatewayapi_subscribe_current_user:
                user_ids_to_subscribe.append(self.env.uid)
            
            if record.gatewayapi_additional_subscribers_user_ids:
                user_ids_to_subscribe.extend(record.gatewayapi_additional_subscribers_user_ids.ids)

            if target_channel and user_ids_to_subscribe:
                unique_user_ids = list(set(user_ids_to_subscribe))
                try:
                    target_channel.sudo().add_members(unique_user_ids)
                    _logger.info(f"Subscribed users {unique_user_ids} to channel {target_channel.name} for account {record.name}")
                except Exception as e:
                    _logger.error(f"Failed to subscribe users to channel {target_channel.name} for account {record.name}: {e}")
            elif target_channel and not user_ids_to_subscribe:
                 _logger.info(f"No users selected for subscription to channel {target_channel.name} for account {record.name}")


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
        account = self.get("sms") # In core, self.get calls the method above for 'iap.account'

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

        return account # Fallback

    @api.model
    def check_gatewayapi_credit_balance(self):
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
            check_due = False
            if not last_check_time:
                check_due = True
                _logger.info(f"Account {account.name}: Last check time not set, check is due.")
            else:
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
                    account.sudo().write({'gatewayapi_last_credit_check_time': now})
                    api_credits = account.get_current_credit_balance()
                except UserWarning as e:
                    _logger.warning(f"Account {account.name}: GatewayAPI returned an error: {e}")
                except Exception as e:
                    _logger.warning(f"Account {account.name}: An exception occurred: {e}")
                else:
                    _logger.info(f"Account {account.name}: Successfully retrieved credit balance: {api_credits}")
                    if account.gatewayapi_min_tokens < 0:
                        _logger.info(f"Account {account.name}: Minimum credits not set. Skipping notification.")
                        continue
                    if not account.gatewayapi_token_notification_action:
                        _logger.info(f"Account {account.name}: Notification action not set. Skipping notification.")
                        continue
                    if float(api_credits) < float(account.gatewayapi_min_tokens):
                        _logger.info(f"Account {account.name}: Low credit balance! Current: {api_credits}, Min: {account.gatewayapi_min_tokens}.")
                        ctx = dict(self.env.context or {})
                        ctx.update({'active_id': account.id, 'active_model': 'iap.account'})
                        try:
                            account.gatewayapi_token_notification_action.with_context(ctx).run()
                            _logger.info(f"Account {account.name}: Low credit notification action triggered.")
                        except Exception as e:
                            _logger.error(f"Account {account.name}: Failed to run low credit notification action: {e}")
                    else:
                        _logger.info(f"Account {account.name}: Credit balance ({api_credits}) sufficient.")
            else:
                _logger.info(f"Account {account.name}: Skipping credit balance check, not due.")

    def get_current_credit_balance(self, full_response=False):
        self.ensure_one()
        headers = {'Authorization': (f'Token {self.gatewayapi_api_token}')}
        base_url = self.gatewayapi_base_url
        if not base_url or str(base_url).lower() == 'false':
            base_url = 'https://gatewayapi.eu'
        if not (base_url.startswith('http://') or base_url.startswith('https://')):
            raise UserWarning('GatewayAPI Base URL must start with http:// or https://')
        url = base_url.rstrip('/') + '/rest/me'
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_content = response.json()
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
            _logger.warning("GatewayAPI connection test only on accounts with GatewayAPI config.")
            # To prevent issues if called on non-GatewayAPI or unconfigured account
            # We can set a default status or simply return without action
            self.gatewayapi_connection_status = "Not a GatewayAPI configured account or no base URL."
            return {'type': 'ir.actions.client', 'tag': 'reload'}

        try:
            iap_account.get_current_credit_balance()
        except UserWarning as e:
            _logger.warning(f"GatewayAPI connection test error: {e}")
            iap_account.gatewayapi_connection_status = str(e)
            iap_account.gatewayapi_balance = 0.0
        except Exception as e:
            _logger.exception("GatewayAPI connection test exception")
            iap_account.gatewayapi_connection_status = _("Unexpected error. Check server log.")
            iap_account.gatewayapi_balance = 0.0
        else:
            _logger.info("GatewayAPI connection test successful")
            iap_account.gatewayapi_connection_status = "OK"
            try:
                # Fetch full response to get currency as well if needed by balance display
                full_info = iap_account.get_current_credit_balance(full_response=True)
                iap_account.gatewayapi_balance = float(full_info.get('credit', 0.0))
                iap_account.gatewayapi_currency = full_info.get('currency', '') # Ensure currency is also updated
            except Exception:
                _logger.exception("Failed to update GatewayAPI balance after successful test")
                iap_account.gatewayapi_balance = 0.0
                iap_account.gatewayapi_currency = ''
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.model
    def create(self, vals_list):
        # Ensure show_token is False for new records, as it's now store=True
        # The default_get handles this if 'show_token' is in fields_list, but good to be sure.
        if isinstance(vals_list, dict):
            if 'show_token' not in vals_list:
                vals_list['show_token'] = False
            if vals_list.get('gatewayapi_check_min_tokens') and 'gatewayapi_last_credit_check_time' not in vals_list:
                vals_list['gatewayapi_last_credit_check_time'] = False
        elif isinstance(vals_list, list):
            for vals_item in vals_list:
                if 'show_token' not in vals_item:
                    vals_item['show_token'] = False
                if vals_item.get('gatewayapi_check_min_tokens') and 'gatewayapi_last_credit_check_time' not in vals_item:
                    vals_item['gatewayapi_last_credit_check_time'] = False
        
        records = super(IapAccount, self).create(vals_list)
        
        notification_action = self.env.ref('gatewayapi_sms.low_credits_notification_action', raise_if_not_found=False)
        for record in records:
            if notification_action and record.is_gatewayapi:
                record.write({'gatewayapi_token_notification_action': notification_action.id})
            if record.gatewayapi_check_min_tokens and not record.gatewayapi_last_credit_check_time:
                original_vals = vals_list if isinstance(vals_list, dict) else (vals_list[0] if isinstance(vals_list, list) and vals_list else {})
                if not original_vals.get('gatewayapi_last_credit_check_time') is False:
                     record.write({'gatewayapi_last_credit_check_time': False})
            record._process_notification_channel_settings()
        return records

    def write(self, vals):
        # If show_token is explicitly being set by its own toggle action, allow it.
        # Otherwise, if not present in vals, and not called by toggle, ensure it's reset if needed.
        # However, with store=True, its value persists. Default_get handles new records.
        # fields_view_get can reset it for existing records if that's desired UI behavior.
        # For now, if show_token is False, we don't want it to become True unless toggled.
        # This logic might need refinement based on desired UI persistence of show_token.
        if 'show_token' not in vals and not self.env.context.get('caller', '') == 'toggle_token':
            # This part is tricky with store=True. If user saves form, show_token state will save.
            # If intention is to always hide on save unless toggled, more logic needed here or in fields_view_get.
            # For now, let's assume if it's not in vals, its current DB state is fine.
            pass

        if vals.get('gatewayapi_check_min_tokens') is True and 'gatewayapi_last_credit_check_time' not in vals:
            vals['gatewayapi_last_credit_check_time'] = False
        elif vals.get('gatewayapi_check_min_tokens') is False and 'gatewayapi_last_credit_check_time' not in vals:
            vals['gatewayapi_last_credit_check_time'] = False

        res = super(IapAccount, self).write(vals)

        if 'gatewayapi_check_min_tokens' in vals:
            for record in self:
                if record.gatewayapi_check_min_tokens:
                    if not record.gatewayapi_token_notification_action:
                        try:
                            notification_action = self.env.ref('gatewayapi_sms.low_credits_notification_action')
                            record.gatewayapi_token_notification_action = notification_action.id
                        except Exception as e:
                            _logger.error(f"Failed to set notification action for account {record.id}: {e}")
        
        channel_config_fields = [
            'gatewayapi_channel_config_mode',
            'gatewayapi_existing_channel_id',
            'gatewayapi_new_channel_name',
            'gatewayapi_subscribe_current_user',
            'gatewayapi_additional_subscribers_user_ids'
        ]
        if any(field_name in vals for field_name in channel_config_fields) or 'name' in vals:
            for record in self:
                record._process_notification_channel_settings()
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
        """Toggle visibility of the API token"""
        for rec in self:
            rec.show_token = not rec.show_token
        # Add a context flag to indicate this action was called
        return {'type': 'ir.actions.client', 'tag': 'reload', 'context': {'caller': 'toggle_token'}}

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """Override to ensure token is hidden when reopening the form view if not toggled by user"""
        # For store=True fields, default_get sets it for new records.
        # For existing records, if we want to reset show_token each time a form view is opened,
        # this is one place, but it can be complex if user's explicit toggle should be remembered across views.
        # The core iap.account doesn't seem to aggressively reset show_token on existing records in fields_view_get.
        # It relies on the value stored in the DB.
        # If show_token's value should not persist across saves or view opens for existing records,
        # then store=False was more appropriate, but that led to other issues.
        # Given it's store=True now, its persisted value will be used.
        # The original user file had a simple super() call here.
        res = super(IapAccount, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return res

    # Changed: Restored to original version (only handling show_token)
    @api.model
    def default_get(self, fields_list):
        """Reset show_token to False on new records"""
        res = super(IapAccount, self).default_get(fields_list)
        if 'show_token' in fields_list:
            res['show_token'] = False
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
                # Fallback to super if not specifically a gatewayapi configured entry
                # or if name_get() from inherited 'iap.account' is desired.
                # Original user file had: result.append((rec.id, super(IapAccount, rec).name_get()[0][1]))
                # This can be risky if super().name_get() returns empty or different structure.
                # A safer default if no name: 
                super_name_get = super(IapAccount, rec).name_get()
                if super_name_get and super_name_get[0]:
                    result.append(super_name_get[0])
                else:
                    result.append((rec.id, _('IAP Account %s') % rec.id)) # Fallback name
        return result

    def send_low_credits_notification(self):
        self.ensure_one()
        message = _("""
<p><b>⚠️ Low SMS Credits Alert</b></p>
<p>The SMS credits for <b>%s</b> are running low:</p>
<ul>
    <li>Current balance: <b>%s</b></li>
    <li>Minimum threshold: <b>%s</b></li>
</ul>
<p>Please add more credits to ensure uninterrupted SMS services.</p>
""") % (
            self.name or 'GatewayAPI account',
            self.gatewayapi_balance_display,
            f"{self.gatewayapi_min_tokens} {self.gatewayapi_currency}" if self.gatewayapi_currency else self.gatewayapi_min_tokens
        )
        admin_user = self.env.ref('base.user_admin', raise_if_not_found=False) or self.env['res.users']
        activity = self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'note': message,
            'res_id': self.id,
            'res_model_id': self.env.ref('iap.model_iap_account').id,
            'user_id': admin_user.id if admin_user else self.env.uid, # Fallback to current user if admin not found
            'summary': _('GatewayAPI low on credits'),
        })
        self.message_post(body=message, subject=_('GatewayAPI low on credits'))
        if self.gatewayapi_check_min_tokens:
            channel = False
            if self.notification_id:
                notif_setting = self.notification_id[0]
                channel = notif_setting.get_channel_for_notifications()
            
            if channel:
                _logger.info(f"Sending low credits notification to channel '{channel.name}' for account '{self.name}'")
                channel.message_post(
                    body=message, 
                    subject=_('GatewayAPI Low Credits Alert: %s', self.name),
                    subtype_xmlid='mail.mt_comment',
                    author_id=self.env.user.partner_id.id
                )
            else:
                _logger.info(f"No effective notification channel found for account '{self.name}' to send low credits alert.")
        return activity

    @api.depends('notification_id.channel_id')
    def _compute_field_exists(self):
        for rec in self:
            rec.field_exists = bool(rec.notification_id and rec.notification_id[0].channel_id)

