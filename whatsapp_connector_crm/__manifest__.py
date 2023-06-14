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
    'name': 'ChatRoom CRM extra. Leads. Real All in One',
    'summary': 'From ChatRoom main view Create & Send CRM Leads. Send message from CRM Lead. All in one screen. apichat.io GupShup Chat-Api ChatApi. Whatsapp, Instagram DM, FaceBook Messenger. ChatRoom 2.0.',
    'description': 'Create Leads from ChatRoom. Send message from CRM Lead. WhatsApp integration. WhatsApp Connector. apichat.io. GupShup. Chat-Api. ChatApi. ChatRoom 2.0.',
    'version': '15.0.6',
    'author': 'AcruxLab',
    'live_test_url': 'https://chatroom.acruxlab.com/web/signup',
    'support': 'info@acruxlab.com',
    'price': 59.0,
    'currency': 'USD',
    'images': ['static/description/Banner_crm_v10.gif'],
    'website': 'https://acruxlab.com/plans',
    'license': 'OPL-1',
    'application': True,
    'installable': True,
    'category': 'Discuss/Sales/CRM',
    'depends': [
        'whatsapp_connector',
        'crm',
    ],
    'data': [
        'views/crm_lead_views.xml',
        'views/acrux_chat_conversation_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # widgets
            '/whatsapp_connector_crm/static/src/js/acrux_*.js',
        ],
        'web.assets_qweb': [
            'whatsapp_connector_crm/static/src/xml/*',
        ],
    },
}
