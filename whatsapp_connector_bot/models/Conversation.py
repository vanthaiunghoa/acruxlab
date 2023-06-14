# -*- coding: utf-8 -*-
from odoo import models
import traceback
import logging
_logger = logging.getLogger(__name__)


class AcruxChatConversation(models.Model):
    _inherit = 'acrux.chat.conversation'

    def get_to_current(self):
        out = super(AcruxChatConversation, self).get_to_current()
        self.env['acrux.chat.bot'].bot_clean(self.id)
        return out

    def new_message_hook(self, message_id, limit, data, last_sent):
        limit, send_bus = super(AcruxChatConversation, self).new_message_hook(message_id, limit, data, last_sent)
        if message_id.contact_id.status != 'current':
            rollback = False
            try:
                messages = self.env['acrux.chat.bot']._bot_get(message_id)
                for mess in messages:
                    rollback = True
                    self.env.cr.commit()  # commit time
                    message_id.contact_id.send_message(mess, check_access=False)
                    limit += 1
                if message_id.contact_id.status == 'done':
                    # When BOT change status to 'done'
                    if messages:
                        self.env.cr.commit()
                    message_id.contact_id.release_conversation_bot()
                    limit = 0
                    send_bus = False
                elif message_id.contact_id.status == 'current':
                    # When BOT change status to 'current'. Agent required !
                    if messages:
                        self.env.cr.commit()
                    if message_id.contact_id.agent_id:
                        message_id.contact_id.tmp_agent_id = message_id.contact_id.agent_id.id
                        message_id.contact_id.delegate_conversation()
                        limit = 0
                        send_bus = False
            except Exception as e:
                if rollback:
                    self.env.cr.rollback()
                _logger.warning("BOT error: %s" % self)
                _logger.exception(e)
                self.env['acrux.chat.bot.log'].sudo().create({
                    'conversation_id': message_id.contact_id.id,
                    'text': message_id.text,
                    'bot_log': traceback.format_exc(),
                })

        return limit, send_bus

    def search_partner_bot(self, domain=False):
        self.ensure_one()
        ResPartner = self.env['res.partner']
        if not domain:
            domain = [('company_id', 'in', [self.connector_id.company_id.id, False]),
                      ('conv_standard_numbers', 'like', self.number)]
        return ResPartner.search(domain)

    def release_conversation_bot(self):
        self.ensure_one()
        self.release_conversation()
        conv_delete_ids = self.read(['id', 'agent_id'])
        notifications = []
        notifications.append((self.get_channel_to_many(), 'delete_taken_conversation', conv_delete_ids))
        notifications.append((self.get_channel_to_many(), 'delete_conversation', conv_delete_ids))
        self._sendmany(notifications)
