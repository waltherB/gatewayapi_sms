# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

import logging
import requests

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class IapAccount(models.Model):
    _name = "iap.account"
    _inherit = ['iap.account', 'mail.thread', 'mail.activity.mixin']

    provider = fields.Selection(
        selection_add=[("sms_api_gatewayapi", "GatewayAPI")],
        ondelete={"sms_api_gatewayapi": "cascade"},
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
    show_token = fields.Boolean(default=False, help="Show or hide the API token in the form.")

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

    def get_current_credit_balance(self):
        iap_account_sms = self.env['iap.account']._get_sms_account()
        headers = {
            'Authorization': (
                f'Token {iap_account_sms.gatewayapi_api_token}'
            )
        }
        base_url = iap_account_sms.gatewayapi_base_url
        if not base_url or base_url == 'False':
            base_url = 'https://gatewayapi.eu'
        url = base_url.rstrip('/') + '/rest/me'
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_content = response.json()
        _logger.debug(
            f"GatewayAPI credit balance check responded with: "
            f"{response_content}"
        )
        if 'credit' in response_content:
            return response_content['credit']
        else:
            error_msg = response_content.get('error', 'Unknown error')
            raise UserWarning(error_msg)

    @api.model
    def _get_sms_account(self):
        return self.get("sms")

    def gatewayapi_connection_test(self):
        """Test connection by checking current credit balance and writing a status message to gatewayapi_connection_status"""
        iap_account = self._get_sms_account()
        if iap_account.id != self.id or self.provider != "sms_api_gatewayapi":
            _logger.warning(
                "GatewayAPI connection test is only performed on SMS account "
                "where GatewayAPI is set as provider."
            )
        try:
            # Only test connection, do not use api_credits
            iap_account.get_current_credit_balance()
        except UserWarning as e:
            _logger.warning(
                f"GatewayAPI returned an error while attempting to get current "
                f"credit balance: {e}"
            )
            iap_account.gatewayapi_connection_status = str(e)
        except Exception as e:
            _logger.warning(
                f"An exception occurred while attempting to get current credit "
                f"balance: {e}"
            )
            iap_account.gatewayapi_connection_status = _(
                u"Unexpected error. Check server log for more info."
            )
        else:
            _logger.info("GatewayAPI connection test successful")
            iap_account.gatewayapi_connection_status = "OK"
            # Explicitly update the balance
            try:
                iap_account.gatewayapi_balance = float(iap_account.get_current_credit_balance())
            except Exception:
                iap_account.gatewayapi_balance = 0.0
        # Force form reload
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
    def create(self, vals):
        rec = super().create(vals)
        rec._update_gatewayapi_cron()
        return rec

    def write(self, vals):
        res = super().write(vals)
        self._update_gatewayapi_cron()
        return res

    @api.depends('gatewayapi_api_token', 'gatewayapi_base_url')
    def _compute_gatewayapi_balance(self):
        for rec in self:
            if rec.provider == 'sms_api_gatewayapi' and rec.gatewayapi_api_token:
                try:
                    rec.gatewayapi_balance = float(rec.get_current_credit_balance())
                except Exception:
                    rec.gatewayapi_balance = 0.0
            else:
                rec.gatewayapi_balance = 0.0

    def action_toggle_show_token(self):
        for rec in self:
            rec.show_token = not rec.show_token
