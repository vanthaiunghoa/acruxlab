# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from ..tools import image2jpg
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    image_chat = fields.Image('Compressed Image', compute='compute_image_chat',
                              store=True, attachment=True)

    @api.depends('image_variant_1920', 'product_tmpl_id.image_1920')
    def compute_image_chat(self):
        for rec in self:
            if rec.image_variant_1920:
                rec.image_chat = image2jpg(self.env, rec.image_variant_1920)
                _logger.info('%s: image_variant_1920' % rec)
            elif rec.product_tmpl_id.image_1920:
                rec.image_chat = image2jpg(self.env, rec.product_tmpl_id.image_1920)
                _logger.info('%s: tmpl_id.image' % rec)
            else:
                rec.image_chat = False
                _logger.info('%s: False' % rec)
            if rec.image_chat:
                cond = [('res_model', '=', rec._name),
                        ('res_id', '=', rec.id),
                        ('res_field', '=', 'image_chat')]
                att = rec.env['ir.attachment'].sudo().search(cond, limit=1)
                if att:
                    att.generate_access_token()

    @api.model
    def _recreate_image_chat(self):
        tmpl_ids = self.env['product.template'].search([('image_1920', '!=', False)]).ids
        prod_ids = self.search(['|', ('product_tmpl_id', 'in', tmpl_ids),
                                     ('image_variant_1920', '!=', False)])
        prod_ids = prod_ids.filtered(lambda x: not x.image_chat)
        _logger.info('\n_recreate_image_chat: analyzing %s products' % len(prod_ids))
        prod_ids.compute_image_chat()
        return True

    def read_from_chatroom(self, field_read=None, load='_classic_read'):
        if not field_read:
            field_read = self.env['acrux.chat.conversation'].get_product_fields_to_read()
        return self.sudo().read(fields=field_read, load=load)
