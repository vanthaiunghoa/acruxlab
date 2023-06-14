odoo.define('whatsapp_connector_crm.chat_classes', function(require) {
"use strict";

var chat = require('whatsapp_connector.chat_classes');

return _.extend(chat, {
    CrmLeadForm: require('whatsapp_connector_crm.crm_lead'),
});
});