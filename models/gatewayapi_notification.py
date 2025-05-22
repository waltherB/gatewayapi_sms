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

    def get_or_create_channel(self):
        """Get or create a notification channel for low credit alerts."""
        self.ensure_one()

        if self.channel_id:
            return self.channel_id

        channel_name = f"GatewayAPI SMS Notifications - {self.account_id.name or 'Default'}"
        
        # Ensure partner_ids has a default value if needed by mail.channel creation.
        # Usually, admin is added or specific users.
        admin_user = self.env.ref('base.user_admin', raise_if_not_found=False)
        if not admin_user:
            _logger.warning("Admin user not found, cannot automatically add to new notification channel.")
            partner_ids = []
        else:
            partner_ids = [(4, admin_user.partner_id.id)] # Add admin partner to the channel

        channel_vals = {
            'name': channel_name,
            'channel_type': 'channel',  # Use 'chat' for private, 'channel' for public/group
            'description': f"Channel for GatewayAPI SMS credit alerts for account {self.account_id.name or 'Default'}",
            'group_public_id': None,  # Set to None for a private channel, or link to a group for restricted access
            'channel_partner_ids': partner_ids, # Add initial members during creation
        }

        channel = self.env['mail.channel'].create(channel_vals)
        _logger.info(f"Created new mail.channel '{channel.name}' (ID: {channel.id}) for GatewayAPI notifications.")

        # Assign the newly created channel to the current notification record
        self.channel_id = channel.id
        return channel

