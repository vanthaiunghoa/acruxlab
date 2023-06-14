# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ProductImport(models.TransientModel):
    _name = 'acrux.chat.bot.product.import'
    _description = 'Import Products'

    bot_id = fields.Many2one('acrux.chat.bot', string='Bot', required=True,
                             ondelete='cascade')
    product_ids = fields.Many2many('product.template', 'bot_product_import_product_rel',
                                   'import_id', 'product_id', string='Products')
    product_image_send = fields.Boolean('Send Image?', default=True)
    product_menu = fields.Boolean('Create Menu?', default=True)
    ws_template_id = fields.Many2one('mail.template', 'Template', ondelete='set null',
                                     domain="[('model', '=', 'product.template'), ('name', 'ilike', 'ChatRoom')]")

    def _get_default_values(self):
        return {
            # copia de padre
            'parent_id': self.bot_id.id,
            'connector_id': self.bot_id.connector_id.id,
            'apply_from': self.bot_id.apply_from,
            'apply_to': self.bot_id.apply_to,
            'mute_minutes': self.bot_id.mute_minutes,
            'apply_weekday': self.bot_id.apply_weekday,
            # ----
            'bot_model_id': self.env['ir.model']._get('product.template').id,
            'is_product': True,
            'ws_template_id': self.ws_template_id.id,
            'product_image_send': self.product_image_send,
        }

    def _check_requirements(self):
        if not self.bot_id:
            raise ValidationError(_('A Bot is required.'))
        if not self.product_ids:
            raise ValidationError(_('At least one product is required.'))
        if not self.ws_template_id:
            raise ValidationError(_('A Template is required.'))

    def import_records(self):
        self.ensure_one()
        self._check_requirements()

        Bot = self.env['acrux.chat.bot']
        vals = self._get_default_values()
        bot_ids = self.env['acrux.chat.bot']
        seq = 1
        child_seq = (self.bot_id.sequence or 0) + 1
        menu = []
        for product in self.product_ids:
            vals.update({
                'name': product.name,
                'product_id': product.id,
                'bot_res_id': str(product.id),
                'text_match': str(seq),
            })
            menu.append(f'{seq} > {product.name}')
            new_bot_id = Bot.create(vals)
            self.env.cr.commit()
            new_bot_id.onchange_ws_template_id()
            bot_ids |= new_bot_id
            seq += 1
            child_seq += 1
        if self.product_menu:
            self.bot_id.body_whatsapp = 'Send a number to pick a option:\n' + '\n'.join(menu)
        self.bot_id.is_product = False
        self.bot_id.onchange_is_product()
        self.bot_id.recreate_sequence()
        return self.env['acrux.chat.pop.message'].message('Message', f'{len(bot_ids)} products imported.')
