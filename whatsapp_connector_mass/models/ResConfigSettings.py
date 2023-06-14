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
from odoo import models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def action_create_whatsapp_sidebar(self):
        ActWindow = self.env['ir.actions.act_window']
        check_module = self.env.context.get('check_module')
        check_model = self.env.context.get('check_model')
        module = self.env['ir.module.module'].sudo().search([('name', '=', check_module)], limit=1)
        installed = True if module and module.state == 'installed' else False
        if installed:
            try:
                model_id = self.env['ir.model']._get(check_model)
            except Exception as _e:
                msg = _('You cannot activate this option because you do not have the %s model installed.')
                return self.env['acrux.chat.pop.message'].message('Error', msg % check_model)
            exist = ActWindow.search([('res_model', '=', 'acrux.chat.send.multi.wizard'),
                                      ('binding_model_id', '=', model_id.id)])
            if exist:
                msg = _('Menu already exists.<br/>In the \'Action\' menu you can find \'Send Multi Whatsapp\'.')
                return self.env['acrux.chat.pop.message'].message('Ok', msg)
            ActWindow.create({
                'name': 'Send Multi Whatsapp',
                'type': 'ir.actions.act_window',
                'res_model': 'acrux.chat.send.multi.wizard',
                'view_mode': 'form',
                # 'view_id': view.id,
                'target': 'new',
                # 'binding_view_types': 'list',
                'binding_model_id': model_id.id,
            })
            msg = _('Menu has been created.<br/>In the \'Action\' menu you can find \'Send Multi Whatsapp\'.')
            return self.env['acrux.chat.pop.message'].message('Ok', msg)
        else:
            msg = _('You cannot activate this option because you do not have the %s module installed.')
            return self.env['acrux.chat.pop.message'].message('Error', msg % check_module)
