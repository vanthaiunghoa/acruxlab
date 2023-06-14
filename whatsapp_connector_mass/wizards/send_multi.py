# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError


class AcruxSendMultiWizard(models.TransientModel):
    _name = 'acrux.chat.send.multi.wizard'
    _description = 'ChatRoom Message Multi'

    name = fields.Char('Reference')
    connector_id = fields.Many2one('acrux.chat.connector', string='Send by', ondelete='set null',
                                   default=lambda x: x.env['acrux.chat.connector'].search([], limit=1).id)
    body_whatsapp = fields.Text('Message')
    body_whatsapp_html = fields.Html('Html Message', sanitize=False)
    model = fields.Char('Related Document Model', required=True)
    ws_template_id = fields.Many2one('mail.template', 'Template',
                                     ondelete='set null',
                                     domain="[('model', '=', model), ('name', 'ilike', 'ChatRoom')]")
    mark_invoice_as_sent = fields.Boolean('Mark as sent')
    chatter_log = fields.Boolean('Log in chatter')
    put_in_queue = fields.Boolean('Put in queue', default=True)
    count_ids = fields.Integer('Total', readonly=True)
    check_unique_contact = fields.Boolean('Unique contact?',
                                          help='Verify that messages are not repeated for the same contact')

    @api.model
    def default_get(self, default_fields):
        res_ids = self.env.context.get('active_ids')
        model = self.env.context.get('active_model')
        if not res_ids:
            raise UserError(_("Please select records."))
        if not model:
            raise UserError(_("Please select model."))
        if model == 'account.move':
            invoices = self.env['account.move'].browse(res_ids).filtered(
                lambda move: move.is_invoice(include_receipts=True))
            if not invoices:
                raise UserError(_('You can only send invoices.'))

        res = super(AcruxSendMultiWizard, self).default_get(default_fields)

        if 'count_ids' in default_fields:
            res['count_ids'] = len(self.env.context.get('active_ids'))
        if 'model' in default_fields and 'model' not in res:
            res['model'] = model
        if 'name' in default_fields and 'name' not in res:
            date = fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y-%m-%d %H:%M')
            res['name'] = '%s (%s)' % (self.env['ir.model']._get(model).name, date)
        if 'template_id' in default_fields and 'template_id' not in res:
            res['template_id'] = self.env['mail.template'].search(
                [('model', '=', model), ('name', 'ilike', 'ChatRoom')], limit=1, order='name').id
        return res

    @api.onchange('ws_template_id')
    def onchange_ws_template_id(self):
        if self.ws_template_id:
            self.body_whatsapp = tools.html2plaintext(self.ws_template_id.body_html or '').strip()
            self.body_whatsapp_html = self.ws_template_id.body_html
        else:
            self.body_whatsapp = False
            self.body_whatsapp_html = False

    def send_action(self):
        res_ids = self.env.context.get('active_ids')
        Mass = self.env['mailing.mailing'].with_context(whatsapp_mailing=True)
        mailing_model_id = self.env['ir.model']._get(self.model)
        vals = {
            'mailing_type': 'whatsapp',
            'connector_id': self.connector_id.id,
            'ws_subject': self.name,
            'body_whatsapp': self.body_whatsapp,
            'body_whatsapp_html': self.body_whatsapp_html,
            'check_unique_contact': self.check_unique_contact,
            'ws_template_id': self.ws_template_id.id,
            'mailing_model_id': mailing_model_id.id,
            'mailing_domain': "[('id', 'in', %s)]" % res_ids,
        }
        mass_id = Mass.create(vals)
        if self.put_in_queue:
            mass_id.action_put_in_queue()
        # if self.mark_invoice_as_sent and self.model == 'account.move':
        #     self.env['account.move'].serach([('id', '=', res_ids)]).sudo().write({'is_move_sent': True})
        return {'type': 'ir.actions.act_window_close'}
