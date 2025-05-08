# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

import logging
import requests

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class IapAccount(models.Model):
    _name = "iap.account"
    _inherit = ['iap.account', 'mail.thread', 'mail.activity.mixin']

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
    gatewayapi_token_notification_action = fields.Many2one(
        'ir.actions.server',
        string="Credits notification action",
        help="Action to be performed when the number of credits is less than "
             "min_tokens."
    )
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
    show_token = fields.Boolean(default=False, help="Show or hide the API token in the form.")

    @api.depends('gatewayapi_base_url', 'gatewayapi_api_token', 'provider')
    def _compute_is_gatewayapi(self):
        """Compute whether this account is configured for GatewayAPI"""
        for rec in self:
            rec.is_gatewayapi = (rec.provider == 'sms_api_gatewayapi' or 
                              (rec.gatewayapi_base_url and rec.gatewayapi_api_token))

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
            _logger.info("Created new GatewayAPI account with ID %s", account.id)
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
        """If current credits are lower than gatewayapi_min_tokens, execute action"""
        iap_account = self._get_sms_account()
        if iap_account.gatewayapi_min_tokens < 0:
            _logger.info(
                "GatewayAPI minimum credits not set. "
                "Skipping balance check."
            )
            return
        if not iap_account.gatewayapi_token_notification_action:
            _logger.info(
                "GatewayAPI notification action not set. "
                "Skipping balance check."
            )
            return
        try:
            api_credits = iap_account.get_current_credit_balance()
        except UserWarning as e:
            _logger.warning(
                f"GatewayAPI returned an error while attempting to get "
                f"current credit balance: {e}"
            )
        except Exception as e:
            _logger.warning(
                f"An exception occurred while attempting to get current "
                f"credit balance: {e}"
            )
        else:
            if float(api_credits) < float(iap_account.gatewayapi_min_tokens):
                _logger.info(
                    f"You only have {api_credits} GatewayAPI credits left."
                )
                ctx = dict(self.env.context or {})
                ctx.update({
                    'active_id': iap_account.id,
                    'active_model': 'iap.account'
                })
                iap_account.gatewayapi_token_notification_action.with_context(
                    ctx
                ).run()
            else:
                _logger.info(
                    f"You have {api_credits} GatewayAPI credits, which is more "
                    f"than your set minimum of "
                    f"{iap_account.gatewayapi_min_tokens} credits"
                )

    def get_current_credit_balance(self, full_response=False):
        iap_account_sms = self.env['iap.account']._get_sms_account()
        headers = {
            'Authorization': (
                f'Token {iap_account_sms.gatewayapi_api_token}'
            )
        }
        base_url = iap_account_sms.gatewayapi_base_url
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

    def _update_gatewayapi_cron(self):
        cron = self.env.ref('gatewayapi_sms.ir_cron_check_tokens', raise_if_not_found=False)
        if cron:
            cron.write({
                'interval_number': self.gatewayapi_cron_interval_number or 1,
                'interval_type': self.gatewayapi_cron_interval_type or 'days',
            })

    @api.model
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_gatewayapi_cron()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._update_gatewayapi_cron()
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
        """Send a notification about low credits"""
        self.ensure_one()
        
        # Prepare message
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
        
        # Create activity
        admin_user = self.env.ref('base.user_admin')
        activity = self.env['mail.activity'].create({
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'note': message,
            'res_id': self.id,
            'res_model_id': self.env.ref('iap.model_iap_account').id,
            'user_id': admin_user.id,
            'summary': _('GatewayAPI low on credits'),
        })
        
        # Also log a message in the chatter
        self.message_post(body=message, subject=_('GatewayAPI low on credits'))
        
        return activity
