# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'crm.lead'

    conversation_id = fields.Many2one('acrux.chat.conversation', 'ChatRoom',
                                      ondelete='set null', copy=False)
