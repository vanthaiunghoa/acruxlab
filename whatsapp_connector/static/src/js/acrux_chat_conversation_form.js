odoo.define('whatsapp_connector.conversation_form', function(require) {
"use strict";

var FormView = require('whatsapp_connector.form_view');

/**
 * Widget que maneja el formulario de Conversation
 *
 * @class
 * @name ConversationForm
 * @extends web.Widget.FormView
 * @see acrux_chat.form_view
 */
var ConversationForm = FormView.extend({
    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, options) {
        if (options) {
            options.model = 'acrux.chat.conversation';
            options.record = options.conv_info;
        }
        this._super.apply(this, arguments);
        this.parent = parent;
    },

    /**
     * @override
     * @see FormView.start
     */
    start: function() {
        return this._super().then(() => this.parent.product_search.minimize());
    },
    
    /**
     * @override
     * @see FormView.recordSaved
     * @returns {Promise}
     */
    recordSaved: function(record) {
        return this._super(record).then(() => {
            return this._rpc({
                model: this.parent.model,
                method: 'update_conversation_bus',
                args: [[this.parent.selected_conversation.id]],
                context: this.context
            });
        });
    },
});

return ConversationForm;
});
