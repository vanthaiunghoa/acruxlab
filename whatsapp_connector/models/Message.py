# -*- coding: utf-8 -*-
import hashlib
import base64
import traceback
import json
from werkzeug.utils import secure_filename
from odoo import models, fields, api, _, registry, SUPERUSER_ID
from odoo.exceptions import ValidationError
from ..tools import get_binary_attach, date_delta_seconds
from ..tools import create_attachment_from_url


class AcruxChatMessages(models.Model):
    _inherit = 'acrux.chat.base.message'
    _name = 'acrux.chat.message'
    _description = 'Chat Message'
    _order = 'date_message desc, id desc'

    name = fields.Char('name', compute='_compute_name', store=True)
    msgid = fields.Char('Message Id')
    contact_id = fields.Many2one('acrux.chat.conversation', 'Contact',
                                 required=True, ondelete='cascade', index=True)
    connector_id = fields.Many2one('acrux.chat.connector', related='contact_id.connector_id',
                                   string='Connector', store=True, readonly=True)
    date_message = fields.Datetime('Date', required=True, default=fields.Datetime.now)
    read_date = fields.Datetime('Read Date', index=True)
    from_me = fields.Boolean('Message From Me', index=True)
    company_id = fields.Many2one('res.company', related='contact_id.company_id',
                                 string='Company', store=True, readonly=True)
    ttype = fields.Selection(selection_add=[('contact', 'Contact'),
                                            ('product', 'Product')],
                             ondelete={'contact': 'cascade',
                                       'product': 'cascade'})
    error_msg = fields.Char('Error Message', readonly=True)
    event = fields.Selection([('unanswered', 'Unanswered Message'),  # user asignado
                              ('to_new', 'New Conversation'),  # user que lo hizo o none
                              ('to_curr', 'Start Conversation'),  # user asignado
                              ('to_done', 'End Conversation'),  # user que lo hizo
                              ],
                             string='Event')
    user_id = fields.Many2one('res.users', string='Agent')
    try_count = fields.Integer('Try counter', default=0)
    show_product_text = fields.Boolean('Show Product Text', default=True)
    title_color = fields.Char(related='connector_id.border_color', store=False)
    is_signed = fields.Boolean('Is Signed', default=False)
    template_waba_id = fields.Many2one('acrux.chat.template.waba', 'Template',
                                       ondelete='set null')
    template_params = fields.Text('Params')
    mute_notify = fields.Boolean()
    metadata_type = fields.Selection([('apichat_preview_post', 'apichat_preview_post')])
    metadata_json = fields.Text('Metadata text')

    @api.depends('text')
    def _compute_name(self):
        for r in self:
            if r.text:
                r.name = r.text[:10]
            else:
                r.name = '/'

    def conversation_update_time(self):
        for mess in self:
            is_info = bool(mess.ttype and mess.ttype.startswith('info'))
            if not is_info:
                mess_ids = mess.ids
                dbname = self.env.cr.dbname
                _context = self.env.context

                @self.env.cr.postcommit.add
                def conversation_update():
                    db_registry = registry(dbname)
                    with db_registry.cursor() as cr:
                        env = api.Environment(cr, SUPERUSER_ID, _context)
                        mess = env['acrux.chat.message'].browse(mess_ids)
                        data = {}
                        cont = mess.contact_id
                        if mess.from_me:
                            data.update({'last_sent': mess.date_message})
                            if cont.last_received:
                                data.update({'last_received_first': False})
                        else:
                            # nº message
                            data.update({'last_received': mess.date_message})
                            # 1º message
                            if not cont.last_received_first:
                                data.update({'last_received_first': mess.date_message})

                        last_sent = data.get('last_sent')
                        last_received = data.get('last_received')
                        exist = last_sent or last_received
                        if exist:
                            last = max(last_sent or exist, last_received or exist)
                        else:
                            last = fields.Datetime.now()
                        data.update({'last_activity': last})
                        cont.write(data)

    @api.model
    def get_contact_user(self, conv_id):
        if not conv_id:
            return False
        Conv = self.env['acrux.chat.conversation']
        conv_id = Conv.browse([conv_id])
        return conv_id.agent_id or conv_id.res_partner_id.user_id or False

    @api.model
    def create(self, vals):
        if 'user_id' not in vals:
            from_me = vals.get('from_me')
            user_id = False
            if not from_me:
                user_id = self.get_contact_user(vals.get('contact_id'))
            if not user_id:
                user_id = self.env.user
            if user_id:
                vals.update(user_id=user_id.id)
        ret = super(AcruxChatMessages, self).create(vals)
        ret.filtered('active').conversation_update_time()
        return ret

    def write(self, vals):
        to_update_time = False
        if 'active' in vals and vals['active']:
            to_update_time = self.filtered(lambda x: not x.active)
        res = super(AcruxChatMessages, self).write(vals)
        if to_update_time:
            to_update_time.filtered('active').conversation_update_time()
        return res

    @api.model
    def unlink_attachment(self, attach_to_del_ids, only_old=True):
        data = [('id', 'in', attach_to_del_ids)]
        if only_old:
            data.append(('delete_old', '=', True))
        to_del = self.env['ir.attachment'].sudo().search(data)
        erased_ids = to_del.ids
        to_del.unlink()
        return erased_ids

    def clean_content(self):
        mess_ids = self.filtered(lambda x: x.res_model == 'ir.attachment' and x.res_id)
        attach_to_del = mess_ids.mapped('res_id')
        mess_ids.unlink_attachment(attach_to_del, only_old=False)
        mess_ids.write({'res_model': False, 'res_id': 0})

    def unlink(self):
        ''' Delete attachment too '''
        mess_ids = self.filtered(lambda x: x.res_model == 'ir.attachment' and x.res_id)
        attach_to_del = mess_ids.mapped('res_id')
        ret = super(AcruxChatMessages, self).unlink()
        if attach_to_del:
            self.unlink_attachment(attach_to_del)
        return ret

    @api.model
    def get_fields_to_read(self):
        return ['id', 'text', 'ttype', 'date_message', 'from_me', 'res_model',
                'res_id', 'error_msg', 'show_product_text', 'title_color',
                'user_id', 'metadata_type', 'metadata_json']

    def get_js_dict(self):
        return self.read(self.get_fields_to_read())

    def get_url_image(self, res_model, res_id, field='image_chat', prod_id=None):
        self.ensure_one()
        url = False
        if not prod_id:
            prod_id = self.env[res_model].search([('id', '=', res_id)], limit=1)
        prod_id = prod_id if len(prod_id) == 1 else False
        if prod_id:
            field_obj = getattr(prod_id, field)
            if not field_obj:
                return prod_id, False
            check_weight = self.message_check_weight(field=field_obj)
            if check_weight:
                hash_id = hashlib.sha1(str((prod_id.write_date or prod_id.create_date or '')).encode('utf-8')).hexdigest()[0:7]
                url = '/web/static/chatresource/%s/%s_%s/%s' % (prod_id._name, prod_id.id, hash_id, field)
                base_url = self.connector_id.odoo_url.rstrip('/')
                url = base_url.rstrip('/') + url
        return prod_id, url

    def get_url_attach(self, att_id):
        self.ensure_one()
        url = False
        attach_id = self.env['ir.attachment'].sudo().search([('id', '=', att_id)], limit=1)
        attach_id = attach_id if len(attach_id) == 1 else False
        if attach_id:
            self.message_check_weight(value=attach_id.file_size, raise_on=True)
            access_token = attach_id.generate_access_token()[0]
            url = '/web/chatresource/%s/%s' % (attach_id.id, access_token)
            base_url = self.connector_id.odoo_url.rstrip('/')
            url = base_url.rstrip('/') + url
        return attach_id, url

    def message_parse(self):
        ''' Return message formated '''
        self.ensure_one()
        message = False
        if self.ttype == 'text':
            message = self.ca_ttype_text()
        elif self.ttype in ['image', 'video', 'file']:
            message = self.ca_ttype_file()
        elif self.ttype == 'audio':
            message = self.ca_ttype_audio()
        elif self.ttype == 'product':
            message = self.ca_ttype_product()
        elif self.ttype == 'location':
            message = self.ca_ttype_location()
        elif self.ttype == 'contact':
            raise ValidationError('Not implemented')
        if self.template_waba_id:
            self.set_template_data(message)
        message.update({
            'to': self.contact_id.number,
            'id': str(self.id),
        })
        return message

    def set_template_data(self, message):
        self.ensure_one()
        if self.connector_id.connector_type == 'gupshup':
            message['template_id'] = self.template_waba_id.template_id
            params = json.loads(self.template_params)
            message['params'] = params['params']

    def get_request_path(self):
        self.ensure_one()
        return 'send'

    def message_send(self):
        '''Return msgid
        In: {'type': string (required) ['text', 'image', 'video', 'file', 'audio', 'location'],
             'text': string (required),
             'from': string,
             'to': string,
             'filename': string,
             'url': string,
             'address': string,
             'latitude': string,
             'longitude': string,
             }
        Out: {'msg_id': [string, False],
              }
        '''
        self.ensure_one()
        ret = False
        connector_id = self.contact_id.connector_id
        if not self.ttype.startswith('info'):
            self.message_check_allow_send()
            self.sign()
            data = self.message_parse() or {}
            result = connector_id.ca_request(self.get_request_path(), data)
            msg_id = result.get('msg_id', False)
            if msg_id:
                self.msgid = msg_id
                return msg_id
            else:
                raise ValidationError('Server error.')
        else:
            return ret

    def sign(self):
        self.ensure_one()
        if not self.is_signed and self.text:
            if self.connector_id.allow_signing and self.env.user.chatroom_signing_active \
                    and self.ttype not in ['contact', 'location']:
                self.is_signed = True
                if self.env.user.chatroom_signing:
                    self.text = '%s\n%s' % (self.env.user.chatroom_signing, self.text)
                else:
                    self.text = '%s:\n%s' % (self.env.user.name, self.text)

    def message_check_time(self, raise_on_error=True):
        self.ensure_one()
        if self.connector_id.connector_type == 'gupshup' and self.template_waba_id:
            return True
        contact_id = self.contact_id
        last_received = contact_id.last_received
        max_hours = contact_id.connector_id.time_to_respond
        if max_hours and max_hours > 0:
            if not last_received:
                if raise_on_error:
                    if self.connector_id.connector_type == 'gupshup':
                        raise ValidationError(_('You must send a WABA Template to initiate a conversation.'))
                    raise ValidationError(_('The client must have started a conversation.'))
                return False
            diff_hours = date_delta_seconds(last_received) / 3600
            if diff_hours >= max_hours:
                if raise_on_error:
                    raise ValidationError(_('The time to respond exceeded (%s hours). '
                                          'The limit is %s hours.') % (int(round(diff_hours)), max_hours))
                return False
        return True

    def message_check_allow_send(self):
        ''' Check elapsed time '''
        self.ensure_one()
        if self.text and len(self.text) >= 4000:
            raise ValidationError(_('Message is to large (4.000 caracters).'))
        connector_id = self.contact_id.connector_id
        if not connector_id.ca_status:
            raise ValidationError(_('Sorry, you can\'t send messages.\n%s is not connected.' % connector_id.name))
        if connector_id.connector_type == 'gupshup':
            self.message_check_time()
            if not self.contact_id.is_waba_opt_in:
                raise ValidationError(_('You must request opt-in before send a template message.'))

    def message_check_weight(self, field=None, value=None, raise_on=False):
        ''' Check size '''
        self.ensure_one()
        ret = True
        limit = int(self.env['ir.config_parameter'].sudo().get_param('acrux_max_weight_kb') or '0')
        if limit > 0:
            limit *= 1024  # el parametro esta en kb pero el value pasa en bytes
            if field:
                value = len(base64.b64decode(field) if field else b'')
            if (value or 0) >= limit:
                if raise_on:
                    msg = '%s Kb' % limit if limit < 1000 else '%s Mb' % (limit / 1000)
                    raise ValidationError(_('Attachment exceeds the maximum size allowed (%s).') % msg)
                return False
        return ret

    def ca_ttype_text(self):
        self.ensure_one()
        ret = {
            'type': 'text',
            'text': self.text
        }
        return ret

    def ca_ttype_audio(self):
        self.ensure_one()
        if not self.res_id or self.res_model != 'ir.attachment':
            raise ValidationError('Attachment type is required.')
        attach_id, url = self.get_url_attach(self.res_id)
        if not attach_id:
            raise ValidationError('Attachment is required.')
        if not url:
            raise ValidationError('URL Attachment is required.')
        ret = {
            'type': 'audio',
            'url': url
        }
        return ret

    def ca_ttype_file(self):
        self.ensure_one()
        if not self.res_id or self.res_model != 'ir.attachment':
            raise ValidationError('Attachment type is required.')
        attach_id, url = self.get_url_attach(self.res_id)
        if not attach_id:
            raise ValidationError('Attachment is required.')
        if not url:
            raise ValidationError('URL Attachment is required.')
        ret = {
            'type': self.ttype,
            'text': self.text or '',
            'filename': attach_id.name,
            'url': url
        }
        return ret

    def ca_ttype_product(self):
        self.ensure_one()
        url = False
        filename = ''
        image_field = 'image_chat'  # to set dynamic: self.res_filed
        if not self.res_id or self.res_model != 'product.product':
            raise ValidationError('Product type is required.')
        prod_id, caption = self.contact_id.get_product_caption(self.res_id, self.text)

        # image ----------
        field_image = getattr(prod_id, image_field)
        if field_image:
            filename = secure_filename(prod_id.display_name)
            attach = get_binary_attach(self.env, self.res_model, self.res_id, image_field,
                                       fields_ret=['mimetype'])
            mimetype = attach and attach['mimetype']
            if mimetype:
                ext = mimetype.split('/')
                if len(ext) == 2:
                    filename = secure_filename('%s.%s' % (prod_id.display_name, ext[1]))

            prod_id, url = self.get_url_image(res_model=self.res_model, res_id=self.res_id,
                                              field=image_field, prod_id=prod_id)
        # send ----------
        if not url:
            # Simple text message
            ret = {
                'type': 'text',
                'text': caption
            }
            return ret
        else:
            if not self.connector_id.allow_caption():
                caption = ''
            ret = {
                'type': 'image',
                'text': caption,
                'filename': filename,
                'url': url
            }
        return ret

    def ca_ttype_sale(self):
        self.ensure_one()
        if self.res_model != 'sale.order':
            raise ValidationError('Order type is required.')
        return self.ca_ttype_file()

    def ca_ttype_location(self):
        ''' Text format:
                name
                address
                latitude, longitude
        '''
        self.ensure_one()
        parse = self.text.split('\n')
        if len(parse) != 3:
            return self.ca_ttype_text()
        cords = parse[2].split(',')
        ret = {
            'type': 'location',
            'address': '%s\n%s' % (parse[0].strip(), parse[1].strip()),
            'latitude': cords[0].strip('( '),
            'longitude': cords[1].strip(') '),
        }
        return ret

    def add_attachment(self, data):
        self.ensure_one()
        url = data['url']
        if url.startswith('http'):
            try:
                headers = None
                if self.connector_id.connector_type == 'waba_extern':
                    if 'identify=' in url:
                        split = url.split('identify=')
                        identify = split[1]
                        url = split[0].rstrip('&')
                        headers = {'Authorization': 'Bearer ' + identify}
                attach_id = create_attachment_from_url(self.env, url, self, data.get('filename'), headers)
                self.write({'res_model': 'ir.attachment', 'res_id': attach_id.id})
            except Exception as _e:
                traceback.print_exc()
                self.write({'text': (self.text + ' ' + _('[Error getting %s ]') % url[:50]).strip(),
                            'ttype': 'text'})
        else:
            self.write({'text': (self.text + ' [Error %s]' % url).strip(),
                        'ttype': 'text'})

    def post_create_from_json(self, data):
        self.ensure_one()
        if data['ttype'] in ['image', 'audio', 'video', 'file']:
            self.add_attachment(data)
        if self.contact_id.connector_type == 'apichat.io' and data.get('metadata'):
            self.metadata_json = json.dumps(data.get('metadata'), indent=2)
            self.metadata_type = 'apichat_preview_post'

    def process_message_event(self, data):
        self.ensure_one()
        if data['type'] == 'failed':
            self.error_msg = data['reason']
