# -*- coding: utf-8 -*-
{
    'name': "GatewayAPI SMS Connector",
    'summary': "Send SMS with GatewayAPI",
    'author': "Walther Barnett",
    'website': "https://github.com/waltherB/gatewayapi_sms",
    'license': 'AGPL-3',
    'category': 'Technical',
    'version': '17.0.2.0.1',
    'icon': 'static/description/icon.png',
    'depends': ['base', "sms", "iap_alternative_provider", "phone_validation"],
    'external_dependencies': {
        'python': ['phonenumbers', 'requests']
    },
    'data': [
        'data/iap_account_data.xml',
        'data/ir_cron.xml',
        'views/iap_account.xml',
        'views/sms_sms.xml',
        'views/sms_resend.xml'
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
        'static/description/screenshot_01_config.png',
        'static/description/screenshot_02_test_connection.png',
        'static/description/screenshot_03_notification.png',
        'static/description/screenshot_04_balance.png',
    ],
    'description': '''
GatewayAPI SMS Connector for Odoo 17
------------------------------------
Send SMS via GatewayAPI directly from Odoo. Features include:
- Secure API Token management with show/hide toggle
- Credit balance monitoring and notifications
- Easy configuration and integration
- Scheduled credit checks and admin alerts
''',
    'post_init_hook': 'post_init_hook',
}
