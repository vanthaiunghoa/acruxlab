
from odoo import tools
from odoo import fields, models


class AnswerTime(models.Model):
    _name = 'agent.answer.time.report'
    _description = 'Agent Answer Time Report'
    _auto = False

    '''pueden traerse todos los campos de mensaje'''
    name = fields.Char('Name', readonly=True)
    contact_id = fields.Many2one('acrux.chat.conversation', 'Conversation', readonly=True)
    connector_id = fields.Many2one('acrux.chat.connector', 'Connector', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    user_id = fields.Many2one('res.users', 'Agent', readonly=True)
    date_message = fields.Datetime('Date', readonly=True)
    date_answer = fields.Datetime('Answer Date', readonly=True)

    prev_message_id = fields.Many2one('acrux.chat.message', string='Client Message', readonly=True)
    next_message_id = fields.Many2one('acrux.chat.message', string='Answer Message', readonly=True)
    info_message_id = fields.Many2one('acrux.chat.message', string='Info Message', readonly=True)
    answer_time = fields.Float('Answer Time (sec)', readonly=True, group_operator='avg')

    def create_info_message(self):
        info_message_view_name = 'acrux_info_message'
        tools.drop_view_if_exists(self.env.cr, info_message_view_name)
        query = """
CREATE OR REPLACE VIEW %s AS
SELECT m.*
FROM acrux_chat_message m
WHERE m.ttype = 'info'
    AND m.event = 'to_curr'
ORDER BY m.id
        """ % info_message_view_name
        self.env.cr.execute(query)

    def create_prev_message(self):
        prev_message_function_name = 'acrux_prev_message'
        self.env.cr.execute('DROP FUNCTION IF EXISTS %s' % prev_message_function_name)
        self.env.cr.execute("""
CREATE OR REPLACE FUNCTION %s (p_contact_id INTEGER, p_info_id INTEGER)
RETURNS INTEGER AS $prev_id$
DECLARE
   prev_id INTEGER;
BEGIN
    SELECT m.id
    INTO prev_id
    FROM acrux_chat_message m
    WHERE m.contact_id = p_contact_id
        AND m.id < p_info_id
        AND m.ttype NOT LIKE 'info%%'
        AND m.from_me = FALSE
    ORDER BY m.id DESC
    LIMIT 1;

    RETURN prev_id;
END; $prev_id$ LANGUAGE plpgsql;
        """ % prev_message_function_name)

    def create_next_message(self):
        next_message_function_name = 'acrux_next_message'
        self.env.cr.execute('DROP FUNCTION IF EXISTS %s' % next_message_function_name)
        self.env.cr.execute("""
CREATE OR REPLACE FUNCTION %s (p_contact_id INTEGER, p_info_id INTEGER)
RETURNS INTEGER AS $next_id$
DECLARE
   next_id INTEGER;
BEGIN
    SELECT m2.id
    INTO next_id
    FROM (
        SELECT m3.*
        FROM acrux_chat_message m3
        WHERE m3.contact_id = p_contact_id
            AND m3.id > p_info_id
        ORDER BY m3.id
        LIMIT 1
    ) m2
    WHERE m2.ttype NOT LIKE 'info%%'
    AND m2.from_me = TRUE;

    RETURN next_id;
END; $next_id$ LANGUAGE plpgsql;
        """ % next_message_function_name)

    def query(self):
        return """
SELECT
    ROW_NUMBER () OVER () as id,
    prev_m.name,
    prev_m.contact_id,
    prev_m.connector_id,
    prev_m.company_id,
    info2.user_id,
    prev_m.date_message,
    info2.info_message_id,
    next_m.id as next_message_id,
    prev_m.id as prev_message_id,
    next_m.date_message as date_answer,
    EXTRACT(EPOCH FROM (next_m.date_message - prev_m.date_message)) AS answer_time
FROM (
SELECT info.id info_message_id,
       info.user_id,
       public.acrux_prev_message(info.contact_id, info.id) AS prev_message_id,
       public.acrux_next_message(info.contact_id, info.id) AS next_message_id
FROM acrux_info_message info ) AS info2, acrux_chat_message prev_m, acrux_chat_message next_m
WHERE info2.prev_message_id = prev_m.id
    AND info2.next_message_id = next_m.id
        """

    def init(self):
        self.create_info_message()
        self.create_prev_message()
        self.create_next_message()
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = 'CREATE or REPLACE VIEW %s as (%s)' % (self._table, self.query())
        self.env.cr.execute(query)
