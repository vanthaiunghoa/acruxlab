odoo.define('whatsapp_connector.message_metadata', function(require) {
"use strict";

const Widget = require('web.Widget')
const session = require('web.session')


/**
 * Representa metadatos de los mensajes, actualmente solo apichat
 *
 * @class
 * @name Message
 * @extends web.Widget
 */
const MessageMetadata = Widget.extend({
    template: 'acrux_chat_message_metadata',
    events: {
        'click .o_acrux_chat_message_metadata': 'openExternalLink',
    },

    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, options) {
        this._super.apply(this, arguments)

        this.parent = parent
        this.options = _.extend({}, options)
        this.context = _.extend({}, this.parent.context || {}, this.options.context)
        this.type = options.metadata_type
        this.data = JSON.parse(options.metadata_json)
        this.data.title = this.data.title || ''
        this.data.body = this.data.body || ''
    },

    openExternalLink: function() {
        if (this.data.url) {
            window.open(session.url(this.data.url), '_blank');
        }
    }
})

return MessageMetadata
})
