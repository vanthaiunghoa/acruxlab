# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.addons.whatsapp_connector.tools import clean_number, phone_format


class MailingContact(models.Model):
    _inherit = 'mailing.contact'

    is_whatsapp = fields.Boolean(string='Is Whatsapp', default=False)
    ws_phone = fields.Char(string='Phone')
    ws_phone_normalized = fields.Char(string='Phone Normalize',
                                      compute="_compute_ws_phone_normalized",
                                      compute_sudo=True, store=True)

    @api.depends('ws_phone')
    def _compute_ws_phone_normalized(self):
        for record in self:
            sanitized = clean_number(record.ws_phone)
            valid = phone_format(sanitized, raise_error=False)
            record.ws_phone_normalized = sanitized if valid else False
