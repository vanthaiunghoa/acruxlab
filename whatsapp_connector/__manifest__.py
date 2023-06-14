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
    'name': 'ChatRoom BASE Whatsapp - Messenger - Instagram. Live Chat. Real All in One',
    'summary': 'From ChatRoom main view Search & Send Product. Send message from many places with Templates (Sale, Invoice, Purchase, CRM Leads, Product, Stock Picking, Partner). All in one screen. apichat.io GupShup Chat-Api ChatApi. Whatsapp, Instagram DM, FaceBook Messenger. ChatRoom 2.0.',
    'description': 'Send Product, Real All in One. Send and receive messages. Real ChatRoom. WhatsApp integration. WhatsApp Connector. apichat.io. GupShup. Chat-Api. ChatApi. Drag and Drop. ChatRoom 2.0.',
    'version': '15.0.29',
    'author': 'AcruxLab',
    'live_test_url': 'https://chatroom.acruxlab.com/web/signup',
    'support': 'info@acruxlab.com',
    'price': 75.0,
    'currency': 'USD',
    'images': ['static/description/Banner_base_v11.gif'],
    'website': 'https://acruxlab.com/plans',
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
    'category': 'Discuss/Sales/CRM',
    'depends': [
        'bus',
        'sales_team',
        'product'
    ],
    'data': [
        'data/data.xml',
        'data/cron.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/CustomMessage.xml',
        'wizard/init_free_test.xml',
        'wizard/MessageWizard.xml',
        'wizard/ScanQr.xml',
        'wizard/SimpleNewConversation.xml',
        'views/ir_attachment.xml',
        'views/default_answer_views.xml',
        'views/connector_views.xml',
        'views/conversation_views.xml',
        'views/message_views.xml',
        'views/res_partner.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
        'views/module_views.xml',
        'views/template_waba_views.xml',
        'reports/report_conversation_views.xml',
        'reports/report_agent_answer_time.xml',
        'views/menu.xml',
        'reports/reports.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/whatsapp_connector/static/src/components/*.js',
            '/whatsapp_connector/static/src/js/basic/*.js',
            '/whatsapp_connector/static/src/js/webclient/actions/*.js',
            '/whatsapp_connector/static/src/js/acrux_*.js',
            '/whatsapp_connector/static/src/legacy/js/control_panel/control_panel.js',
            '/whatsapp_connector/static/src/models/*.js',
            '/whatsapp_connector/static/src/css/*.css',
            '/whatsapp_connector/static/src/*.js',
        ],
        'web.assets_qweb': [
            '/whatsapp_connector/static/src/xml/*',
            '/whatsapp_connector/static/src/components/attachment_viewer/attachment_viewer.xml',
        ],
    },
    'post_load': '',
    'external_dependencies': {'python': ['phonenumbers']},

}
