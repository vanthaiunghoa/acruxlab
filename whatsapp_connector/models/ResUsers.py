# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons.bus.models.bus_presence import DISCONNECTION_TIMER


class ResUsers(models.Model):
    _inherit = 'res.users'

    acrux_chat_active = fields.Boolean('Active in Chat', default=True)
    is_chatroom_group = fields.Boolean(compute='_compute_is_chat_group', compute_sudo=True, string='ChatRoom User',
                                       store=True)
    chatroom_signing_active = fields.Boolean('Activate Signature', default=False)
    chatroom_signing = fields.Char('Signature')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['acrux_chat_active', 'is_chatroom_group',
                                               'chatroom_signing_active', 'chatroom_signing']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['acrux_chat_active', 'chatroom_signing_active',
                                                'chatroom_signing']

    def write(self, vals):
        out = super(ResUsers, self).write(vals)
        if not self.env.context.get('is_acrux_chat_room') and 'chatroom_signing_active' in vals:
            self.notify_status_changed()
        return out

    @api.depends('groups_id')
    def _compute_is_chat_group(self):
        for user in self:
            user.is_chatroom_group = user.has_group('whatsapp_connector.group_chat_basic') and not user.share

    def toggle_acrux_chat_active(self):
        for r in self:
            r.acrux_chat_active = not r.acrux_chat_active
        self.notify_status_changed()

    def set_chat_active(self, value):
        value = value.get('acrux_chat_active')
        self.acrux_chat_active = value
        self.notify_status_changed()

    def notify_status_changed(self):
        Bus = self.env['bus.bus']
        for record in self:
            status_data = [{'agent_id': [record.id, record.name],
                            'status': record.acrux_chat_active,
                            'signing_active': record.chatroom_signing_active}]
            channel = (record.env.cr.dbname, 'acrux.chat.conversation', 'private', record.env.company.id, record.id)
            Bus._sendone(channel, 'change_status', status_data)

    def chatroom_active(self, check_online=False):
        self.ensure_one()
        active = self.acrux_chat_active
        if active and check_online:
            self.env.cr.execute('''
                SELECT
                    U.id as user_id,
                    CASE WHEN B.last_poll IS NULL THEN 'offline'
                         WHEN age(now() AT TIME ZONE 'UTC', B.last_poll) > interval '%s' THEN 'offline'
                         ELSE 'online'
                    END as im_status
                FROM res_users U
                    LEFT JOIN bus_presence B ON B.user_id = U.id
                WHERE U.id = %s
                    AND U.active = 't'
            ''' % ("%s seconds" % DISCONNECTION_TIMER, self.id))
            result = self.env.cr.dictfetchone()
            active = result['im_status'] == 'online'
        return active
