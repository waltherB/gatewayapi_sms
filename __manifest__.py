# -*- coding: utf-8 -*-
{
    'name': "PlaySMS Connector",
    'summary': "Send SMS with PlaySMS",
    'author': "Walther Barnett",
    'website': "https://github.com/waltherB/sms-playsms-http/playsms-connector",
    'license': 'AGPL-3',
    'category': 'Technical',
    'version': '17.0.1.0.0',
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
    'images': ['static/description/banner.png'],
}
