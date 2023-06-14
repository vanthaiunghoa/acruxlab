# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ConversationActivities(models.Model):
    _inherit = 'acrux.chat.conversation.activities'

    ttype = fields.Selection(selection_add=[('bot_thread', 'BOT thread'), ('bot_mute', 'BOT mute')],
                             ondelete={'bot_thread': 'cascade', 'bot_mute': 'cascade'})

    @api.autovacuum
    def _gc_chat_bot(self):
        self.clean_chat_bot(max_thread_hours=48, max_mute_hours=48)

    @api.model
    def clean_chat_bot(self, max_thread_hours=0, max_mute_hours=0):
        if max_thread_hours > 0:
            unlink_old = fields.Datetime.subtract(fields.Datetime.now(), hours=max_thread_hours)
            self.sudo().search([('ttype', '=', 'bot_thread'),
                                ('create_date', '<', unlink_old)]).unlink()
        if max_mute_hours > 0:
            unlink_old = fields.Datetime.subtract(fields.Datetime.now(), hours=max_mute_hours)
            self.sudo().search([('ttype', '=', 'bot_mute'),
                                ('create_date', '<', unlink_old)]).unlink()
