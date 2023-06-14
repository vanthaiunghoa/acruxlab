# -*- coding: utf-8 -*-

from odoo import models, api


class Template(models.Model):
    _inherit = 'acrux.chat.template.waba'

    @api.model
    def create_or_update(self, data, connector_id):
        if connector_id.connector_type == 'waba_extern':
            new_data = []
            for template in data['data']:
                components = template.get('components', [])
                body = list(filter(lambda tmp: tmp['type'] == 'BODY', components))
                if body:
                    new_data.append({
                        'template_id': template['id'],
                        'name': template['name'],
                        'language_code': template['language'],
                        'status': template['status'],
                        'category': template['category'],
                        'template_type': 'TEXT',
                        'data': body[0]['text'],
                        'app_id': data['app_id'],
                    })
            data = new_data
        return super(Template, self).create_or_update(data, connector_id)
