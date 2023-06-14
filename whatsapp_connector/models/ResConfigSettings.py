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
import requests
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    acrux_chat_base_url = fields.Char('Base Url', config_parameter='web.base.url', readonly=True)
    acrux_chat_check_base_url = fields.Char(compute="_compute_acrux_chat_check_base_url")

    @api.depends('acrux_chat_base_url')
    def _compute_acrux_chat_check_base_url(self):
        for rec in self:
            msg = False
            if 'localhost' in rec.acrux_chat_base_url:
                msg = _('You are working on "localhost", you will not be able to receive messages!')
            rec.acrux_chat_check_base_url = msg

    # ACTIONS --------------
    def open_resource_tree(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Message Templates',
            'view_mode': 'tree,form',
            'res_model': 'mail.template',
            'domain': [('name', 'like', self.env.context.get('acrux_domain', 'ChatRoom')),
                       ('model_id', 'in', [self.env.ref(x).id for x in self.env.context['acrux_model']])],
            'target': 'current',
            'context': {'default_name': 'ChatRoom:'},
        }

    def action_del_and_recreate_image_chat(self):
        self.env['acrux.chat.connector'].sudo().del_and_recreate_image_chat()

    def action_webhook_test(self):
        for rec in self:
            try:
                req = requests.get(rec.acrux_chat_base_url + '/acrux_webhook/test', timeout=5)
                assert req.status_code == 200, 'Error'
                return self.env['acrux.chat.pop.message'].message(_('All good!'))
            except Exception as _e:
                # AssertionError
                pass
            msg = _('You have more than 1 database in %s') % rec.acrux_chat_base_url
            return self.env['acrux.chat.pop.message'].message('Error', msg)
