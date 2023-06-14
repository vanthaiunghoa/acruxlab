# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_payment_link(self):
        self.ensure_one()
        env = self.env['payment.link.wizard'].with_context(active_model=self._name, active_id=self.id)
        payment = env.create({})
        return payment.link or ''
