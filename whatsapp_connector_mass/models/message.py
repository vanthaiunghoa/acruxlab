# -*- coding: utf-8 -*-

from odoo import models, fields


class AcruxChatMessages(models.Model):
    _inherit = 'acrux.chat.message'

    mailing_id = fields.Many2one('mailing.mailing', 'Marketing', ondelete='set null')
    # should be just one
    mailing_trace_ids = fields.One2many('mailing.trace', 'ws_message_id',
                                        string='Trace')
    mailing_res_id = fields.Integer()

    def message_send(self):
        '''
            :override
            Set mailing trace to sent state.
        '''
        out = super(AcruxChatMessages, self).message_send()
        if out:
            self.mailing_trace_ids.write({'trace_status': 'sent',
                                          'sent_datetime': fields.Datetime.now()})
        return out

    def process_message_event(self, data):
        super(AcruxChatMessages, self).process_message_event(data)
        if data['type'] == 'failed' and self.mailing_res_id:
            conv_id = self.contact_id
            msg = self.error_msg or 'Failed'
            res_model = self.env[self.mailing_id.mailing_model_real].sudo()
            record = res_model.browse(self.mailing_res_id)
            self.mailing_id.create_trace_error(conv_id.number, record, msg=msg)
