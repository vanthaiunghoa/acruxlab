# -*- coding: utf-8 -*-

from odoo import models


class MailingMailingScheduleDate(models.TransientModel):
    _inherit = 'mailing.mailing.schedule.date'

    def set_schedule_date(self):
        '''
            Override views for mailing.trace
            :override
            :see mass_sms
        '''
        super(MailingMailingScheduleDate, self).set_schedule_date()
        mailing_ws = self.mass_mailing_id.filtered(lambda x: x.mailing_type == 'whatsapp')
        mailing_ws.generate_ws_message()
