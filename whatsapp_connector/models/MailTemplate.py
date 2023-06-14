# -*- coding: utf-8 -*-
from odoo import models, fields


class Template(models.Model):
    _inherit = 'mail.template'

    waba_template_id = fields.One2many('acrux.chat.template.waba', 'mail_template_id',
                                       string='Waba Template')

    def get_waba_param(self, res_id):
        params = []
        if len(self) == 0 or not res_id:
            return params
        self.ensure_one()
        for param in self.waba_template_id.param_ids:
            # O15 = '{{%s}}' - O14 <= '${%s}'
            template_value = '{{%s}}' % param.value
            res = self._render_template(template_value, self.model, [res_id], post_process=True)
            params.append(res[res_id])
        return params
