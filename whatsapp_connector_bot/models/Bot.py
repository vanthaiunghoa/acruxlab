# -*- coding: utf-8 -*-
import random
from collections import namedtuple
from pytz import timezone
from datetime import datetime
from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError, UserError
from odoo.tools import safe_eval
from odoo.addons.whatsapp_connector.tools import date2local, get_binary_attach, phone_format

FieldsRead = ['id', 'bot_key', 'name', 'parent_id', 'connector_id', 'apply_from',
              'apply_to', 'mute_minutes', 'apply_weekday', 'text_match', 'active',
              'child_ids', 'code', 'body_whatsapp', 'ws_template_id', 'attachment_ids',
              'is_product', 'bot_res_id', 'product_image_send']
ChatBot = namedtuple('ChatBot', FieldsRead)
ChatBotM2O = namedtuple('ChatBotM2O', ['id', 'name'])


class AcruxChatBot(models.Model):
    _name = 'acrux.chat.bot'
    _description = 'ChatBot'
    _parent_name = 'parent_id'
    _rec_name = 'complete_name'
    _order = 'seq'

    seq = fields.Char('Order', compute='_get_fill_sequence', store=True)
    sequence = fields.Integer('Sequence', default=0)
    name = fields.Char('Reference', required=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True,
                                recursive=True)
    show_name = fields.Html(string='Route', compute='_compute_complete_name', store=True)
    bot_key = fields.Char('Bot Key')

    active = fields.Boolean(default=True)
    code = fields.Text('Action (Python Code)')

    child_ids = fields.One2many('acrux.chat.bot', 'parent_id', string='Child IDs', copy=False, readonly=True)
    parent_id = fields.Many2one('acrux.chat.bot', 'Parent Bot', ondelete='set null', copy=False,
                                help='Only apply when it is a response from this BOT.')
    connector_id = fields.Many2one('acrux.chat.connector', 'Connector', ondelete='set null',
                                   help='Only apply for messages in this Connector. '
                                        'Leave empty if you have one'
                                   )
    apply_from = fields.Float('Apply From', help='00:00 to 23:59', required=True, default=0.0)
    apply_to = fields.Float('Apply To', help='00:00 to 23:59', required=True, default=0.0)
    mute_minutes = fields.Integer('Mute (Minutes)', help='Number of minutes in which the automatic '
                                  'reply will not be send.')
    apply_weekday = fields.Char('In days', help='Comma separated number, where Monday is 1 and Sunday is 7. '
                                                'Leave empty for every day.')
    text_match = fields.Char('Menu Option', help='Applies only if the message equals this value. '
                                                 'Very useful for analyzing menu options.')
    body_whatsapp = fields.Text('Message')
    body_whatsapp_html = fields.Html('Html Message', related='ws_template_id.body_html',
                                     readonly=True, store=False, sanitize=False)
    attachment_ids = fields.Many2many('ir.attachment', 'acrux_bot_ir_attachments_rel',
                                      'acrux_bot_id', 'attachment_id',
                                      string='Attachments')
    ws_template_id = fields.Many2one('mail.template', 'Template', ondelete='set null',
                                     domain="[('model', '=', bot_model_real), ('name', 'ilike', 'ChatRoom')]")
    bot_model_real = fields.Char('Real Model', related='bot_model_id.model', store=True, readonly=True)
    bot_model_id = fields.Many2one('ir.model', string='Model', ondelete='set null')
    bot_res_id = fields.Char('Res id')
    is_product = fields.Boolean('Is Product?', default=False)
    product_id = fields.Many2one('product.template', string='Product', ondelete='cascade')
    product_image = fields.Binary(related='product_id.image_1920', store=False)
    product_image_send = fields.Boolean('Send Image?', default=True)

    _sql_constraints = [
        ('complete_name_uniq', 'unique (complete_name)', _('Name has to be unique.'))
    ]

    @api.depends('seq', 'name', 'parent_id.complete_name', 'product_id.name', 'sequence', 'text_match')
    def _compute_complete_name(self):
        for rec in self:
            name = '%s' % (rec.name)
            img = ''
            if rec.product_id.id:
                name = rec.product_id.name
                name = name.replace('"', '').replace('\\', '')
                img = '<img src="/web/image/product.template/%s/image_128" title="%s" alt="%s" class="acrux_m2o_avatar"/>' \
                      % (rec.product_id.id, name, name)
            if rec.text_match:
                show_name = f'{img} <b class="bot_route_match">{rec.text_match}</b> {rec.name}'
            else:
                show_name = f'{img} {rec.name}'
            parent = rec.parent_id
            while parent:
                show_name = f'<span class="bot_route">{show_name}</span>'
                parent = parent.parent_id
            x, y, z = show_name.rpartition('<span class="bot_route">')
            if y:
                show_name = x + '<span class="bot_route_end">' + z
            if not show_name.startswith('<span'):
                show_name = f'<span>{show_name}</span>'
            rec.show_name = show_name
            if rec.parent_id:
                rec.complete_name = '%s / %s' % (rec.parent_id.complete_name, name)
            else:
                rec.complete_name = name
        env = self.with_context(active_test=False)
        parent_ids = env.read_group([('parent_id', '!=', False)],
                                    fields=['parent_id', 'seq'],
                                    groupby=['parent_id'])
        for parent in parent_ids:
            last_bot_id = env.search(parent['__domain'],
                                     order='seq DESC', limit=1)
            last_bot_id.show_name = last_bot_id.show_name.replace('bot_route_end', 'bot_route_last')

    @api.depends('sequence', 'parent_id.complete_name', 'parent_id.child_ids')
    def _get_fill_sequence(self):
        for rec in self:
            rec.seq = rec.get_fill_sequence()
            for childs in rec.child_ids:
                childs._get_fill_sequence()

    def get_fill_sequence(self, level=10):
        if self.parent_id and level > 0:
            return self.parent_id.get_fill_sequence(level - 1) + '_%s' % str(self.sequence or 0).zfill(3)
        else:
            return '%s' % str(self.sequence or 0).zfill(3)

    @api.model
    def recreate_sequence(self):
        bot_ids = self.with_context(active_test=False).search([])
        for bot_id in bot_ids:
            bot_id.sequence = bot_id.sequence

    @api.constrains('code')
    def _check_python_code(self):
        for action in self.sudo().filtered('code'):
            msg = safe_eval.test_python_expr(expr=action.code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive categories.'))
        return True

    @api.constrains('apply_from', 'apply_to')
    def _constrain_apply(self):
        for r in self:
            if r.apply_from == 0.0 and r.apply_to == 0.0:
                continue
            if r.apply_from or r.apply_to:
                if r.apply_from >= r.apply_to:
                    raise ValidationError(_('Error: Apply From must be less than Apply To.'))
                if r.apply_from < 0.0 or r.apply_to < 0.0 or r.apply_from > 24.0 or r.apply_to > 24.0:
                    raise ValidationError(_('Please write in this format: HH:MM (Min.: 00:00 - Max.: 24:00)'))

    @api.model
    def _eval_answer(self, bot, message_id):
        out_model = []
        out_code = []
        if bot.is_product and bot.product_image_send:
            bot = self.browse(bot.id)
            out = bot.build_ws_message_product_images()
            for msg in out:
                msg['contact_id'] = message_id.contact_id.id
            if out:
                out_model.append(out)
        if bot.ws_template_id or bot.attachment_ids or bot.body_whatsapp:
            bot = self.browse(bot.id)  # se ignora la cache
            if bot.ws_template_id and bot.bot_res_id:
                out = list(bot.build_ws_message_template(int(bot.bot_res_id)))
            else:
                out = bot.build_ws_message_simple()
            for msg in out:
                msg['contact_id'] = message_id.contact_id.id
            if out:
                out_model.append(out)
        code = bot.code and bot.code.strip()
        if code:
            local_dict = self._get_eval_context(message_id)
            safe_eval.safe_eval(code, locals_dict=local_dict, mode='exec', nocopy=True)
            out_code = local_dict.get('ret', [])  # ret: list of dicts
            if isinstance(out_code, dict):
                out_code = [out_code]
        out = []
        if out_model:
            for x in out_model:
                out += list(map(lambda msg: {'send': msg}, x))
        if out_code:
            out += out_code
        return out

    def _get_eval_context(self, message_id):
        eval_context = {
            'env': self.env,
            'now_local': fields.Datetime.context_timestamp(self, datetime.today()),
            'datetime': safe_eval.datetime,
            'dateutil': safe_eval.dateutil,
            'timezone': timezone,
            'random_choice': random.choice,
            'email_re': tools.email_re,
            'UserError': UserError,
            'mess_id': message_id,
            'text': message_id.text,
            'search_partner': message_id.contact_id.search_partner_bot,
            'ret': []
        }
        return eval_context

    @api.model
    def _build_dict(self, bot, message_id):
        results = self._eval_answer(bot, message_id)
        if isinstance(results, dict):
            results = [results]
        ret = []
        action = dict()
        for res in results:
            if res.get('goto_and_send'):
                action = {'goto_and_send': res.get('goto_and_send')}
            if res.get('goto_and_wait'):
                action = {'goto_and_wait': res.get('goto_and_wait')}
            if res.get('next'):
                action = {'next': True}
            if res.get('exit'):
                action = {'exit': True}
            if res.get('write'):
                x = res.get('write')
                data = x.get('data')
                res_id = x.get('res_id')
                res_model = x.get('res_model')
                if data and res_id and res_model:
                    self.env[res_model].browse(res_id).write(data)
            if res.get('create'):
                x = res.get('create')
                data = x.get('data')
                res_model = x.get('res_model')
                if data and res_model:
                    self.env[res_model].create(data)
            if res.get('link_partner'):
                partner_id = res.get('link_partner', False)
                message_id.contact_id.res_partner_id = partner_id
            if res.get('create_partner'):
                conv_id = message_id.contact_id
                number_format = phone_format(conv_id.number, formatted=True, raise_error=False)
                ResPartner = self.env['res.partner'].with_context(
                    default_mobile=number_format,
                    conversation_id=conv_id.id)
                partner_id = ResPartner.create({'name': conv_id.name})
                conv_id.res_partner_id = partner_id.id
            if res.get('send_text'):
                ret.append({
                    'ttype': 'text',
                    'from_me': True,
                    'contact_id': message_id.contact_id.id,
                    'text': res.get('send_text'),
                })
            if res.get('send'):
                ret.append(res.get('send'))
        return action, ret

    def copy(self, default=None):
        self.ensure_one()
        default = default or {}
        if not default.get('name'):
            default['name'] = '%s (copy)' % self.name
        return super().copy(default)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            parent_id = vals.get('parent_id')
            bot_ids = self.with_context(active_test=False).search([], order='sequence')
            for bot_id in bot_ids:
                if parent_id and parent_id == bot_id.parent_id.id:
                    max_seq = max(bot_ids.filtered(lambda x: parent_id == x.parent_id.id).mapped('sequence') or [10])
                    seq = (max_seq + 1) if max_seq else 10
                    vals['sequence'] = seq
        self.clear_caches()
        ret = super(AcruxChatBot, self).create(vals_list)
        self.recreate_sequence()
        return ret

    def write(self, vals):
        self.clear_caches()
        ret = super(AcruxChatBot, self).write(vals)
        return ret

    def unlink(self):
        self.clear_caches()
        ret = super(AcruxChatBot, self).unlink()
        self.recreate_sequence()
        return ret

    @api.model
    @tools.ormcache()
    def get_bot_cache(self):
        match = []
        no_match = []
        bot_ids = self.with_context(active_test=False).search([])
        for x in bot_ids:
            x = x.read(FieldsRead)[0]
            if x['text_match']:
                match += [x]
            else:
                no_match += [x]
        ret = match + no_match
        return ret

    @api.model
    def get_bot_obj(self):
        ret = []
        for r in self.get_bot_cache():
            if r['parent_id']:
                r['parent_id'] = ChatBotM2O._make([r['parent_id'][0], r['parent_id'][1]])
            if r['connector_id']:
                r['connector_id'] = ChatBotM2O._make([r['connector_id'][0], r['connector_id'][1]])
            ret.append(ChatBot(**r))
        return ret

    @api.model
    def get_bot_by(self, bots, key, txt):
        rec = list(filter(lambda x: getattr(x, key) == txt, bots))
        return rec and rec[0]

    @api.model
    def get_bot_hook(self, bot, message_id):
        return True

    @api.model
    def _bot_get(self, message_id):

        log = []
        bot_log = message_id.connector_id.bot_log

        def add_log(*args):
            bot_log and log.append(' '.join('%s' % x for x in args))

        BotIds = self.get_bot_obj()

        def get_bot_by_key(txt):
            return self.get_bot_by(BotIds, 'bot_key', txt)

        messages = []
        conv_id = message_id.contact_id
        tz = message_id.connector_id.tz or self.env.context.get('tz') or self.env.user.tz
        Activities = self.env['acrux.chat.conversation.activities'].sudo().with_context(tz=tz)
        now = fields.Datetime.now()
        has_thread = len(list(filter(lambda x: x.parent_id, BotIds))) > 0

        answer_ids = False
        if has_thread:
            data = [('conversation_id', '=', conv_id.id), ('ttype', '=', 'bot_thread')]
            thread_minutes = message_id.connector_id.thread_minutes or 0
            if thread_minutes > 0:
                thread_date = fields.Datetime.subtract(now, minutes=int(thread_minutes))
                data.append(('create_date', '>', thread_date))
            in_thread_ids = Activities.search_read(data, ['rec_id'], limit=1)
            if in_thread_ids and in_thread_ids[0]['rec_id'] > 0:
                bot_id = in_thread_ids[0]['rec_id']
                answers = list(filter(lambda x: x.active and x.parent_id and x.parent_id.id == bot_id, BotIds))
                if answers:
                    answer_ids = answers
                    add_log('In Bot childs =', answer_ids and answer_ids[0].parent_id.name)
        if not answer_ids:
            answer_ids = list(filter(lambda x: x.active and not x.parent_id, BotIds))
            has_thread and add_log('In Bot childs = False')
        add_log('Order =', ' - '.join(x.name for x in answer_ids))
        if answer_ids:
            now_time = date2local(Activities, now)
            now_float = now_time.hour + now_time.minute / 60.0
            weekday = str(now_time.isoweekday())  # monday/lunes == 1
            for BotId in answer_ids:
                add_log('=>', BotId.name)
                if not self.get_bot_hook(BotId, message_id):
                    continue
                if BotId.text_match and BotId.text_match != message_id.text:
                    add_log('     < No match =', BotId.text_match)
                    continue
                if BotId.connector_id and BotId.connector_id.id != message_id.connector_id.id:
                    add_log('     < No match connector =', BotId.connector_id.name)
                    continue
                if BotId.apply_weekday and weekday not in BotId.apply_weekday:
                    add_log('     < No match weekday =', weekday, 'not in', BotId.apply_weekday)
                    continue
                if not((BotId.apply_from == 0.0 and BotId.apply_to == 0.0) or
                        (BotId.apply_from < now_float < BotId.apply_to)):
                    add_log('     < No match apply =', BotId.apply_from, '<', now_float, '<', BotId.apply_to)
                    continue
                mute_minutes = BotId.mute_minutes
                if mute_minutes:
                    mute_date = fields.Datetime.subtract(now, minutes=int(mute_minutes))
                    mute_act = Activities.search_count([('conversation_id', '=', conv_id.id),
                                                       ('ttype', '=', 'bot_mute'),
                                                       ('rec_id', '=', BotId.id),
                                                       ('create_date', '>', mute_date)])
                    if mute_act:
                        add_log('     < MUTE:', '+ %s minutes' % mute_minutes)
                        continue
                    Activities.create({'conversation_id': conv_id.id,
                                       'ttype': 'bot_mute',
                                       'rec_id': BotId.id})
                thread_id = False
                action, messages = self._build_dict(BotId, message_id)
                add_log('     action =', action)
                if action.get('goto_and_send'):
                    thread = get_bot_by_key(action.get('goto_and_send'))
                    if thread.child_ids:
                        thread_id = thread
                        add_log('     <= Stop and exec Bot =', thread_id.name)
                    else:
                        add_log('     < WARN: Ok, send, but I can\'t wait here (Bot without childs)')
                    _not_used, mess_add = self._build_dict(thread, message_id)
                    if mess_add:
                        messages += mess_add
                elif action.get('goto_and_wait'):
                    thread = get_bot_by_key(action.get('goto_and_wait'))
                    if thread.child_ids:
                        thread_id = thread
                        add_log('     <= Stop and wait in Bot =', thread_id.name)
                    else:
                        add_log('     < WARN: I can\'t wait here (Bot without childs)')
                elif action.get('next'):
                    add_log('     < Go to next Bot. No send message.')
                    continue
                elif BotId.child_ids:
                    if action.get('exit'):
                        add_log('     <= Exit, No exec childs')
                    else:
                        add_log('     <= Wait childs')
                        thread_id = BotId

                if thread_id:
                    Activities.create({'conversation_id': conv_id.id,
                                       'ttype': 'bot_thread',
                                       'rec_id': thread_id.id})
                else:
                    add_log('     <= EXIT')
                    if has_thread:
                        Activities.search([('conversation_id', '=', conv_id.id),
                                           ('ttype', '=', 'bot_thread'),
                                           ]).unlink()
                break
        if log:
            add_log('SEND', len(messages), 'message')
            self.env['acrux.chat.bot.log'].sudo().create({
                'conversation_id': conv_id.id,
                'text': message_id.text,
                'bot_log': '\n'.join(log),
            })
        return messages

    @api.model
    def bot_clean(self, conv_id):
        self.env['acrux.chat.conversation.activities'].sudo().\
            search([('conversation_id', '=', conv_id)]).unlink()

    @api.onchange('ws_template_id')
    def onchange_ws_template_id(self):
        if self.ws_template_id:
            self.body_whatsapp = tools.html2plaintext(self.ws_template_id.body_html or '').strip()
        else:
            self.body_whatsapp = False

    @api.onchange('bot_model_real')
    def onchange_ws_bot_model_real(self):
        self.ws_template_id = False

    @api.onchange('product_id')
    def onchange_product_id(self):
        for record in self:
            if record.product_id:
                record.bot_res_id = str(record.product_id.id)
                record.bot_model_id = self.env['ir.model']._get('product.template').id
            else:
                record.bot_res_id = False
                record.bot_model_id = False

    @api.onchange('is_product')
    def onchange_is_product(self):
        for record in self:
            if not record.is_product:
                record.bot_res_id = False
                record.ws_template_id = False
                record.product_id = False

    def build_ws_message_product_images(self):
        self.ensure_one()
        messages_dict = []
        if self.is_product and self.product_id and self.product_image_send:
            attach = False
            prod_id = self.product_id.product_variant_id
            image_field = False
            for image_f in ['image_chat', 'image_256']:
                if hasattr(prod_id, image_f):
                    field_image = getattr(prod_id, image_f)
                    if field_image:
                        image_field = image_f
                        break
            if image_field:
                attach = get_binary_attach(self.env, 'product.product', prod_id.id, image_field,
                                           fields_ret=['mimetype'])
                # TODO: image_chat no guarda nombre archivo
                # mimetype = attach and attach['mimetype']
                # if mimetype:
                #     ext = mimetype.split('/')
                #     if len(ext) == 2:
                #         filename = secure_filename('%s.%s' % (prod_id.display_name, ext[1]))

            if attach.get('id'):
                msg = {
                    'text': self.product_id.display_name,
                    'from_me': True,
                    'ttype': 'image',
                    'res_id': attach.get('id'),
                    'res_model': 'ir.attachment',
                }
                messages_dict.append(msg)
        return messages_dict

    def build_ws_message_simple(self):
        self.ensure_one()

        attach_init = 0
        create_text_message = True
        messages_dict = []
        if not self.ws_template_id:
            if self.attachment_ids:
                self.attachment_ids.generate_access_token()
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
        return messages_dict

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
        }
        self._build_ws_parse_attach(msg, attach)
        if attach:
            msg.update({'res_model': 'ir.attachment', 'res_id': attach.id})
        else:
            msg['ttype'] = 'text'
        return msg

    def build_ws_message_template(self, res_id):
        self.ensure_one()

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
        msg_base = {'from_me': True}
        if values.get('body'):
            txt_mes = {'ttype': 'text', 'text': values.get('body')}
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
        if attachment_ids:
            self.env.cr.commit()
        return reversed(msg_datas)

    def import_product(self):
        ctx = self.with_context(default_bot_id=self.id)
        return {
            'name': _('Import Products'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'acrux.chat.bot.product.import',
            'target': 'new',
            'context': ctx.env.context
        }
