# -*- coding: utf-8 -*-

from odoo import fields, models, api, _, SUPERUSER_ID

# fix ?
_depends = {'mail.thread': []}


import logging

_logger = logging.getLogger(__name__)


class GatewayapiNotification(models.Model):
    _name = "gatewayapi.notification"
    _description = "GatewayAPI Notification Settings"
    _depends = _depends
    
    name = fields.Char(
        related="account_id.name",
        readonly=True
    )
    account_id = fields.Many2one(
        'iap.account',
        string="IAP Account",
        required=True,
        ondelete='cascade'
    )
    channel_id = fields.Many2one(
        'mail.channel',
        string="Notification Channel",
        help="Discussion channel to post low credit notifications to. "
             "Leave empty to create a new channel automatically.",
    )
    
    def get_or_create_channel(self):
        """Get or create a notification channel for low credit alerts"""
        self.ensure_one()
        
        # Use existing channel if set
        if self.channel_id:
            return self.channel_id
            
        # Create a new channel for notifications
        channel_name = f"GatewayAPI SMS Notifications - {self.account_id.name}"
        channel = self.env['mail.channel'].create({
            'name': channel_name,
            'channel_type': 'channel',
            'description': f"Channel for GatewayAPI SMS credit alerts for account {self.account_id.name}",
        })
        
        # Add admin user to the channel
        admin_user = self.env.ref('base.user_admin')
        channel.channel_member_ids = [(0, 0, {
            'partner_id': admin_user.partner_id.id,
        })]
        
        # Save the channel
        self.channel_id = channel.id
        
        return channel 
