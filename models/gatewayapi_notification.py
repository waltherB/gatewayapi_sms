# -*- coding: utf-8 -*-

from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class GatewayapiNotification(models.Model):
    _name = "gatewayapi.notification"
    _description = "GatewayAPI Notification Settings"
    # IMPORTANT: Removed 'mail.channel' from _inherit.
    # This model is intended to *have* a mail.channel (Many2one), not *be* a mail.channel.
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # It's good practice to ensure there's a unique constraint if account_id
    # is meant to be unique per notification setting.
    _sql_constraints = [
        ('account_id_uniq', 'unique (account_id)', 'An IAP account can only have one GatewayAPI notification setting.')
    ]

    name = fields.Char(
        related="account_id.name",
        readonly=True,
        store=True  # Add store=True if you want to search/group by this related field effectively
    )
    account_id = fields.Many2one(
        'iap.account',
        string="IAP Account",
        required=True,
        ondelete='cascade',
        # Consider adding a domain if applicable, e.g., to filter IAP accounts
        # domain="[('service_name', '=', 'gatewayapi_sms')]" # Example
    )

    # This field correctly defines the Many2one relationship to mail.channel
    channel_id = fields.Many2one(
        'mail.channel',
        string="Notification Channel",
        help="Discussion channel to post low credit notifications to. "
             "Leave empty to create a new channel automatically.",
        copy=False
    )

    def get_channel_for_notifications(self): # Renamed
        self.ensure_one()
        if self.channel_id:
            return self.channel_id
        # _logger.info(f"No notification channel is configured for IAP account {self.account_id.name} (via gatewayapi.notification record).") # Optional logging
        return False

