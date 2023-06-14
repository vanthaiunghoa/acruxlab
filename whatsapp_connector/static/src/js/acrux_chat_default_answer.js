odoo.define('whatsapp_connector.default_answer', function(require) {
"use strict";

var Widget = require('web.Widget');
var core = require('web.core');

var _t = core._t;


/**
 * Se crea nueva clase DefaultAnswer, para almacenar las respuestas predeterminadas
 *
 * @class
 * @name DefaultAnswer
 * @extends web.Widget
 */
var DefaultAnswer = Widget.extend({
    template: 'acrux_chat_default_answer',
    events: {
        'click .o_acrux_chat_default_answer_send': 'sendAnswer',
    },

    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, options) {
        this._super.apply(this, arguments);

        this.parent = parent;
        this.options = _.extend({}, options);
        this.context = _.extend({}, this.parent.context || {}, this.options.context);
        this.name = this.options.name || '';
        this.sequence = this.options.sequence || '';
        this.id = this.options.id || '';
        this.text = this.options.text || '';
        this.ttype = this.options.ttype || '';
        this.res_model = this.options.res_model;
        this.res_id = this.options.res_id;
        this.env = this.parent.env
    },

    /**
     * Se envia la respuesta predeterminada al chat
     *
     * @param {Event} [event]
     * @returns {Promise<void>}
     */
    sendAnswer: async function(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
            $(event.target).prop('disabled', true);
        }
        let out = Promise.resolve()
        if (this.parent.selected_conversation &&
            this.parent.selected_conversation.isMine()) {
            let text, ttype = this.ttype;
            if (this.ttype == 'code') {
                ttype = 'text'
                text = await this._rpc({
                    model: 'acrux.chat.default.answer',
                    method: 'eval_answer',
                    args: [[this.id], this.parent.selected_conversation.id],
                    context: this.context
                })
            } else {
                if (this.text && '' != this.text) {
                    text = this.text;
                } else {
                    text = this.name;
                }
            }
            let options = {
                from_me: true, text: text, ttype: ttype,
                res_model: this.res_model, res_id: this.res_id,
            };
            out = this.parent.selected_conversation.createMessage(options);
            out.then(() => this.parent.showConversationPanel())
            out.then(() => this.parent.showChatPanel())
        } else {
            this.env.services.crash_manager.show_warning({message: _t('You must select a conversation.')})
        }
        return out.finally(() => {
            if (event) {
                $(event.target).prop('disabled', false);
            }
        });
    }

});

return DefaultAnswer;
});
