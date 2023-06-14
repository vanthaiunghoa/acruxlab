# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.addons.whatsapp_connector.tools import get_binary_attach


class Conversation(models.Model):
    _inherit = 'acrux.chat.conversation'

    @api.onchange('res_partner_id')
    def onchange_res_partner_id(self):
        convs = self.filtered(lambda conv: conv.connector_id.is_owner_facebook())
        convs = convs.filtered(lambda conv: not conv.connector_id.is_waba_extern())
        super(Conversation, self - convs).onchange_res_partner_id()

    def update_conversation(self):
        if self.connector_id.is_owner_facebook():
            if not self.env.context.get('not_download_profile_picture'):
                if not self.connector_id.is_waba_extern():  # waba_extern no lo soporta
                    params = {'chatId': self.number}
                    self._update_conversation(params, timeout=None)
        else:
            super(Conversation, self).update_conversation()

    @api.model
    def search_partner_from_number(self, conv_id):
        out = self.env['res.partner']
        if not conv_id.connector_id.is_owner_facebook():
            out = super(Conversation, self).search_partner_from_number(conv_id)
        elif conv_id.connector_id.is_waba_extern():
            out = super(Conversation, self).search_partner_from_number(conv_id)
        return out

    def conversation_send_read(self):
        convs = self.filtered(lambda conv: conv.connector_id.is_owner_facebook())
        super(Conversation, self - convs).conversation_send_read()

        Message = self.env['acrux.chat.message']
        for conv_id in convs:
            conn_id = conv_id.connector_id
            if conn_id.ca_status and conn_id.is_facebook():
                message_id = Message.search([('contact_id', '=', conv_id.id)], limit=1)
                if message_id and message_id.message_check_time(raise_on_error=False):
                    conv_id.mark_conversation_read({'phone': conv_id.number})
            elif conn_id.ca_status and conn_id.is_waba_extern():
                message_ids = Message.search_read([('contact_id', '=', conv_id.id),
                                                   ('from_me', '=', False),
                                                   ('read_date', '=', False)], fields=['msgid'], limit=20)
                if message_ids:
                    message_ids = list(map(lambda msg: msg['msgid'], message_ids))
                    conv_id.mark_conversation_read({'message_ids': message_ids}, timeout=30)

    @api.model
    def _get_message_allowed_types(self):
        out = super(Conversation, self)._get_message_allowed_types()
        out.append('url')
        return out

    def split_complex_message(self, msg_data):
        msg_data = super(Conversation, self).split_complex_message(msg_data)
        if (self.connector_id.is_owner_facebook() and not self.connector_id.is_waba_extern() and
                msg_data['ttype'] in ('product', 'image', 'video', 'file', 'audio')):

            def create_text_message(msg_origin, caption):
                msg_2nd = msg_origin.copy()
                msg_2nd.update({'ttype': 'text', 'text': caption, 'res_model': False, 'res_id': False})
                msg_origin['text'] = ''  # quitar el caption al mensaje original
                return msg_2nd

            msg_2nd = None
            caption = msg_data.get('text', '')
            if msg_data['ttype'] in ('file', 'audio'):  # para file y audio, solo se quita el texto si lo tiene
                msg_data['text'] = ''
            elif msg_data['ttype'] == 'product':
                prod_id, caption = self.get_product_caption(msg_data.get('res_id'), caption)
                attach = get_binary_attach(self.env, 'product.product', prod_id.id,
                                           'image_chat', fields_ret=['id'])
                if caption and attach:  # se tiene que crear un mensaje nuevo
                    msg_2nd = create_text_message(msg_data, caption)  # nuevo mensaje
                    msg_data['show_product_text'] = False
            elif msg_data['ttype'] in ('image', 'video'):  # se crea otro mensaje de tipo texto con el caption
                if caption:
                    msg_2nd = create_text_message(msg_data, caption)
                msg_data['text'] = ''
            if msg_2nd:  # enviar y notificar el mensaje
                message_obj = self.env['acrux.chat.message'].create(msg_2nd)
                message_obj.message_send()
                data_to_send = self.build_dict(limit=0)
                data_to_send[0]['messages'] = message_obj.get_js_dict()
                self._sendone(self.get_bus_channel(), 'new_messages', data_to_send)
        return msg_data

    @api.model
    def new_webhook_event(self, connector_id, event):
        ttype = event.get('type')
        if ttype == 'face-status':
            connector_id.process_facebook_get_status(event)
        else:
            super(Conversation, self).new_webhook_event(connector_id, event)
