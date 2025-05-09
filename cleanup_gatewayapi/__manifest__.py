# -*- coding: utf-8 -*-
{
    'name': 'Cleanup GatewayAPI',
    'version': '1.0',
    'summary': 'Cleanup module for GatewayAPI SMS',
    'description': """
        This module cleans up database entries after uninstalling GatewayAPI SMS module.
        It removes references to fields that no longer exist.
    """,
    'category': 'Technical',
    'author': 'Your Company',
    'depends': ['iap'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
} 