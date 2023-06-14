# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.tools.translate import _


class MailingList(models.Model):
    _inherit = 'mailing.list'

    def action_view_contacts(self):
        '''
            :override
        '''
        if self.env.context.get('whatsapp_mailing'):
            action = self.env['ir.actions.actions']._for_xml_id('whatsapp_connector_mass.mailing_contact_action_whatsapp')
            action['domain'] = [('list_ids', 'in', self.ids)]
            context = dict(self.env.context,
                           search_defautl_filter_valid_ws_recipient=1,
                           default_list_ids=self.ids,
                           default_is_whatsapp=True)
            action['context'] = context
            return action
        return super(MailingList, self).action_view_contacts()

    def action_import_conversation(self):
        '''
            Return wizard to import chatroom conversations
            :retun dict: odoo action
        '''
        self.ensure_one()
        return self._import_records('conversation')

    def action_import_partner(self):
        '''
            Return wizard to import partners
            :retun dict: odoo action
        '''
        self.ensure_one()
        return self._import_records('partner')

    def _import_records(self, ttype):
        '''
            Action to import records to contact list.
            :return dict: odoo action
        '''
        return {
            'name': _('Import Records'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mass.whatsapp.import.wizard',
            'views': [[False, 'form']],
            'target': 'new',
            'context': dict(default_contact_list_id=self.id, default_ttype=ttype)
        }

    def import_conversation(self, conversation_ids):
        '''
            Import conversations from chatrrom to list, create contact and add
            relation with list
            :param object partner_ids: acrux.chat.conversation
            :return dict: odoo action
        '''
        self.ensure_one()
        Contact = self.env['mailing.contact']
        count = 0
        for conv in conversation_ids.filtered(lambda conv: conv.number_format):
            name = conv.name
            vals = {'list_ids': [(4, self.id)], 'is_whatsapp': True}
            if conv.res_partner_id:
                vals['country_id'] = conv.res_partner_id.country_id.id
                if name == conv.number:
                    name = conv.res_partner_id.name
            contact_id = Contact.search([('ws_phone_normalized', '=', '+' + conv.number)], limit=1)
            if not contact_id:
                data = {
                    'ws_phone': conv.number_format,
                    'name': name,
                }
                contact_id = Contact.create(data)
                contact_id.ws_phone_normalized = '+' + conv.number
            contact_id.write(vals)
            count += 1
        msg = _('Imported %s of %s records selected.') % (count, len(conversation_ids))
        return self.env['acrux.chat.pop.message'].message(_('Import successful'), msg)

    def import_partners(self, partner_ids):
        '''
            Import partners to list, create contact and add relation with list
            :param object partner_ids: res.parter
            :return dict: odoo action
        '''
        self.ensure_one()
        Contact = self.env['mailing.contact']
        contact = Contact.new()
        count = 0
        for partner in partner_ids.filtered(lambda partner: partner.mobile or partner.phone):
            vals = {'ws_phone': partner.mobile or partner.phone,
                    'country_id': partner.country_id.id}
            contact.update(vals)
            contact._compute_ws_phone_normalized()
            if contact.ws_phone_normalized:
                contact_id = Contact.search([('ws_phone_normalized', '=', contact.ws_phone_normalized)],
                                            limit=1)
                if not contact_id:
                    vals.update({
                        'is_whatsapp': True,
                        'name': partner.name,
                        'email': partner.email,
                    })
                    contact_id = Contact.create(vals)
                contact_id.write({'list_ids': [(4, self.id)], 'is_whatsapp': True})
                count += 1
        msg = _('Imported %s of %s records selected.') % (count, len(partner_ids))
        return self.env['acrux.chat.pop.message'].message(_('Import successful'), msg)
