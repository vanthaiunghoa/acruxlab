# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api
from .. import tools
from datetime import datetime


class Template(models.Model):
    _name = 'acrux.chat.template.waba'
    _description = 'Chat Template Waba'
    _order = 'created_on'

    name = fields.Char('Name')
    template_id = fields.Char('Id', required=True, readonly=True)
    app_id = fields.Char('AppId', required=True, readonly=True)
    category = fields.Char('Category', readonly=True)
    created_on = fields.Datetime('Created On', readonly=True)
    data = fields.Text('Data', readonly=True)
    element_name = fields.Char('Element Name', readonly=True)
    external_id = fields.Char('External ID', readonly=True)
    language_code = fields.Char('Language Code', readonly=True)
    language_policy = fields.Char('Language Policy', readonly=True)
    master = fields.Boolean('Master', readonly=True)
    meta = fields.Text('Meta', readonly=True)
    modified_on = fields.Datetime('Modified On', readonly=True)
    namespace = fields.Char('Namespace', readonly=True)
    reason = fields.Char('Reason', readonly=True)
    status = fields.Char('Status', required=True, readonly=True)
    template_type = fields.Char('Template Type', required=True, readonly=True)
    vertical = fields.Char('Vertical', readonly=True)
    connector_id = fields.Many2one('acrux.chat.connector', 'Connector',
                                   required=True, ondelete='cascade')
    param_ids = fields.One2many('acrux.chat.template.waba.param', 'template_id',
                                string='Params')
    model_id = fields.Many2one('ir.model', string='Apply to', ondelete='cascade')
    mail_template_id = fields.Many2one('mail.template', 'Template', ondelete='set null',
                                       readonly=True, copy=False)
    ready_to_create_template = fields.Boolean('Ready', compute='_compute_ready_to_create_template', store=False)

    def unlink(self):
        self.mapped('mail_template_id').unlink()
        return super(Template, self).unlink()

    def copy(self, default=None):
        default = default or {}
        new_template = super(Template, self).copy(default)
        for param in self.param_ids:
            param.copy(default={'template_id': new_template.id})
        return new_template

    @api.model
    def to_snake_case(self, val):
        return re.sub(r'(?<!^)(?=[A-Z])', '_', val).lower()

    @api.model
    def to_camel_case(self, val):
        split = ''.join(word.title() for word in val.split('_'))
        return split[0].lower() + split[1:]

    @api.model
    def create_or_update(self, data, connector_id):
        out = self.env[self._name]
        field_names = self.fields_get_keys()
        for record in data:
            vals = {self.to_snake_case(key): record[key] for key in record if self.to_snake_case(key) in field_names}
            if vals.get('created_on'):
                vals['created_on'] = tools.date2sure_write(datetime.fromtimestamp(vals['created_on']))
            if vals.get('modified_on'):
                vals['modified_on'] = tools.date2sure_write(datetime.fromtimestamp(vals['modified_on']))
            template_ids = self.search([('connector_id', '=', connector_id.id),
                                        ('template_id', '=', vals['template_id'])])
            if template_ids:
                template_ids.write(vals)
            else:
                vals['connector_id'] = connector_id.id
                template_ids = self.create(vals)
            for template_id in template_ids:
                template_id.create_or_update_params()
            out |= template_ids
        to_unlink = self.search([('connector_id', '=', connector_id.id),
                                 ('id', 'not in', out.ids)])
        to_unlink.unlink()
        return out

    def create_or_update_params(self):
        self.ensure_one()
        Params = self.env['acrux.chat.template.waba.param']
        param_to_delete = self.env['acrux.chat.template.waba.param']
        params = re.findall(r'\{\{\d+\}\}', self.data)
        seen = set()
        params = [x for x in params if len(seen) < len(seen.add(x) or seen)]
        size = max(len(params), len(self.param_ids))
        i = 0
        vals = {'template_id': self.id}
        while i < size:
            if i < len(self.param_ids):
                param = self.param_ids[i]
                if i < len(params):
                    if param.key != params[i]:
                        param.write({'key': params[i], 'value': False})
                else:
                    param_to_delete |= param
            else:
                vals['key'] = params[i]
                Params.create(vals)
            i += 1
        param_to_delete.unlink()

    @api.depends('status', 'model_id', 'name', 'param_ids', 'param_ids.value')
    def _compute_ready_to_create_template(self):
        for rec in self:
            flag = rec.status == 'APPROVED' and rec.model_id and rec.name and all(rec.param_ids.mapped('value'))
            rec.ready_to_create_template = flag

    def create_mail_template(self):
        MailTemplate = self.env['mail.template']
        for rec in self:
            body = rec.data
            for param in rec.param_ids:
                body = body.replace(param.key, '<t t-out="%s" data-oe-t-inline="true" contenteditable="false"></t>' % param.value)
            vals = {'name': 'ChatRoom: ' + rec.name, 'model_id': rec.model_id.id, 'body_html': body}
            if rec.mail_template_id:
                rec.mail_template_id.write(vals)
            else:
                rec.mail_template_id = MailTemplate.create(vals)

    @api.onchange('name', 'model_id')
    def _onchage_name_model(self):
        for rec in self:
            if rec.mail_template_id:
                if rec.name:
                    rec.mail_template_id.name = 'ChatRoom: ' + rec.name
                if rec.mail_template_id.model_id:
                    rec.mail_template_id.model_id = rec.model_id
