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
    'name': 'ChatRoom Marketing & Group with Templates. Whatsapp, Instagram DM, FaceBook Messenger.',
    'summary': 'Send mass message with Templates. Advanced Options. apichat.io Gupshup Chat-Api. ChatApi. Marketing whatsapp group ChatRoom 2.0.',
    'description': 'Send mass WhatsApp with Templates message Marketing. apichat.io. Chat-Api. ChatApi. Marketing whatsapp group ChatRoom 2.0.',
    'version': '15.0.15',
    'author': 'AcruxLab',
    # 'live_test_url': 'https://chatroom.acruxlab.com/web/signup',
    'support': 'info@acruxlab.com',
    'price': 179.0,
    'currency': 'USD',
    'images': ['static/description/Banner_mass_v10.gif'],
    'website': 'https://acruxlab.com/plans',
    'license': 'OPL-1',
    'application': True,
    'installable': True,
    'category': 'Marketing/Email Marketing',
    'depends': [
        'whatsapp_connector',
        'mass_mailing',
        'phone_validation',
        'sms',  # for sms_widget widget
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/utm_data.xml',
        'data/cron.xml',
        'views/menus.xml',
        'views/mailing_contact_views.xml',
        'views/mailing_list_views.xml',
        'views/mailing_mailing_views.xml',
        'views/mailing_trace_views.xml',
        # 'views/utm_campaign_views.xml',
        'views/res_config_settings_views.xml',
        'report/mailing_trace_report_views.xml',
        'wizards/import_records.xml',
        'wizards/mailing_sms_test_views.xml',
        'wizards/send_multi_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/whatsapp_connector_mass/static/src/css/*.css',
        ],
    },
    'qweb': [
    ],
    'post_load': '',
}
