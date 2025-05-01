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
        help="GatewayAPI API Token",
        password=True
    )
    gatewayapi_min_tokens = fields.Integer(
        string="Minimum credits",
        help="Minimum credit level for alerting purposes. "
             "If it is a negative number, e.g. -1, the alarming is disabled."
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
        base_url = iap_account_sms.gatewayapi_base_url or 'https://gatewayapi.eu'
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
