# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.whatsapp_connector.tools import log_request_error


class Connector(models.Model):
    _inherit = 'acrux.chat.connector'

    connector_type = fields.Selection(selection_add=[('facebook', 'Facebook'),
                                                     ('instagram', 'Instagram'),
                                                     ('waba_extern', 'Waba Extern')],
                                      ondelete={'facebook': 'cascade',
                                                'instagram': 'cascade',
                                                'waba_extern': 'cascade'})

    @api.onchange('connector_type')
    def _onchange_connector_type_fb(self):
        if self.is_facebook():
            self.endpoint = 'https://social.acruxlab.net/prod/v1/fb'
        elif self.is_instagram():
            self.endpoint = 'https://social.acruxlab.net/prod/v1/in'
        elif self.is_waba_extern():
            self.endpoint = 'https://social.acruxlab.net/prod/v1/wa_ext'
        else:
            self.endpoint = 'https://api.acruxlab.net/prod/v2/odoo'

    def get_api_url(self, path=''):
        '''
            :overide
        '''
        self.ensure_one()
        if self.is_owner_facebook():
            out = self.facebook_api_url(path)
        else:
            out = super(Connector, self).get_api_url(path)
        return out

    def ca_get_status(self):
        '''
            :overide
        '''
        self.ensure_one()
        if self.is_owner_facebook():
            out = self.facebook_get_status()
        else:
            out = super(Connector, self).ca_get_status()
        return out

    def get_actions(self):
        '''
            :overide
        '''
        self.ensure_one()
        if self.is_owner_facebook():
            out = self.facebook_get_actions()
        else:
            out = super(Connector, self).get_actions()
        return out

    def response_handler(self, req):
        '''
            :overide
        '''
        self.ensure_one()
        if self.is_owner_facebook():
            if req.status_code == 200:
                try:
                    out = req.json()
                except ValueError as _e:
                    out = {}
            else:
                log_request_error([req.text or req.reason], req)
                raise ValidationError(req.text or req.reason)
        else:
            out = super(Connector, self).response_handler(req)
        return out

    def ca_request(self, path, data={}, params={}, timeout=False, ignore_exception=False):
        '''
            :overide
        '''
        self.ensure_one()
        if self.is_owner_facebook():
            path = self.get_facebook_path(path)
            if path is None:
                return
        vals = {
            'path': path,
            'data': data,
            'params': params,
            'timeout': timeout,
            'ignore_exception': ignore_exception
        }
        return super(Connector, self).ca_request(**vals)

    def get_facebook_path(self, path):
        if path == 'config_set':
            path = 'config'
        elif path == 'contact_get':
            path = 'contact'
        elif path == 'send':
            path = 'sendMessage'
        elif path == 'msg_set_read':
            if self.is_instagram():  # instagram no soporta marcar como leido
                path = None
            else:
                path = 'readChat'
        elif path == 'status_logout':
            path = 'logout'
        elif path == 'template_get':  # facebook e instagram no soprotan
            path = 'templates' if self.is_waba_extern() else None
        return path

    def assert_id(self, key):
        '''
            :overide
        '''
        if not self.is_owner_facebook() or self.is_waba_extern():
            super(Connector, self).assert_id(key)

    def clean_id(self, key):
        '''
            :overide
        '''
        out = False
        if self.is_owner_facebook() and not self.is_waba_extern():
            out = key
        else:
            out = super(Connector, self).clean_id(key)
        return out

    def format_id(self, key):
        '''
            :overide
        '''
        if self.is_facebook():
            out = 'Facebook'
        elif self.is_instagram():
            out = 'Instagram'
        else:
            out = super(Connector, self).format_id(key)
        return out

    def is_owner_facebook(self):
        return self.connector_type in ['facebook', 'instagram', 'waba_extern']

    def is_facebook(self):
        return self.connector_type == 'facebook'

    def is_instagram(self):
        return self.connector_type == 'instagram'

    def is_waba_extern(self):
        return self.connector_type == 'waba_extern'

    def facebook_api_url(self, path):
        self.ensure_one()
        return '%s/%s' % (self.endpoint.strip('/'), path)

    @api.model
    def facebook_get_actions(self):
        return {
            'status': 'get',
            'config': 'post',
            'contact': 'get',
            'logout': 'post',
            'readChat': 'post',
            'sendMessage': 'post',
            'templates': 'get',
        }

    def facebook_get_status(self):
        self.ensure_one()
        if self.connector_type == 'not_set':
            raise ValidationError(_('"Connect to" is not set, check out your config.'))
        Pop = self.env['acrux.chat.pop.message']
        self.ca_qr_code = False
        params = {
            'webhook': self.webhook_url,
            'lang': self.env.context.get('lang', 'en'),
        }
        data = self.ca_request('status', timeout=20, params=params)
        message, detail, redirectData = self.process_facebook_get_status(data)
        return Pop.message(message, detail) if message else redirectData

    def process_facebook_get_status(self, data):
        self.ensure_one()
        message = detail = False
        redirectData = True
        if 'is_connected' in data:
            if data['is_connected']:
                detail = _('Connected.')
                message = 'Status'
                self.ca_status = True
                self.message = detail
                self.ca_set_settings()
            else:
                message = 'Status'
                detail = data.get('reason', _('An unexpected error occurred'))
                self.ca_status = False
                self.message = detail
        elif 'url' in data:
            redirectData = {
                'type': 'ir.actions.act_url',
                'url': data['url'],
                'target': 'self',
            }
        else:
            self.ca_status = False
            message = 'An unexpected error occurred. Please try again.'
            self.message = message
        return message, detail, redirectData

    def allow_caption(self):
        out = super(Connector, self).allow_caption()
        if self.is_owner_facebook():
            out = self.is_waba_extern()  # instagram y facebook no lo soportan
        return out
