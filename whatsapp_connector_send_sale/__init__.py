# -*- coding: utf-8 -*-
from . import models
from odoo import api, SUPERUSER_ID
from odoo.exceptions import UserError


def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    exclude = 'whatsapp_connector_template_sale'
    modules = env['ir.module.module'].search_count([('name', '=', exclude),
                                                    ('state', 'in', ['installed', 'to install', 'to upgrade'])])
    if modules > 0:
        raise UserError('This module replaces "%s". Please uninstall first.' % exclude)
