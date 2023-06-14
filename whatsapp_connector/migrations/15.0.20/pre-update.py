# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.warning("\n**** Pre update whatsapp_connector from version %s to 15.0.20 ****" % version)

    ''' acrux.chat.message event selection '''
    cr.execute("""UPDATE ir_attachment SET public='t' WHERE res_model = 'acrux.chat.message'""")
