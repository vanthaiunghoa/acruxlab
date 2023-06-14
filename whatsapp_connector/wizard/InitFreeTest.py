# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.tools.translate import _


class InitFreeTestWizard(models.TransientModel):
    _name = 'init.free.test.wizard'
    _description = 'Init Free Test'

    connector_id = fields.Many2one('acrux.chat.connector', 'Connector', required=True,
                                   ondelete='cascade')

    def init_test(self):
        self.ensure_one()
        self.connector_id.init_free_test()
        PopMessage = self.env['acrux.chat.pop.message']
        pop = _('<p>We have created your account.<br/>On the "Connector" tab click on "Check Status or Get QR".</p>')
        return PopMessage.message(_('Good !'), pop)
