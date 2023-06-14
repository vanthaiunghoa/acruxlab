
from odoo import tools
from odoo import fields, models


class ConversationReport(models.Model):
    _name = 'conversation.init.report'
    _description = 'Conversation Init Report'
    _auto = False
    _rec_name = 'date_message'
    _order = 'date_message desc'

    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    connector_id = fields.Many2one('acrux.chat.connector', string='Connector',
                                   readonly=True)
    conversation_id = fields.Many2one('acrux.chat.conversation', 'Conversation',
                                      readonly=True)
    agent_id = fields.Many2one('res.users', 'Agent', readonly=True)
    date_message = fields.Datetime('Date', readonly=True)
    amount = fields.Integer('Amount', readonly=True)

    def _query(self):
        # cada conversacion nueva cuenta como una
        # entonces si un agente habla varias veces con un mismo cliente
        # un mismo día, esta cuenta como varias conversaciones

        # TODO cambiar el evento por el de conversacion nueva
        return '''
            SELECT conn.id connector_id,
                   conn.company_id company_id,
                   conv.id conversation_id,
                   msg.id,
                   msg.date_message,
                   msg.user_id as agent_id,
                   1 as amount
              FROM acrux_chat_message msg,
                   acrux_chat_conversation conv,
                   acrux_chat_connector conn,
                   res_users users,
                   res_partner partner
             WHERE     msg.contact_id = conv.id
                   AND conv.connector_id = conn.id
                   AND msg.ttype = 'info'
                   AND msg.event = 'to_curr'
                   AND msg.user_id = users.id
                   and users.partner_id = partner.id
        '''

    def _query_by_day(self):
        # este query considera que solo puede haber una conversacion nueva
        # por dia, entonces si un agente habla varias veces con el mismo
        # cliente por dia, esta conversacion contará como una

        # TODO cambiar el evento por el de conversacion nueva
        return '''
            SELECT a.*,ROW_NUMBER () OVER () as id
              FROM (SELECT DISTINCT conn.id connector_id,
                                    conn.company_id company_id,
                                    conv.id conversation_id,
                                    msg.user_id as agent_id,
                                    DATE_TRUNC('day', msg.date_message at time zone 'utc' at time zone coalesce(partner.tz, 'utc')) date_message,
                                    1 AS amount
                      FROM acrux_chat_message msg,
                           acrux_chat_conversation conv,
                           acrux_chat_connector conn,
                           res_users users,
                           res_partner partner
                     WHERE     msg.contact_id = conv.id
                           AND conv.connector_id = conn.id
                           AND msg.ttype = 'info'
                           AND msg.event = 'to_curr'
                           AND msg.user_id = users.id
                           AND users.partner_id = partner.id) a
        '''

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = 'CREATE or REPLACE VIEW %s as (%s)' % (self._table, self._query())
        self.env.cr.execute(query)
