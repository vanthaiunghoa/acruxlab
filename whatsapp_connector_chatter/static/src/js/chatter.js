odoo.define('whatsapp_connector_chatter.Chatter', function (require) {
"use strict";

var Widget = require('web.Widget');
var AcruxChatAction = require('whatsapp_connector.acrux_chat').AcruxChatAction;
var chat = require('whatsapp_connector.chat_classes');
var core = require('web.core');

var QWeb = core.qweb;

var Chatter = Widget.extend({
    
    events: {
        'click .o_acrux_chat_item': 'selectConversation',
        'click button.acrux_load_more': 'loadMoreMessage',
    },

    /**
     * @override
     * @see Widget.init
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);

        this.partner_id = null;              // partner para mostrar las conversaciones
        this.conv_ids = [];                  // conversaciones
        this.selected_conversation = null;   // conversación selecionada
        this.whatsapp_limit = 20;            // limite de mensajes por carga
        this.currency_id = null;             // moneda
        this.props = this.getParent().props; // propiedades
        this.promise_render = null;          // promesa render
        this.is_chatroom_installed = true;   // indica el que modulo chatter se instalo
        this.setPartner();
    },

    /**
     * @override
     * @see Widget.init
     */
    destroy: function() {
        this.selected_conversation = null;
        this._super.apply(this, arguments);
    },

    /**
     * Esto debería actualizar el widget
     */
    update: function (props) {
        let prom = [];
        if (this.needUpdate(props)) {
            this.props = props;
            this.setPartner();
            if (this.props.isWhatsappTalkVisible) {
                prom.push(this.queryConversation());
            }
            if (!this.currency_id) {
                prom.push(AcruxChatAction.prototype.getCurrency.apply(this))
            }
        } else {
            this.props = props;
        }
        return Promise.all(prom);
    },

    /**
     * Captura el click en ver mensajes de whatsapp
     */
    render: function() {
        let out;
        if (!this.promise_render) {
            if (this.props.isWhatsappTalkVisible) {
                out = this.renderWhatsapp();
            } else {
                this.do_hide();
                out = Promise.resolve();
            }
            this.promise_render = out.then(() => this.promise_render = null);
        } else {
            out = Promise.resolve();
        }
        return out;
    },

    /**
     * verifica si el widget necesita actualizarse o no
     */
    needUpdate: function(props) {
        let flag = false;
        if (this.props.recId == props.recId) { // el registro es el mismo
            if (this.props.modelName === 'res.partner') {
                if (this.partner_id || props.recId) {
                    if (this.partner_id && props.recId) {
                        flag = this.partner_id != props.recId;
                    } else {
                        flag = true;
                    }
                }
            } else {
                // si tiene una relacion con partner
                if (this.partner_id || props.originalState.data[props.fieldName]) {
                    if (this.partner_id && props.originalState.data[props.fieldName]) {
                        flag = this.partner_id != props.originalState.data[props.fieldName].data.id;
                    } else {
                        flag = true;
                    }
                }
            }
        } else {
            flag = true;
        }
        return flag;
    },

    /**
     * Limpia la data del widget
     */
    clearData: function() {
        // se tiene que borrar la conversacione seleccionada
        // antes de crear las nuevas conversaciones
        this.selected_conversation = null;
        if (this.conv_ids) {
            // es necesario limpiar las conversaciones viejas
            this.conv_ids.forEach(x => x.destroy());
            this.conv_ids = [];
        }
    },

    /**
     * Se encarga de renderizar todas las conversaciones
     */
    renderWhatsapp: function() {
        let $conv = $(QWeb.render('chatter.WhatsappConversation'));
        let $el = $conv.find('.o_current_chats'), promises = [];
        this.conv_ids.forEach(x => promises.push(x.appendTo($el)));
        return Promise.all(promises).then(() => {
            this.renderElement();  //limpia el div
            $conv.appendTo(this.$el);
            this.$chat_message = this.$('div.o_chat_thread');
            if (this.selected_conversation) {
                return this.renderConversation();
            }
        });
    },

    /**
     * establece el partner porque puede venir de diferentes fuentes
     */
    setPartner: function() {
        if (this.props.recId > 0) {
            if (this.props.modelName === 'res.partner') {
                this.partner_id = this.props.recId;
            } else {
                if (this.props.originalState.data[this.props.fieldName]) {
                    this.partner_id = this.props.originalState.data[this.props.fieldName].data.id
                } else {
                    this.partner_id = null;
                }
            }
        } else {
            this.partner_id = null;
        }
        this.clearData();
    },

    /**
     * Consulta las conversaciones del partner
     */
    queryConversation: function() {
        let out = Promise.resolve();
        if (this.partner_id) {
            out = this._rpc({
                model: 'acrux.chat.conversation',
                method: 'search_conversation_by_partner',
                args: [this.partner_id, this.whatsapp_limit]
            }).then(conv_ids => {
                this.clearData();
                this.conv_ids = conv_ids.map(conv => new chat.Conversation(this, conv))
                this.selected_conversation = this.conv_ids[0];
            })
        } else {
            this.clearData();
        }
        return out;
    },
    
    /**
     * Selecciona las conversaciones y muestra sus mensajes
     */
    selectConversation: function(event) {
        let id = $(event.currentTarget).data('id');
        let conv_id = this.conv_ids.find(x => x.id == id);

        if (conv_id && (this.selected_conversation == null ||
                this.selected_conversation.id != conv_id.id) ) {
            this.selected_conversation = conv_id;
            return this.renderConversation();
        }
    },
    
    /**
     * Cambia el estatus de conversacion activa y muestra los mensajes de esta
     * conversacione
     */
    renderConversation: function() {
        let $conv = this.$(`div.o_acrux_chat_item[data-id="${this.selected_conversation.id}"]`);
        this.$('.o_acrux_chat_item').removeClass('active');
        $conv.addClass('active');

        return this.renderMessage().then(() => {
            let $message = this.$chat_message[0];
            $message.scrollTop = $message.scrollHeight - $message.clientHeight;
        })
    },

    /**
     * Muestra los mensajes de una conversacion.
     * 
     */
    renderMessage: function() {
        let out;
            
        this.$chat_message.empty();
        if (this.selected_conversation.messages.length) {
            let messages = this.selected_conversation.messages;
            out = this.selected_conversation._syncLoop(0, messages, -1, this.$chat_message);
        } else {
            out = Promise.resolve();
        }
        return out.then(() => this.renderLoadBtn());
    },

    /**
     * Muestra en boton de cargar más
     */
    renderLoadBtn: function() {
        this.$chat_message.find('.acrux_load_more').remove();
        if (this.selected_conversation && 
                (this.selected_conversation.messages.length % this.whatsapp_limit) == 0 && 
                    this.selected_conversation.messages.length) {
            var btn = QWeb.render('whatsapp.connector.load_more_btn');
            this.$chat_message.prepend(btn);
        }
    },

    /**
     * Se encarga de cargar mas mensajes a la conversacion
     */
    loadMoreMessage: function() {
        let out = Promise.resolve(); 
        if (this.selected_conversation.messages.length >= this.whatsapp_limit) {
            var select = this.selected_conversation;
            out = this._rpc({
                model: 'acrux.chat.conversation',
                method: 'build_dict',
                args: [[select.id], this.whatsapp_limit, select.messages.length]
            }).then(async result => {
                if (result[0].messages) {
                    return select.addExtraClientMessage(result[0].messages).then(() => {
                        return this.renderLoadBtn();
                    })
                }
            });
        }
        return out;
    },
    
    /**
     * Por compatibilidad;
     */
    format_monetary: function(val) {
        return AcruxChatAction.prototype.format_monetary.apply(this, arguments);
    },
});


var HideChattterWhatsappTab = function (_self, _action, _options) {
    let el = document.querySelector('.o_ChatterTopbar_whatsapp');
    if (el) {
        if (el.classList.contains('o-active')) {
            el.click()
        }
    }
    return {type: 'ir.actions.act_window_close'};
}

core.action_registry.add('acrux.chat.hide_chatter_whatsapp_tag', HideChattterWhatsappTab);

return Chatter;

});
