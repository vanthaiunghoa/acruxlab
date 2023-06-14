# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ImportRecords(models.TransientModel):
    _name = 'mass.whatsapp.import.wizard'
    _description = 'Import records to contacts list'

    contact_list_id = fields.Many2one('mailing.list', string='List',
                                      required=True, ondelete='cascade')
    ttype = fields.Selection([('partner', 'Partner'),
                              ('conversation', 'Conversations')],
                             string='Type', default='partner',
                             required=True)
    partner_ids = fields.Many2many('res.partner', string='Partners',
                                   domain=['|', ('phone', '!=', False), ('mobile', '!=', False)])
    conversation_ids = fields.Many2many('acrux.chat.conversation', string='Conversations')

    def import_records(self):
        '''
            Call functions to import partners or conversation to mailing contacts
        '''
        self.ensure_one()
        out = {}
        if self.ttype == 'partner':
            if not self.partner_ids:
                raise ValidationError(_('You have to select at least one partner.'))
            out = self.contact_list_id.import_partners(self.partner_ids)
        elif self.ttype == 'conversation':
            if not self.conversation_ids:
                raise ValidationError(_('You have to select at least one conversation.'))
            out = self.contact_list_id.import_conversation(self.conversation_ids)
        else:
            raise ValidationError(_('Operation not allowed.'))
        return out
