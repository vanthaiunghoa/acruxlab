# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SimpleNewConversation(models.TransientModel):
    _name = 'acrux.chat.simple.new.conversation.wizard'
    _description = 'New Conversation'

    connector_id = fields.Many2one('acrux.chat.connector', 'Connector', required=True,
                                   ondelete='cascade',
                                   default=lambda self: self.env['acrux.chat.connector'].search([], limit=1).id)
    search_str = fields.Char('Search')
    conversation_ids = fields.Many2many('acrux.chat.conversation', 'conv_chat_simple_new_conversation_wizard_rel')
    operation = fields.Selection([('none', 'None'), ('open', 'Open'),
                                  ('create', 'Create')], 'Operation',
                                 default='none', required=True)

    @api.onchange('connector_id')
    def _on_change_connector_id(self):
        for record in self:
            record.search_str = False
            record.conversation_ids = False
            record.operation = 'none'

    @api.onchange('search_str')
    def _on_change_search(self):
        Conversation = self.env['acrux.chat.conversation']
        for record in self:
            if record.search_str:
                cond = [('connector_id', '=', record.connector_id.id)]
                cond.extend(['|', ('name', 'ilike', record.search_str),
                             ('number', 'ilike', record.connector_id.clean_id(record.search_str))])
                record.conversation_ids = Conversation.search(cond)
                record.operation = 'open' if record.conversation_ids else 'create'
            else:
                record.operation = 'none'

    def create_conversation(self):
        self.ensure_one()
        context = self.env.context.copy()
        context.update({'default_connector_id': self.connector_id.id})
        try:
            phone = self.connector_id.clean_id(self.search_str)
            self.connector_id.assert_id(phone)
            context['default_number'] = phone
        except Exception as _e:
            if not self.search_str[0].isdigit():
                context['default_name'] = self.search_str
        return {
            'type': 'ir.actions.client',
            'tag': 'acrux.chat.create_new_conversation',
            'context': context,
        }
