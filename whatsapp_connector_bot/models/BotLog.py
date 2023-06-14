# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AcruxChatBotLog(models.Model):
    _name = 'acrux.chat.bot.log'
    _description = 'ChatBot Log'
    _order = 'id desc'
    _rec_name = 'create_date'

    bot_log = fields.Text('Log')
    text = fields.Text('Message')
    conversation_id = fields.Many2one('acrux.chat.conversation', string='Contact',
                                      ondelete='cascade', readonly=True)
    connector_id = fields.Many2one(related='conversation_id.connector_id', string='Connector',
                                   ondelete='cascade', readonly=True)

    @api.autovacuum
    def _gc_mute(self):
        unlink_old = fields.Datetime.subtract(fields.Datetime.now(), days=7)
        self.sudo().search([('create_date', '<', unlink_old)]).unlink()
