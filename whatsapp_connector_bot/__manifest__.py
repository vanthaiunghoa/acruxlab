# -*- coding: utf-8 -*-
# =====================================================================================
# License: OPL-1 (Odoo Proprietary License v1.0)
#
# By using or downloading this module, you agree not to make modifications that
# affect sending messages through Acruxlab or avoiding contract a Plan with Acruxlab.
# Support our work and allow us to keep improving this module and the service!
#
# Al utilizar o descargar este módulo, usted se compromete a no realizar modificaciones que
# afecten el envío de mensajes a través de Acruxlab o a evitar contratar un Plan con Acruxlab.
# Apoya nuestro trabajo y permite que sigamos mejorando este módulo y el servicio!
# =====================================================================================
{
    'name': 'ChatRoom Real ChatBot professional. Whatsapp - Instagram DM - FaceBook Messenger.',
    'summary': 'Chat Bot. Automatic messages for product and text. Templates and Python code. WhatsApp ChatBot integration. ChatBot WhatsApp bot apichat.io GupShup Chat-Api ChatApi. ChatRoom 2.0.',
    'description': 'BOT WhatsApp Automatic messages for product and free text. Templates and Python code. WhatsApp ChatBot integration. ChatBot WhatsApp bot ChatRoom 2.0.',
    'version': '15.0.16',
    'author': 'AcruxLab',
    'live_test_url': 'https://acruxlab.com/plans',
    'support': 'info@acruxlab.com',
    'price': 149.0,
    'currency': 'USD',
    'images': ['static/description/Banner_bot_v10.gif'],
    'website': 'https://acruxlab.com/whatsapp',
    'license': 'OPL-1',
    'application': True,
    'installable': True,
    'category': 'Discuss',
    'depends': [
        'whatsapp_connector',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'wizard/product_import.xml',
        'views/bot_log_views.xml',
        'views/bot_views.xml',
        'views/connector_views.xml',
        'views/menu.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/whatsapp_connector_bot/static/src/css/chat_bot.css',
        ],
    },
    'post_load': '',
    'external_dependencies': {},
    'pre_init_hook': '',
}
