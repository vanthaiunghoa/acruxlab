# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import safe_eval


class AcruxChatDefaultAnswer(models.Model):
    _inherit = 'acrux.chat.base.message'
    _name = 'acrux.chat.default.answer'
    _description = 'Chat Default Answer'
    _order = 'sequence'

    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Sequence')
    file_attach = fields.Binary("Attachment", compute='_compute_attach',
                                inverse='_inverse_attach', store=True, attachment=False)
    file_attach_name = fields.Char('File Name')
    is_attached_type = fields.Boolean('Is Attached', compute='_compute_is_attached_type',
                                      store=False)
    show_in_chatroom = fields.Boolean('Show', default=True, help='Show in Chatroom main view')
    ttype = fields.Selection(selection_add=[('code', 'Code')],
                             ondelete={'code': 'cascade'})

    @api.depends('ttype')
    def _compute_is_attached_type(self):
        for rec in self:
            rec.is_attached_type = rec.ttype and rec.ttype not in rec._not_attached_type()

    @api.model
    def _not_attached_type(self):
        return ['text', 'location', 'info', 'code']

    @api.constrains('file_attach', 'ttype')
    def _constrain_status(self):
        for rec in self:
            if rec.ttype not in rec._not_attached_type() and not rec.file_attach:
                raise ValidationError(_('File is required.'))

    @api.onchange('ttype')
    def onchanges(self):
        if self.ttype in self._not_attached_type():
            self.file_attach = False
            self.res_model = False
            self.res_id = False
        else:
            self.text = False

    def _compute_attach(self):
        pass

    def _inverse_attach(self):
        Att = self.env['ir.attachment'].sudo()
        for rec in self:
            if rec.res_id and not rec.file_attach_name:
                Att.search([('res_model', '=', self._name), ('id', '=', rec.res_id)]).unlink()
            if rec.file_attach:
                attac_id = Att.create({'name': rec.file_attach_name,
                                       'type': 'binary',
                                       'datas': rec.file_attach,
                                       'store_fname': rec.file_attach_name,
                                       'res_model': self._name,
                                       'res_id': rec.id})
                attac_id.generate_access_token()
                rec.write({'res_model': 'ir.attachment',
                           'res_id': attac_id.id})
            else:
                rec.write({'res_model': False,
                           'res_id': False})

    @api.onchange('ttype', 'text')
    def _onchange_type_code(self):
        for r in self:
            if r.ttype == 'code' and r.text:
                r.text = r.text.strip()

    @api.constrains('ttype')
    def _constrain_type_code(self):
        for r in self:
            if r.ttype == 'code':
                if not r.text:
                    raise ValidationError(_('Message is required.'))

    def eval_answer(self, conversation_id):
        self.ensure_one()
        if isinstance(conversation_id, (int, list, tuple)):
            conversation_id = self.env['acrux.chat.conversation'].browse(conversation_id)
        local_dict = {
            'datetime': safe_eval.datetime,
            'conversation_id': conversation_id,
            'pytz': safe_eval.pytz,
            'user': self.env.user,
            'now': fields.Datetime.context_timestamp(self, datetime.today()),
            'result': None
        }
        safe_eval.safe_eval(self.text.strip(), locals_dict=local_dict, mode='exec', nocopy=True)
        return local_dict['result']

    @api.model
    def get_fields_to_read(self):
        return ['name', 'sequence', 'id', 'text', 'ttype', 'res_model', 'res_id']

    @api.model
    def get_for_chatroom(self):
        return self.search_read([('show_in_chatroom', '=', True)], self.get_fields_to_read())
