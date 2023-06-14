# -*- coding: utf-8 -*-
from odoo import models, fields


class Connector(models.Model):
    _inherit = 'acrux.chat.connector'

    bot_log = fields.Boolean('ChatBot Log')
    thread_minutes = fields.Integer('Exit Childs (Minutes)', default=60,
                                    help='Minutes to stay in childs without activity. '
                                         'After this time, it returns to root.')
