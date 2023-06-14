# -*- coding: utf-8 -*-
from odoo import models, fields


class TemplateParam(models.Model):
    _name = 'acrux.chat.template.waba.param'
    _description = 'Chat Template Waba Param'
    _rec_name = 'key'
    _order = 'template_id, key'

    template_id = fields.Many2one('acrux.chat.template.waba', string='Template',
                                  required=True, ondelete='cascade')
    key = fields.Char('Param', required=True)
    value = fields.Char('Replacement')
