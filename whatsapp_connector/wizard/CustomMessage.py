# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools.translate import _


class PopMessage(models.TransientModel):
    '''
        To Use:
        return self.env['acrux.chat.pop.message'].message('Message','<b>Detail</b>')
    '''
    _name = 'acrux.chat.pop.message'
    _description = 'Pop Message'

    name = fields.Char('Message')
    info = fields.Html('Detail')

    @api.model
    def message(self, name, html=''):
        return {
            'name': _('Message'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'acrux.chat.pop.message',
            'target': 'new',
            'context': dict(default_name=name, default_info=html)
        }
