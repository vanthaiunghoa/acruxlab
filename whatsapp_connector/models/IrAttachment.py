# -*- coding: utf-8 -*-
from odoo import models, fields, api


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    delete_old = fields.Boolean('Delete if old', default=False,
                                help="It can be removed if it is old.")

    def write(self, vals):
        if 'public' not in vals and vals.get('res_model', '') == 'acrux.chat.message':
            vals['public'] = True
        return super(IrAttachment, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'public' not in vals and vals.get('res_model', '') == 'acrux.chat.message':
                vals['public'] = True
        return super(IrAttachment, self).create(vals_list)

    def read_from_chatroom(self, field_read=None, load='_classic_read'):
        if not field_read:
            field_read = self.env['acrux.chat.conversation'].get_attachment_fields_to_read()
        return self.sudo().read(fields=field_read, load=load)
