# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ConversationActivities(models.Model):
    _name = 'acrux.chat.conversation.activities'
    _description = 'Conversation Activities'
    _rec_name = 'ttype'
    _order = 'id desc'

    conversation_id = fields.Integer('Conversation', required=True, index=True)
    ttype = fields.Selection([('generic', 'Generic')], string='Type', required=True, index=True)
    rec_id = fields.Integer('Resource id')

    @api.autovacuum
    def _gc_generic(self):
        ''' Please create autovacuum for each ttype '''
        unlink_old = fields.Datetime.subtract(fields.Datetime.now(), days=1)
        self.sudo().search([('ttype', '=', 'generic'), ('create_date', '<', unlink_old)]).unlink()
