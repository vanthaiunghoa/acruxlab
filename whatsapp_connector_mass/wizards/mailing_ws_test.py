# -*- coding: utf-8 -*-

from odoo import exceptions, models, fields, _
from odoo.addons.whatsapp_connector.tools import clean_number, phone_format


class MassWsTest(models.TransientModel):
    _name = 'mailing.ws.test'
    _description = 'Test Whatsapp Mailing'

    def _default_numbers(self):
        return self.env.user.partner_id.phone_sanitized or ""

    numbers = fields.Char(string='Number', required=True,
                          default=_default_numbers)
    mailing_id = fields.Many2one('mailing.mailing', string='Mailing', required=True, ondelete='cascade')

    def action_send_sms(self):
        '''
            Send test message for whatsapp mailing
            :override
            :see mass_sms
        '''
        self.ensure_one()
        sanitized_number = clean_number(self.numbers)
        valid = phone_format(sanitized_number, raise_error=False)
        if not valid:
            raise exceptions.UserError(_('Number are not correctly encoded: %s, example :'
                                         ' "+56 67 221 7777, +33 545 55 55 55"', self.numbers))
        mailing_id = self.with_context(no_create_trace=True, is_from_wizard=True).mailing_id
        contacts = mailing_id.generate_ws_message_contacts()
        filter_contacts = [x for x in contacts if clean_number(x['number']) == sanitized_number]
        if not filter_contacts:
            raise exceptions.UserError(_('Number does not exist in contacts (%s).', self.numbers))
        contact = filter_contacts[0] if filter_contacts else contacts[0]
        contact['number'] = sanitized_number
        msg_ids = mailing_id.build_ws_messages([contact])
        conv_number = msg_ids[0].contact_id.number if msg_ids else False
        if conv_number and conv_number != sanitized_number:
            raise exceptions.UserError(_('Contact number must be updated to a valid number in Whatsapp: '
                                         '+%s to +%s.') % (sanitized_number, conv_number))
        for msg in msg_ids:
            msg.active = True
            msg.message_send()
        return True
