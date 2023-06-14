# -*- coding: utf-8 -*-
from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_total_due(self):
        self.ensure_one()
        if hasattr(self, 'total_due'):
            return self.total_due
        else:
            domain = [
                ('partner_id', '=', self.id),
                ('state', 'not in', ['draft', 'cancel']),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
            ]
            model = 'account.move'
            field = 'amount_residual_signed'
            results = self.env[model].read_group(domain, [field], ['partner_id'])
            ret = sum(x[field] for x in results)
            return ret or 0.0
