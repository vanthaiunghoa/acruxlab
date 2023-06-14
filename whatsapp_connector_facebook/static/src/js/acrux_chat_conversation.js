odoo.define('whatsapp_connector_facebook.conversation', function(require) {
"use strict";

var Conversation = require('whatsapp_connector.conversation');

/**
 * @class
 * @name Conversation
 * @extends whatsapp.Conversation
 */
Conversation.include({
    /**
     * Devuelve si el conector pertenece a facebook
     * @returns {Boolean}
     */
    isOwnerFacebook: function() {
        return ['facebook', 'instagram', 'waba_extern'].includes(this.connector_type)
    },

    /**
     * Devuelve si el conector es waba
     * @returns {Boolean}
     */
    isWabaExtern: function() {
        return this.connector_type === 'waba_extern'
    },

    /**
     * Retorna la clase para mostrar el icono
     */
    getIconClass: function() {
        let out = ''
        if (this.connector_type === 'facebook') {
            out = 'acrux_messenger'
        } else if (this.connector_type === 'instagram') {
            out = 'acrux_instagram'
        } else if (this.connector_type === 'waba_extern') {
            out = 'acrux_whatsapp'
        } else {
            out = this._super()
        }
        return out
    }

})

return Conversation
})
