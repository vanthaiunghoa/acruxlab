odoo.define('whatsapp_connector_facebook.form_view', function(require) {
"use strict";

var FormView = require('whatsapp_connector.form_view');

/**
 * Widget para poder agregar formularios odoo en el chat 
 *
 * @class
 * @name FormView
 * @extends web.Widget
 */
FormView.include({

    /**
     * hook para procesar el context
     * @private
     */
    _context_hook: function() {
        this._super()
        if (['res.partner', 'crm.lead'].includes(this.model) &&
            this.parent.selected_conversation && 
            this.parent.selected_conversation.isOwnerFacebook() &&
            !this.parent.selected_conversation.isWabaExtern()) {
            if ('default_mobile' in this.context) {
                delete this.context.default_mobile
            }
            if ('default_phone' in this.context) {
                delete this.context.default_phone
            }
        }
    }
});

return FormView;
});
