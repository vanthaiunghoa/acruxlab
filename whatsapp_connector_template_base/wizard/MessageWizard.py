# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class ChatMessageWizard(models.TransientModel):
    _inherit = 'acrux.chat.message.wizard'

    def default_get_attachment(self):
        ''' now by template '''
        pass

    def use_template(self):
        return True

    @api.model
    def default_get(self, default_fields):
        vals = super(ChatMessageWizard, self).default_get(default_fields)
        if 'model' in default_fields and 'model' not in vals:
            vals['model'] = self.env.context.get('active_model')
        if 'res_id' in default_fields and 'res_id' not in vals:
            vals['res_id'] = self.env.context.get('active_id')
        if 'template_id' in default_fields and 'template_id' not in vals and vals.get('model'):
            vals['template_id'] = self.env['mail.template'].search(
                [('model', '=', vals['model']), ('name', 'ilike', 'ChatRoom')], limit=1, order='name').id
        return vals

    @api.onchange('attachment_ids')
    def onchange_attachment_ids(self):
        Attachment = self.env['ir.attachment']
        for attac_id in self.attachment_ids:
            if not attac_id.access_token:
                data_attach = {
                    'name': attac_id.name,
                    'datas': attac_id.datas,
                    'res_model': 'acrux.chat.message.wizard',
                    'access_token': attac_id._generate_access_token(),
                    'res_id': 0,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                    'delete_old': True,
                }
                new_id = Attachment.create(data_attach)
                self.attachment_ids = [(2, attac_id.id)]
                self.attachment_ids = [(4, new_id.id)]

    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        self.ensure_one()
        self.attachment_ids = False
        res_id = self.res_id
        template_id = self.template_id.id
        if template_id:
            values = self.generate_email_for_composer(
                template_id, [res_id],
                ['body_html', 'attachment_ids']
            )[res_id]
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            for attach_fname, attach_datas in values.pop('attachments', []):
                data_attach = {
                    'name': attach_fname,
                    'datas': attach_datas,
                    'res_model': 'acrux.chat.message.wizard',
                    'access_token': Attachment._generate_access_token(),
                    'res_id': 0,
                    'type': 'binary',  # override default_type from context, possibly meant for another model!
                    'delete_old': True,
                }
                attachment_ids.append(Attachment.create(data_attach).id)
            if values.get('attachment_ids', []) or attachment_ids:
                values['attachment_ids'] = [(6, 0, values.get('attachment_ids', []) + attachment_ids)]
        else:
            values = {'text': False, 'attachment_ids': False}

        if values.get('body_html'):
            values['body'] = values.pop('body_html')
        if 'body' in values:
            values['text'] = values.pop('body')

        values = self._convert_to_write(values)

        for fname, value in values.items():
            setattr(self, fname, value)

    @api.model
    def generate_email_for_composer(self, template_id, res_ids, fields):
        multi_mode = True
        if isinstance(res_ids, int):
            multi_mode = False
            res_ids = [res_ids]

        returned_fields = fields + ['partner_ids', 'attachments']  # modificado
        values = dict.fromkeys(res_ids, False)

        template_values = self.env['mail.template'].with_context(tpl_partners_only=True).browse(
            template_id).generate_email(res_ids, fields)
        for res_id in res_ids:
            res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields
                                 if template_values[res_id].get(field))
            res_id_values['body'] = tools.html2plaintext(res_id_values.pop('body_html', '')).strip()
            self._parse_values(res_id_values)
            values[res_id] = res_id_values

        return multi_mode and values or values[res_ids[0]]

    @api.autovacuum
    def _gc_lost_attachments(self):
        limit_date = fields.Datetime.subtract(fields.Datetime.now(), days=1)
        self.env['ir.attachment'].search([
            ('res_model', '=', 'acrux.chat.message.wizard'),
            ('res_id', '=', 0),
            ('create_date', '<', limit_date),
            ('write_date', '<', limit_date)]
        ).unlink()

    @api.model
    def _parse_values(self, values):
        pass

    def _parse_msg_data(self, conv_id):
        msg_datas = super(ChatMessageWizard, self)._parse_msg_data(conv_id)
        attac_ids = self.attachment_ids
        if attac_ids:
            att_mes = {'ttype': 'file',
                       'from_me': True,
                       'contact_id': conv_id.id,
                       'res_model': 'ir.attachment'}
            for attac_id in attac_ids.sorted(key='id'):
                if attac_id.mimetype in ['image/jpeg', 'image/png', 'image/gif']:
                    att_mes.update({'ttype': 'image'})
                attac_id.res_model = 'acrux.chat.message'
                att_mes.update({'text': attac_id.name,
                                'res_id': attac_id.id})
                if not conv_id.connector_id.allow_caption():
                    att_mes.update({'text': ''})
                msg_datas.append(dict(att_mes))
        return msg_datas
