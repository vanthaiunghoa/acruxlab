# -*- coding: utf-8 -*-

from odoo import api, fields, models


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    mailing_ws_ids = fields.One2many('mailing.mailing', 'campaign_id',
                                     domain=[('mailing_type', '=', 'whatsapp')],
                                     string='Mass Whatsapp')
    mailing_ws_count = fields.Integer('Number of Mass Whatsapp',
                                      compute="_compute_mailing_ws_count")

    @api.depends('mailing_ws_ids')
    def _compute_mailing_ws_count(self):
        for campaign in self:
            campaign.mailing_ws_count = len(campaign.mailing_ws_ids)
