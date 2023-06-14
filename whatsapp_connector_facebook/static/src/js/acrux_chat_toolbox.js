odoo.define('whatsapp_connector_facebook.toolbox', function(require) {
"use strict";
    
var Toolbox = require('whatsapp_connector.toolbox')

/**
 * @class
 * @name Toolbox
 * @extends Toolbox
 */
Toolbox.include({
    /**
     * Condicion para deshabilitar la entrada de texto
     * @param {Object} attachment
     * @returns {Boolean}
     */
    needDisableInput: function(attachment) {
        let out
        if (this.parent.selected_conversation &&
            this.parent.selected_conversation.isOwnerFacebook()) {
            if (this.parent.selected_conversation.isWabaExtern()) {
                out = attachment.mimetype.includes('audio')
            } else {
                out = true
            }
        } else {
            out = this._super(attachment)
        }
        return out
    },
    
})

return Toolbox
})
