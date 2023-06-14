# -*- coding: utf-8 -*-
# =====================================================================================
# License: OPL-1 (Odoo Proprietary License v1.0)
#
# By using or downloading this module, you agree not to make modifications that
# affect sending messages through Acruxlab or avoiding contract a Plan with Acruxlab.
# Support our work and allow us to keep improving this module and the service!
#
# Al utilizar o descargar este módulo, usted se compromete a no realizar modificaciones que
# afecten el envío de mensajes a través de Acruxlab o a evitar contratar un Plan con Acruxlab.
# Apoya nuestro trabajo y permite que sigamos mejorando este módulo y el servicio!
# =====================================================================================
import csv
from odoo import models, fields, tools


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ACTIONS --------------
    def import_demo_chatbot(self):
        Bot = self.env['acrux.chat.bot']
        with tools.file_open("whatsapp_connector_bot/data/demo.chat.bot.csv", "r") as csv_file:
            sequence = 99
            for row in csv.DictReader(csv_file):
                vals = {
                    'sequence': sequence,
                    'bot_key': row['Bot Key'] or False,
                    'name': row['Name'] or False,
                    'code': row['Action'] or False,
                    'parent_id': Bot.search([('name', '=', row['Parent Bot/Name'])], limit=1).id,
                    'apply_from': float(row['Apply From'] or 0),
                    'apply_to': float(row['Apply To'] or 0),
                    'mute_minutes': int(float(row['Mute (Minutes)'] or 0)),
                    # 'apply_weekday': row['In days'] or False,
                    'text_match': row['Menu Option'] or False,
                }
                self.env['acrux.chat.bot'].create(vals)
                self.env.cr.commit()
                sequence += 1
            self.env['acrux.chat.bot'].recreate_sequence()
        return self.env['acrux.chat.pop.message'].message('Ok', 'Go to <b>ChatBot</b> menu.')
