# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.addons.bus.controllers.main import BusController


class BusControllerInherit(BusController):

    def _poll(self, dbname, channels, last, options):
        user_id = request.session.uid
        if user_id and request.env.user.has_group('whatsapp_connector.group_chat_basic'):
            cids = request.httprequest.cookies.get('cids', str(request.env.company.id))
            cids = [int(cid) for cid in cids.split(',')]
            company_id = cids[0]
            channels = list(channels)
            connector_ids = request.env['acrux.chat.connector'].connector_cache()
            for conn_id in connector_ids:
                channels.append((request.db, 'acrux.chat.conversation', company_id, conn_id))
            channels.append((request.db, 'acrux.chat.conversation', 'private', company_id, user_id))
        return super(BusControllerInherit, self)._poll(dbname, channels, last, options)
