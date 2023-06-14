# -*- coding: utf-8 -*-

import logging
import pytz
import json
from datetime import datetime
from random import randrange
from time import time, sleep
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.addons.whatsapp_connector.tools import phone_format, date2local
from psycopg2 import OperationalError
_logger = logging.getLogger(__name__)


class Mailing(models.Model):
    _inherit = 'mailing.mailing'

    @api.model
    def default_get(self, fields):
        '''
            :override
            :see mass_sms
        '''
        res = super(Mailing, self).default_get(fields)
        if fields is not None and 'keep_archives' in fields and res.get('mailing_type') == 'whatsapp':
            res['keep_archives'] = True
        return res

    mailing_type = fields.Selection(selection_add=[('whatsapp', 'Whatsapp')],
                                    ondelete={'whatsapp': 'set default'})
    connector_id = fields.Many2one('acrux.chat.connector', 'Connector',
                                   domain="[('connector_type', 'in', ['apichat.io', 'gupshup'])]",
                                   ondelete='set null')
    connector_type = fields.Selection(related='connector_id.connector_type', store=False, readonly=True)
    connector_status = fields.Boolean(related='connector_id.ca_status')
    body_whatsapp = fields.Text('Whatsapp Body', default='Hello {name}')
    body_whatsapp_html = fields.Html('Html Message', sanitize=False)
    ws_subject = fields.Char('Reference', help='Internal reference',
                             related='subject', translate=False, readonly=False)
    spam_level = fields.Selection([('1', '600 messages per hour'),
                                   ('2', '200 messages per hour'),
                                   ('3', '100 messages per hour')], 'Speed', default='1',
                                  help='If sending to new numbers, a lower speed is recommended.')
    check_unique_contact = fields.Boolean('Unique contact?',
                                          help='Verify that messages are not repeated for the same contact')
    loop_count = fields.Integer('Loop counter', default=0)
    total_ws = fields.Integer(compute='_compute_total_ws', store=False)
    total_ws_sent = fields.Integer(compute='_compute_total_ws', store=False)
    total_ws_pend = fields.Integer(compute='_compute_total_ws', store=False)
    total_ws_contact = fields.Integer(compute='_compute_total_ws', store=False)
    ws_template_id = fields.Many2one('mail.template', 'Template',
                                     ondelete='set null',
                                     domain="[('model', '=', mailing_model_real), ('name', 'ilike', 'ChatRoom')]")
    # O15 see account_move.py
    # mailing_model_id = fields.Many2one(domain=[('model', 'in', MASS_MAILING_BUSINESS_MODELS + ['account.move'])])
    message_limit = fields.Integer('Messages limit', default=0,
                                   help='Maximum messages number allowed to send in one day.')
    enable_from_hour = fields.Float('Enable From', help='00:00 to 23:59', default=0.0, required=True)
    enable_to_hour = fields.Float('Enable To', help='00:00 to 23:59', default=24.0, required=True)
    stopped_date = fields.Date('Stopped Date', help='Stop this mailing for this date', copy=False)
    error_message = fields.Text('Error Message', help='Message error.', copy=False)

    @api.constrains('enable_from_hour', 'enable_to_hour')
    def _constrain_enable_hour(self):
        for r in self:
            if r.enable_from_hour == 0.0 and r.enable_to_hour == 0.0:
                continue
            if r.enable_from_hour or r.enable_to_hour:
                if r.enable_from_hour >= r.enable_to_hour:
                    raise ValidationError(_('Enable From must be less than Enable To.'))
                if r.enable_from_hour < 0.0 or r.enable_to_hour < 0.0 or r.enable_from_hour > 24.0 or r.enable_to_hour > 24.0:
                    raise ValidationError(_('Please write in this format: HH:MM (Min: 00:00 - Max: 24:00)'))

    @api.constrains('connector_id', 'ws_template_id')
    def _constrain_connector_type(self):
        for r in self:
            if r.connector_id.connector_type == 'gupshup' and not r.ws_template_id.waba_template_id:
                raise ValidationError(_('Please select WABA template.'))

    @api.depends('mailing_type')
    def _compute_medium_id(self):
        '''
            :override
            :see mass_sms
        '''
        mass_ws = self.filtered(lambda m: m.mailing_type == 'whatsapp')
        for mailing in mass_ws:
            if not mailing.medium_id or mailing.medium_id != self.env.ref('whatsapp_connector_mass.utm_medium_ws'):
                mailing.medium_id = self.env.ref('whatsapp_connector_mass.utm_medium_ws').id
        return super(Mailing, self - mass_ws)._compute_medium_id()

    @api.depends('mailing_trace_ids.failure_type')
    def _compute_sms_has_iap_failure(self):
        '''
            :override
            :see mass_sms
        '''
        mass_ws = self.filtered(lambda m: m.mailing_type == 'whatsapp')
        for ws in mass_ws:
            ws.sms_has_insufficient_credit = ws.sms_has_unregistered_account = False
        return super(Mailing, self - mass_ws)._compute_sms_has_iap_failure()

    def _compute_total(self):
        mass_ws = self.filtered(lambda m: m.mailing_type == 'whatsapp')
        for mass_mailing in mass_ws:
            mass_mailing.total = len(mass_mailing.mailing_trace_ids.ids)
        return super(Mailing, self - mass_ws)._compute_total()

    def _compute_total_ws(self):
        Message = self.env['acrux.chat.message'].with_context(active_test=False)
        Conversation = self.env['acrux.chat.conversation'].with_context(active_test=False)
        for mass_mailing in self:
            if mass_mailing.mailing_type == 'whatsapp':
                total_ws = Message.search_count([('mailing_id', '=', mass_mailing.id)])
                total_ws_pend = Message.search_count([('mailing_id', '=', mass_mailing.id), ('active', '=', False)])
                mass_mailing.total_ws = total_ws
                mass_mailing.total_ws_sent = total_ws - total_ws_pend
                mass_mailing.total_ws_pend = total_ws_pend
                mass_mailing.total_ws_contact = Conversation.search_count(
                    [('chat_message_ids.mailing_id', '=', mass_mailing.id)])
            else:
                mass_mailing.total_ws = 0
                mass_mailing.total_ws_sent = 0
                mass_mailing.total_ws_pend = 0
                mass_mailing.total_ws_contact = 0

    @api.onchange('mailing_model_real')
    def onchange_ws_mailing_model_real(self):
        self.ws_template_id = False

    @api.onchange('ws_template_id')
    def onchange_ws_template_id(self):
        if self.ws_template_id:
            self.body_whatsapp = tools.html2plaintext(self.ws_template_id.body_html or '').strip()
            self.body_whatsapp_html = self.ws_template_id.body_html
        else:
            self.body_whatsapp = False
            self.body_whatsapp_html = False

    # -------------------------------------------------
    # ORM OVERRIDES
    # --------------------------------------------------

    @api.model
    def create(self, values):
        '''
            :override
            :see mass_sms
        '''
        if values.get('mailing_type') == 'whatsapp' and values.get('ws_subject'):
            values['subject'] = values['ws_subject']
        return super(Mailing, self).create(values)

    def unlink(self):
        Message = self.env['acrux.chat.message'].sudo()
        domain_search = [('mailing_id', 'in', self.ids),
                         ('msgid', '=', False),
                         ('active', '=', False)]
        Message.search(domain_search).unlink()
        return super(Mailing, self).unlink()

    def create_trace_sent(self, message):
        if not self.env.context.get('no_create_trace'):
            Trace = self.env['mailing.trace']
            for mass in self:
                Trace.create({
                    'model': mass.mailing_model_real,
                    'res_id': message.mailing_res_id,
                    'mass_mailing_id': mass.id,
                    'trace_status': 'sent',
                    'sent_datetime': fields.Datetime.now(),
                    'ws_message_id': message.id,
                    'ws_phone': '+%s' % message.contact_id.number,
                })

    def create_trace_error(self, number, record, msg=''):
        if not self.env.context.get('no_create_trace'):
            Trace = self.env['mailing.trace']
            msg = msg or _('Invalid phone')
            for mass in self:
                Trace.create({
                    'model': record._name,
                    'res_id': record.id,
                    'mass_mailing_id': mass.id,
                    'trace_status': 'error',
                    'ws_error_msg_trace': msg,
                    'ws_phone': number,
                })

    # --------------------------------------------------
    # BUSINESS / VIEWS ACTIONS
    # --------------------------------------------------

    def action_retry_failed(self):
        '''
            :override
            :see mass_sms
        '''
        mass_ws = self.filtered(lambda m: m.mailing_type == 'whatsapp')
        if mass_ws:
            mass_ws.action_retry_failed_ws()
        return super(Mailing, self - mass_ws).action_retry_failed()

    def action_retry_failed_ws(self):
        '''
            try to send messages withou failed message
        '''
        Message = self.env['acrux.chat.message']
        failed_ws = Message.search([('mailing_id', 'in', self.ids),
                                    ('msgid', '=', False),
                                    ('active', '=', False)])
        if failed_ws:
            failed_ws.write({'try_count': 0,
                             'error_msg': False})
            failed_ws.mapped('mailing_trace_ids').unlink()
        self.write({'state': 'in_queue', 'loop_count': 0})

    @api.onchange('mailing_model_id')
    def ws_on_change_mailing_model_id(self):
        '''
            Validate allowed models to set in mailing list
        '''
        for record in self.filtered(lambda r: r.mailing_type == 'whatsapp'):
            record.ws_validate_supported_models()

    def ws_validate_supported_models(self):
        '''
            Validate allowed models business logic
        '''
        self.ensure_one()
        if self.mailing_model_real not in ['crm.lead', 'event.registration',
                                           'hr.applicant', 'res.partner',
                                           'event.track', 'sale.order',
                                           'mailing.list', 'mailing.contact', 'account.move']:
            raise ValidationError(_('Option not allowed with whatsapp.'))

    def action_test(self):
        '''
            :override
            :see mass_sms
        '''
        if self.mailing_type == 'whatsapp':
            ctx = dict(self.env.context, default_mailing_id=self.id)
            view = self.env.ref('whatsapp_connector_mass.mailing_ws_test_view_form')
            return {
                'name': _('Test Whatsapp Marketing'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [[view.id, 'form']],
                'res_model': 'mailing.ws.test',
                'target': 'new',
                'context': ctx,
            }
        return super(Mailing, self).action_test()

    def action_view_to_send_ws(self):
        '''
            Return action to see all sent message.
            :return dict: odoo action
        '''
        return {
            'name': 'Whatsapp Messages',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'acrux.chat.message',
            'domain': [('mailing_id', 'in', self.ids)],
            'context': dict(self._context, create=False)
        }

    def action_view_contact_ws(self):
        '''
            Return action to see all contact.
            :return dict: odoo action
        '''
        return {
            'name': 'Whatsapp Contact',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'acrux.chat.conversation',
            'domain': [('chat_message_ids.mailing_id', '=', self.id)],
            'context': dict(self._context, create=False, active_test=False)
        }

    def action_view_traces_all(self):
        return self._action_view_traces_filtered(False)

    def _action_view_traces_filtered(self, view_filter):
        '''
            Override views for mailing.trace
            :override
            :see mass_sms
        '''
        action = super(Mailing, self)._action_view_traces_filtered(view_filter)
        if 'search_default_filter_False' in action['context']:
            action['context'].pop('search_default_filter_False')
            action['context']['search_default_state'] = 1
        if self.mailing_type == 'whatsapp':
            tree_view = self.env.ref('whatsapp_connector_mass.mailing_trace_view_tree_ws')
            form_view = self.env.ref('whatsapp_connector_mass.mailing_trace_view_form_ws')
            search_view = self.env.ref('whatsapp_connector_mass.mailing_trace_view_search_ws')
            action['views'] = [(tree_view.id, 'tree'), (form_view.id, 'form'), (search_view.id, 'search')]
        return action

    def action_put_in_queue(self):
        '''
            :override
            :see mass_sms
        '''
        mass_ws = self.filtered(lambda m: m.mailing_type == 'whatsapp')
        if mass_ws:
            mass_ids = mass_ws.with_context(not_check_is_valid=True)
            for mass_id in mass_ids:
                generate_ws = bool(mass_id.state == 'draft')
                schedule_date = mass_id.schedule_date or fields.Datetime.now()
                mass_id.write({'state': 'in_queue', 'schedule_date': schedule_date, 'loop_count': 0})
                if generate_ws:
                    mass_id.generate_ws_message()
        return super(Mailing, self - mass_ws).action_put_in_queue()

    def generate_ws_message(self):
        '''
            Generate whatsapp message to be sent, also, generate mailing.trace.
            Phone number of message are taking from:
                crm: if phone exist, phone else parter
                event.registration, hr.applicant,
                event.track, sale, partner: is taking from partner's phone
                mailing.linst or maling.contact: from phone field
        '''
        for mailing in self:
            contacts = mailing.generate_ws_message_contacts()
            if contacts:
                mailing.build_ws_messages(contacts)

    def generate_ws_message_contacts(self):
        def get_chat(mailing, partner_id):
            conn_id = mailing.connector_id
            conv_ids = partner_id.contact_ids.filtered(lambda x: x.connector_id.id == conn_id.id)
            if conv_ids:
                return conv_ids[0]
            return conv_ids

        self.ensure_one()
        mailing = self
        mailing.ws_validate_supported_models()
        res_ids = mailing._get_remaining_recipients()
        res_model = self.env[mailing.mailing_model_real].sudo()
        records = res_model.browse(res_ids)
        contacts = []
        for record in records:
            if mailing.mailing_model_real in ['event.registration', 'hr.applicant',
                                              'event.track', 'sale.order', 'res.partner', 'account.move']:
                if mailing.mailing_model_real == 'res.partner':
                    partner_id = record
                else:
                    partner_id = record.partner_id
                conv_id = get_chat(mailing, partner_id)
                contacts.append({'number': conv_id.number or partner_id.mobile or partner_id.phone, 'name': partner_id.name,
                                 'doc_name': record.name, 'record': record, 'conv_id': conv_id})
            elif mailing.mailing_model_real == 'crm.lead':
                partner_id = record.partner_id
                conv_id = get_chat(mailing, partner_id)
                name = record.contact_name or partner_id.name or ''
                number = conv_id.number or record.mobile or record.phone or partner_id.mobile or partner_id.phone or ''
                contacts.append({'number': number, 'name': name,
                                 'doc_name': record.name, 'record': record, 'conv_id': conv_id})
            elif mailing.mailing_model_real in ['mailing.list', 'mailing.contact']:
                if mailing.mailing_model_real == 'mailing.list':
                    contact_ids = record.mapped('contact_ids')
                else:
                    contact_ids = record
                conv_id = self.env['acrux.chat.conversation']
                for contact in contact_ids:
                    contacts.append({'number': contact.ws_phone_normalized,
                                     'name': contact.name or contact.ws_phone_normalized,
                                     'doc_name': '',
                                     'record': contact,
                                     'conv_id': conv_id})
        return contacts

    def action_cancel(self):
        '''
            :override
            :see mass_sms
        '''
        super(Mailing, self).action_cancel()
        out = {}
        mass_ws = self.filtered(lambda m: m.mailing_type == 'whatsapp')
        if mass_ws:
            out = mass_ws.cancel_ws_message()
        return out

    def cancel_ws_message(self):
        '''
            Cancel whatsapp mailing.
            Delete all non sent message and mailing.trace
            :return dict: odoo action, warning if messages were sent.
        '''
        out = {}
        Message = self.env['acrux.chat.message'].with_context(active_test=False)
        for mailing in self:
            message_draft = Message.search([('mailing_id', '=', mailing.id),
                                            ('msgid', '=', False)])
            all_message = Message.search_count([('mailing_id', '=', mailing.id)])
            if all_message != len(message_draft):
                out = self.env['acrux.chat.pop.message'].message(_('Caption'), _('Some messages were sent.'))
            message_draft.mapped('mailing_trace_ids').unlink()
            message_draft.unlink()
        return out

    # --------------------------------------------------
    # HOOKS / mass.mailing cron
    # --------------------------------------------------

    def action_send_mail(self, res_ids=None):
        '''
            Function called by mass.mailing cron
            :override
            :see mass_sms
        '''
        # no se envía los mailing de whatsapp para usar su propio cron
        mass_ws = self.filtered(lambda m: m.mailing_type == 'whatsapp')
        return super(Mailing, self - mass_ws).action_send_mail(res_ids=res_ids)

    @api.model
    def _process_mass_mailing_queue(self):
        return super(Mailing, self.with_context(from_mass_mailing_cron=True))._process_mass_mailing_queue()

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        ret = super(Mailing, self).search(args, offset=offset, limit=limit, order=order, count=count)
        if self.env.context.get('from_mass_mailing_cron'):
            ret = ret.filtered(lambda m: m.mailing_type != 'whatsapp' or m.state not in ['in_queue', 'sending'])
        return ret

    # --------------------------------------------------

    def midnight_utc(self):
        tz_name = self.env.context.get('tz')
        assert tz_name, 'Timezone required'
        tz = pytz.timezone(tz_name)
        naive_datetime = datetime.combine(self.local_today(), datetime.min.time())
        local_datetime = tz.localize(naive_datetime, is_dst=None)
        return local_datetime.astimezone(pytz.utc).replace(tzinfo=None)

    def local_today(self):
        assert self.env.context.get('tz'), 'Timezone required'
        return fields.Date.context_today(self)

    def check_numbers(self, max_time, pack=1):
        self.ensure_one()
        if self.connector_id.auto_valid_number and self.connector_id.connector_type == 'apichat.io':
            Message = self.env['acrux.chat.message'].with_context(active_test=False)
            Conversation = self.env['acrux.chat.conversation'].with_context(not_download_profile_picture=True)
            domain_search = [('mailing_id', '=', self.id),
                             ('contact_id.valid_number', '!=', 'yes')]
            # COUNT
            mess_ids = Message.search(domain_search, order='id')
            conv_ids = mess_ids.mapped('contact_id')
            _logger.info('--- 1 conversations pending/invalid: %s' % len(conv_ids))
            if not conv_ids:
                return {'result': 'all good'}
            conv_ids_to_check = conv_ids.filtered(lambda x: not x.valid_number)  # empty
            _logger.info('--- 1 conversations pending to check: %s' % len(conv_ids))
            if not conv_ids_to_check:
                return {'result': 'only invalid'}
            # END COUNT
            n = pack
            numbers_list = [conv_ids_to_check[i:i + n] for i in range(0, len(conv_ids_to_check), n)]
            res_model = self.env[self.mailing_model_real].sudo()
            flag = False
            for numbers_ids in numbers_list:
                if flag:
                    sleep(5)
                flag = True
                ret = self.connector_id.check_is_valid_whatsapp_number(numbers_ids, overwrite=False, raise_error=False)
                if ret.get('error'):
                    return {'result': 'error', 'error': ret.get('error')}
                numbers = ret.get('numbers', {})
                for conv_id in numbers_ids:
                    error = False
                    check = numbers.get(conv_id.number)
                    if check:
                        if check['valid']:
                            conv_id.valid_number = 'yes'
                            if not check['same']:
                                if self.mailing_model_real in ['mailing.list', 'mailing.contact']:
                                    to_update = self.env['mailing.contact'].search([
                                        ('ws_phone_normalized', '=', conv_id.number)])
                                    to_update.write({'ws_phone': '+%s' % check['number'], 'is_whatsapp': True})
                                exist = Conversation.search_count([('connector_id', '=', self.connector_id.id),
                                                                   ('number', '=', check['number'])])
                                if exist:
                                    error = _('Number already exists when trying to fix (%s)') % check['number']
                                else:
                                    conv_id.number = check['number']
                        else:
                            conv_id.valid_number = 'no'
                            error = _('Number not exist in WhatsApp (%s)') % conv_id.number
                    if error:
                        res_id = conv_id.chat_message_ids.filtered(lambda x: x.mailing_id.id == self.id)\
                            .mapped('mailing_res_id')
                        if res_id:
                            record = res_model.browse(res_id[0])
                            self.create_trace_error(conv_id.number, record, msg=error)
                self.env.cr.commit()
                if time() > max_time:
                    break

            # COUNT AGAIN
            mess_ids = Message.search(domain_search, order='id')
            conv_ids = mess_ids.mapped('contact_id')
            _logger.info('--- 2 conversations pending/invalid: %s' % len(conv_ids))
            if not conv_ids:
                return {'result': 'all good'}
            conv_ids_to_check = conv_ids.filtered(lambda x: not x.valid_number)  # empty
            _logger.info('--- 2 conversations pending to check: %s' % len(conv_ids))
            if not conv_ids_to_check:
                return {'result': 'only invalid'}
            # END COUNT
        elif self.connector_id.connector_type == 'gupshup':
            Message = self.env['acrux.chat.message'].with_context(active_test=False)
            domain_search = [('mailing_id', '=', self.id),
                             ('contact_id.is_waba_opt_in', '=', False),
                             ('contact_id.sent_opt_in', '=', False)]
            # COUNT
            mess_ids = Message.search(domain_search, order='id')
            conv_ids = mess_ids.mapped('contact_id')
            _logger.info('--- 1 conversations pending/invalid: %s' % len(conv_ids))
            if conv_ids:
                for conv_id in conv_ids[:500]:
                    conv_id.toggle_opt_in()
                    self.env.cr.commit()
                    sleep(0.2)

                # COUNT AGAIN
                mess_ids = Message.search(domain_search, order='id')
                conv_ids = mess_ids.mapped('contact_id')
            if not conv_ids:
                # check valid_number
                domain_search = [('mailing_id', '=', self.id),
                                 ('contact_id.valid_number', '=', 'no')]
                mess_ids = Message.search(domain_search, order='id')
                conv_ids_not_valid = mess_ids.mapped('contact_id')
                for conv_id in conv_ids_not_valid:
                    res_id = conv_id.chat_message_ids.filtered(lambda x: x.mailing_id.id == self.id) \
                        .mapped('mailing_res_id')
                    if res_id:
                        res_model = self.env[self.mailing_model_real].sudo()
                        record = res_model.browse(res_id[0])
                        self.create_trace_error(conv_id.number, record)
                if conv_ids_not_valid:
                    return {'result': 'only invalid'}
                else:
                    return {'result': 'all good'}
            _logger.info('--- 2 conversations pending to check: %s' % len(conv_ids))
        else:
            return {'result': 'all good'}
        return dict()

    @api.model
    def _cron_check_numbers(self, minutes, connector_id=False, pack=1):
        _logger.info('--- _cron_check_numbers start (Connector: %s)' % connector_id)
        duration = minutes * 60 * 0.9
        max_time = time() + duration
        domain = []
        if connector_id:
            domain = [('connector_id', '=', connector_id)]
        domain += [('mailing_type', '=', 'whatsapp'),
                   ('state', '=', 'in_queue')]
        mailing_ids = self.search(domain, order='schedule_date asc, id asc')
        for mailing in mailing_ids:
            _logger.info('--- mailing: %s | %s | schedule: %s'
                         % (mailing.id, mailing.ws_subject, mailing.schedule_date))
            conn_id = mailing.connector_id
            if conn_id.connector_type == 'apichat.io' and not conn_id.auto_valid_number:
                mailing.state = 'sending'
                continue
            mailing = mailing.with_context(tz=conn_id.tz,
                                           lang=conn_id.company_id.partner_id.lang,
                                           allowed_company_ids=[conn_id.company_id.id])
            today = mailing.local_today()
            if mailing.stopped_date:
                if mailing.stopped_date == today:
                    _logger.info('--- mailing stop: %s' % today)
                    continue
                else:
                    _logger.info('--- mailing play: %s' % today)
                    mailing.play_stopped_mainling()
            if time() > max_time:
                break
            ret = mailing.check_numbers(max_time, pack)
            _logger.info('--- check_numbers response: %s' % ret)
            if ret.get('result') == 'all good':
                mailing.state = 'sending'
            elif ret.get('result') in ['error', 'only invalid']:
                error = ret.get('error') or _('Stopped for %s') % _('Invalid number')
                mailing.loop_count = 0
                mailing.stopped_date = mailing.local_today()
                mailing.error_message = error

    @api.model
    def _cron_send_ws(self, minutes, connector_id=False):
        duration = minutes * 60 * 0.8
        max_time = time() + duration
        for state in ['sending']:
            _logger.info('*** _cron_send_ws start: %s (Connector: %s)' % (state, connector_id))
            data = []
            if connector_id:
                data = [('connector_id', '=', connector_id)]
            data += [('mailing_type', '=', 'whatsapp'),
                     ('state', '=', state),
                     '|', ('schedule_date', '<', fields.Datetime.now()),
                     ('schedule_date', '=', False)]
            mailing = self.search(data, limit=1, order='schedule_date asc, id asc')
            if mailing and mailing.connector_id:
                conn_id = mailing.connector_id
                mailing = mailing.with_context(tz=conn_id.tz,
                                               lang=conn_id.company_id.partner_id.lang,
                                               allowed_company_ids=[conn_id.company_id.id])
                today = mailing.local_today()
                if mailing.stopped_date and mailing.stopped_date == today:
                    _logger.info('*** mainling in stop: %s' % today)
                    continue
                if mailing.connector_status:
                    now = fields.Datetime.now()
                    now_time = date2local(mailing, now)
                    now_float = now_time.hour + now_time.minute / 60.0
                    if mailing.enable_from_hour <= now_float <= mailing.enable_to_hour:
                        mailing.action_send_ws(duration, max_time)
                    else:
                        _logger.info('*** _cron_send_ws mainling ignored for enable hour')
                else:
                    mailing.handler_message_exception(old_message=False, sent_count=0, e=False)
            if time() > max_time:
                _logger.info('*** break _cron_send_ws')
                break
        _logger.info('*** _cron_send_ws end')

    def action_send_ws(self, duration, max_time):
        '''
            Send mailing messages
        '''
        self.ensure_one()
        Message = self.env['acrux.chat.message'].with_context(active_test=False)
        # this calc assumes, a message spends 2 seconds (min) to be sent.
        message_limit = int(duration / 2)
        if self.connector_id.connector_type == 'gupshup':
            message_limit = message_limit * 4
        domain_search = [('mailing_id', '=', self.id),
                         ('msgid', '=', False),
                         ('mailing_res_id', '!=', False),
                         ('error_msg', '=', False)]
        messages_draft = Message.search(domain_search, limit=message_limit, order='id')
        message_sent_count = Message.search_count([('mailing_id', '=', self.id),
                                                   ('msgid', '!=', False),
                                                   ('date_message', '>=', self.midnight_utc())])
        sent_count = 0
        old_message = False
        old_contac = 0
        zzz_max = {'1': (3, 6), '2': (13, 19), '3': (29, 39)}.get(self.spam_level, (3, 6))
        try:
            for message in messages_draft:
                if self.message_limit > 0 and message_sent_count + sent_count + 1 > self.message_limit:
                    self.stopped_date = self.local_today()
                    break
                old_message = message
                message.write({'active': True, 'date_message': fields.Datetime.now()})
                message.message_send()
                self.create_trace_sent(message)
                sent_count += 1
                message.env.cr.commit()
                if time() > max_time:
                    _logger.info('*** _cron_send_ws break')
                    break
                zzz = zzz_max if old_contac != message.contact_id.id else (3, 6)
                rand = randrange(min(zzz), max(zzz))
                if self.connector_id.connector_type != 'apichat.io':
                    rand = round(rand / 4, 1)
                sleep(rand)
                old_contac = message.contact_id.id
        except OperationalError as e:
            if e.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                raise e
            self.handler_message_exception(old_message, sent_count, e, trace_status='bounce')
            raise e
        except Exception as e:
            self.handler_message_exception(old_message, sent_count, e, trace_status='bounce')
            raise e
        set_done = False
        if messages_draft:
            if not Message.search([('mailing_id', '=', self.id),
                                   ('msgid', '=', False)], limit=1):
                set_done = True
        else:
            if Message.search([('mailing_id', '=', self.id)], limit=1):
                set_done = True
        if set_done:
            self.write({'state': 'done', 'sent_date': fields.Datetime.now(),
                        'error_message': False, 'stopped_date': False, 'schedule_date': False})
        _logger.info('*** _cron_send_ws sent_count = %s' % sent_count)

    def handler_message_exception(self, old_message, sent_count, e, trace_status='error'):
        self.env.cr.rollback()
        stop_mailing = False
        if e and e.args and e.args[0] == 'Message limit exceeded.':
            stop_mailing = True
        else:
            if old_message:
                if old_message.try_count < 3:
                    old_message.try_count = old_message.try_count + 1
                else:
                    old_message.error_msg = str(e)
                    old_message.mailing_trace_ids.write({'ws_error_msg_trace': str(e), 'trace_status': trace_status})
            if sent_count == 0:
                if self.loop_count < 3:
                    self.loop_count = self.loop_count + 1
                else:
                    stop_mailing = True
            else:
                self.loop_count = 0
        if stop_mailing:
            self.loop_count = 0
            self.stopped_date = self.local_today()
            self.error_message = _('Stopped for %s') % str(e)
        self.env.cr.commit()

    def play_stopped_mainling(self):
        self.write({'stopped_date': False, 'error_message': False, 'loop_count': 0})

    def build_ws_messages(self, contacts):
        '''
            Create all message for this mailing
            :return object: acrux.chat.message
        '''
        self.ensure_one()
        if not self.connector_id:
            raise UserError(_('Select a connector.'))
        if not self.body_whatsapp:
            raise UserError(_('Text body is empty.'))
        attach_init = 0
        create_text_message = True
        messages_dict = []
        if not self.ws_template_id:
            if self.attachment_ids:
                self.attachment_ids.generate_access_token()
                if self.env.context.get('no_create_trace'):
                    self.env.cr.commit()
                attach = self.attachment_ids[0]
                if attach.mimetype and (attach.mimetype.startswith('image') or attach.mimetype.startswith('video')):
                    attach_init = 1
                    create_text_message = False
                    messages_dict.append(self._build_ws_message_simple(self.body_whatsapp or '', attach))
            if create_text_message:
                messages_dict.append(self._build_ws_message_simple(self.body_whatsapp or ''))
            for attch_index in range(attach_init, len(self.attachment_ids)):
                attach = self.attachment_ids[attch_index]
                messages_dict.append(self._build_ws_message_simple('', attach=attach))
        Message = self.env['acrux.chat.message'].with_context(active_test=False)
        Conversation = self.env['acrux.chat.conversation'].with_context(not_download_profile_picture=True)
        messages_ids = self.env['acrux.chat.message']

        unique_contact = []
        for contact in contacts:
            record = contact['record']
            conv_id = contact['conv_id']
            number_cleaned = conv_id.number or self.connector_id.clean_id(contact['number'] or '')
            valid = conv_id.number or phone_format(number_cleaned, raise_error=False)
            if not valid:
                self.create_trace_error(contact['number'], contact['record'])
                continue
            if record._name in ['mailing.contact'] and (not record.is_whatsapp or not record.ws_phone_normalized):
                self.create_trace_error(contact['number'], contact['record'])
                continue
            if self.check_unique_contact and number_cleaned in unique_contact:
                self.create_trace_error(contact['number'], contact['record'], 'Message already sent to this contact.')
                continue
            else:
                if self.ws_template_id:
                    messages_dict = self._build_ws_message_template(record.id)
                unique_contact.append(number_cleaned)
                if not conv_id:
                    conv_id = Conversation.search([('connector_id', '=', self.connector_id.id),
                                                   ('number', '=', number_cleaned)])
                if not conv_id:
                    conv_id = Conversation.create({'connector_id': self.connector_id.id,
                                                   'number': number_cleaned,
                                                   'name': contact['name'],
                                                   'status': 'done'})
                if conv_id.connector_id.connector_type == 'gupshup' and not conv_id.is_waba_opt_in:
                    conv_id.mute_opt_in = True
                for msg_origin in messages_dict:
                    msg = msg_origin.copy()
                    msg['text'] = msg['text'].replace('{name}', contact['name'] or '')
                    msg['text'] = msg['text'].replace('{doc_name}', contact['doc_name'] or '')
                    msg['contact_id'] = conv_id.id
                    msg['mailing_res_id'] = record.id
                    msg_id = Message.create(msg)
                    messages_ids |= msg_id
        return messages_ids

    @api.model
    def _build_ws_parse_attach(self, msg, attac_id):
        if attac_id:
            if attac_id.mimetype.startswith('image'):
                msg['ttype'] = 'image'
            elif attac_id.mimetype.startswith('video'):
                msg['ttype'] = 'video'
            elif attac_id.mimetype.startswith('audio'):
                msg['ttype'] = 'audio'
                msg['text'] = ''
            else:
                msg['ttype'] = 'file'
                msg['text'] = ''

    def _build_ws_message_simple(self, text, attach=False):
        '''
            Return chatroom message dict style.
            :return dict
        '''
        msg = {
            'text': text,
            'from_me': True,
            'mailing_id': self.id,
            'active': False,
            'mute_notify': True,
        }
        self._build_ws_parse_attach(msg, attach)
        if attach:
            msg.update({'res_model': 'ir.attachment', 'res_id': attach.id})
        else:
            msg['ttype'] = 'text'
        return msg

    def _build_ws_message_template(self, res_id):
        Attachment = self.env['ir.attachment']
        template_id = self.ws_template_id.id
        fields_ret = ['body_html', 'attachment_ids']
        returned_fields = fields_ret + ['attachments']

        template_values = self.env['mail.template'].with_context(tpl_partners_only=True).browse(
            template_id).generate_email([res_id], fields_ret)
        res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields
                             if template_values[res_id].get(field))
        res_id_values['body'] = tools.html2plaintext(res_id_values.pop('body_html', '')).strip()
        values = res_id_values

        attachment_ids = []
        for attach_fname, attach_datas in values.pop('attachments', []):
            data_attach = {
                'name': attach_fname,
                'datas': attach_datas,
                'res_model': 'acrux.chat.message',
                'access_token': Attachment._generate_access_token(),
                'res_id': 0,
                'type': 'binary',
                'delete_old': True,
            }
            attachment_ids.append(Attachment.create(data_attach))
        for id_attac in values.pop('attachment_ids', []):
            attac_id = Attachment.search([('id', '=', id_attac)], limit=1)
            attac_id.access_token = Attachment._generate_access_token()
            attachment_ids.append(attac_id)
        for attac_id in self.attachment_ids:
            attac_id.access_token = Attachment._generate_access_token()
            attachment_ids.append(attac_id)
        msg_datas = []
        msg_base = {
            'from_me': True,
            'mailing_id': self.id,
            'active': False,
            'mute_notify': True,
        }
        if self.ws_template_id.waba_template_id:
            params = self.ws_template_id.get_waba_param(res_id)
            msg_base['template_waba_id'] = self.ws_template_id.waba_template_id.id
            msg_base['template_params'] = json.dumps({'params': params})
        if values.get('body'):
            if len(attachment_ids) == 1:
                attach = attachment_ids[0]
                if attach.mimetype and (attach.mimetype.startswith('image') or attach.mimetype.startswith('video')):
                    return [self._build_ws_message_simple(values.get('body') or '', attach)]

            txt_mes = {'ttype': 'text',
                       'text': values.get('body')}
            x = txt_mes.copy()
            x.update(msg_base)
            msg_datas.append(x)
        for attac_id in attachment_ids:
            att_mes = {'ttype': 'file',
                       'res_model': 'ir.attachment',
                       'res_id': attac_id.id,
                       'text': attac_id.name}
            self._build_ws_parse_attach(att_mes, attac_id)
            x = att_mes.copy()
            x.update(msg_base)
            msg_datas.append(x)
        if attachment_ids and self.env.context.get('no_create_trace'):
            self.env.cr.commit()
        return msg_datas
