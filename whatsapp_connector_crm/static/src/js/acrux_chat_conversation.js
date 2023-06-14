odoo.define('whatsapp_connector_crm.conversation', function(require) {
"use strict";

var Conversation = require('whatsapp_connector.conversation');

/**
 * @class
 * @name Conversation
 * @extends whatsapp.Conversation
 */
Conversation.include({
    /**
     * @override
     * @see Conversation.init
     */
    init: function(parent, options) {
        this._super.apply(this, arguments);

        this.crm_lead_id = this.options.crm_lead_id || [false, ''];
    },

})

return Conversation
})
