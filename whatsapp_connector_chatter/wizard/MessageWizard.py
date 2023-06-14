# -*- coding: utf-8 -*-
from odoo import models


class ChatMessageWizard(models.TransientModel):
    _inherit = 'acrux.chat.message.wizard'

    def send_message_wizard(self):
        out = super(ChatMessageWizard, self).send_message_wizard()
        if not self.env.context.get('is_acrux_chat_room'):
            if not out:
                out = {}
            out.update({
                'type': 'ir.actions.client',
                'tag': 'acrux.chat.hide_chatter_whatsapp_tag',
            })
        return out
