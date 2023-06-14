# -*- coding: utf-8 -*-
from odoo import models, fields, api
from ..tools import phone_info, clean_number


class ResPartner(models.Model):
    _inherit = 'res.partner'

    contact_ids = fields.One2many('acrux.chat.conversation', 'res_partner_id',
                                  string='ChatRoom', copy=False)
    # Just for searching, you may have extra or duplicate area code.
    conv_standard_numbers = fields.Char('Standard numbers',
                                        compute='_compute_conv_standard_numbers',
                                        store=True,
                                        help='Standard number comma separated to search from conversation')

    @api.model
    def default_get(self, default_fields):
        """ Set default Image and Country from phone code """
        ctx = dict(self.env.context)
        conversation_id = self.env.context.get('conversation_id')
        if conversation_id:
            conv_id = self.env['acrux.chat.conversation'].search([('id', '=', conversation_id)])
            if conv_id.image_128:
                ctx['default_image_1920'] = conv_id.image_128
        default_phone = clean_number(self.env.context.get('default_phone') or '')
        default_mobile = clean_number(self.env.context.get('default_mobile') or '')
        mobile = default_mobile or default_phone
        default_country_id = self.env.context.get('default_country_id')
        if not default_country_id and mobile:
            _phone_code, _number, country_id = phone_info(self.env, mobile)
            if country_id:
                ctx['default_country_id'] = country_id.id
        return super(ResPartner, self.with_context(ctx)).default_get(default_fields)

    @api.depends('mobile', 'phone', 'country_id')
    def _compute_conv_standard_numbers(self):

        def parse_num(rec, num):
            country = rec.country_id or rec.company_id.country_id
            out = clean_number(num)
            if country:
                out = '%s%s' % (country.phone_code, out)
            return out.strip() if out else False

        for record in self:
            numbers = False
            if record.mobile:
                number = parse_num(record, record.mobile)
                if number:
                    numbers = number
            if record.phone:
                number = parse_num(record, record.phone)
                if number:
                    if numbers:
                        if number in numbers:
                            pass
                        elif numbers in number:
                            numbers = number
                        else:
                            numbers = '%s,%s' % (number, numbers)
                    else:
                        numbers = number
            numbers = record._compute_conv_standard_numbers_hook(numbers)
            record.conv_standard_numbers = numbers or False

    def _compute_conv_standard_numbers_hook(self, numbers):
        return numbers

    def _get_name(self):
        name = super(ResPartner, self)._get_name()
        if self.env.context.get('show_and_search_numbers') and (self.mobile or self.phone):
            numbers = '%s, %s' % (self.mobile or '', self.phone or '')
            name = "%s ‒ %s" % (name, numbers.strip(', '))
        return name

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if name and self.env.context.get('show_and_search_numbers'):
            args = args or []
            args = ['|', '|',
                    ('display_name', operator, name),
                    ('conv_standard_numbers', operator, name),
                    ('email', operator, name)] + args
            return self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return super(ResPartner, self)._name_search(name, args=args, operator=operator,
                                                    limit=limit, name_get_uid=name_get_uid)
