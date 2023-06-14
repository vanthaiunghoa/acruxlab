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
    'name': 'ChatRoom SEND BASE',
    'summary': 'Base module for others. Messages and Templates.',
    'description': 'Base module for others. WhatsApp Messages and Templates.',
    'version': '15.0.5',
    'author': 'AcruxLab',
    'live_test_url': 'https://chatroom.acruxlab.com/web/signup',
    'support': 'info@acruxlab.com',
    'price': 0.0,
    'currency': 'USD',
    'images': ['static/description/Banner_PACK_v4.png'],
    'website': 'https://acruxlab.com/plans',
    'license': 'OPL-1',
    'application': True,
    'installable': True,
    'auto_install': True,
    'category': 'Discuss',
    'depends': [
        'whatsapp_connector',
    ],
    'data': [
        'data/data.xml',
        'wizard/MessageWizard.xml',
        'views/res_config_settings_views.xml',
    ],
    'qweb': [
    ],
}
