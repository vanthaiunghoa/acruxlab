odoo.define('whatsapp_connector.conversation', function(require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var Message = require('whatsapp_connector.message');
var session = require('web.session');
var framework = require('web.framework');

var QWeb = core.qweb;

/**
 * Representa el modelo de conversación.
 *
 * @class
 * @name Conversation
 * @extends web.Widget
 */
var Conversation = Widget.extend({
    template: 'acrux_chat_conversation',

    events: {
        'click .acrux_close_conv': 'close',
    },

    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, options) {
        this._super.apply(this, arguments);

        this.parent = parent;
        this.options = _.extend({}, options);
        this.context = _.extend({ message_from_chatroom: true }, this.parent.context || {}, this.options.context);
        this.count_new_msg = 0;
        this.session = session;
        
        this.update(this.options);
        this.setMessages(this.options.messages);
    },

    /**
     * @override
     * @see Widget.start
     */
    start: function() {
        return this._super().then(() => this._initRender());
    },

    /**
     * actualiza los datos de la conversacion
     *
     * @param {Object} options Datos de la conversacion
     */
    update: function(options) {
        this.id = options.id || 0;
        this.name = options.name || '';
        this.number_format = options.number_format;
        this.status = options.status || 'new';
        this.border_color = options.border_color || '#FFFFFF';
        this.image_url = options.image_url;
        this.team_id = options.team_id || [false, ''];
        this.res_partner_id = options.res_partner_id || [false, ''];
        this.agent_id = options.agent_id || [false, ''];
        this.connector_id = options.connector_id || [false, ''];
        this.connector_type = options.connector_type || '';
        this.show_icon = options.show_icon || false;
        this.allow_signing = options.allow_signing || false;
        this.assigned = options.assigned || false;
        this.updateMessages(options.messages || [])
    },

    /**
     * Hace trabajos de render
     *
     * @private
     * @returns {Promise} Para indicar que termino
     */
    _initRender: function() {
        // numero de mensajes nuevos
        this.$number_new_msg = this.$('.o_number_new_msg');
        this.$('.acrux_image_perfil').css('box-shadow', '0 0 5px 2px ' + this.border_color);
        this.$number_new_msg.addClass('o_hidden');
        if (this.parent.selected_conversation == this){
            this.$el.addClass('active');
        }
        this.$agent = this.$('.o_acrux_agent');
        return Promise.resolve();
    },

    /**
     * @override
     * @see Widget.destroy
     */
    destroy: function() {
        if (this.parent.selected_conversation && this == this.parent.selected_conversation) {
            this.parent.$chat_title.html('');
            this.parent.$chat_message.html('');
        }
        return this._super.apply(this, arguments);
    },

    /**
     * Establece los mensajes.
     * 
     * @param {Array<Message|Object>} messages
     * @returns {Promise}
     */
    setMessages: function(messages) {
        let out = Promise.resolve()
        this.messages_ids = new Set();
        if (this.messages) {
            this.messages.forEach(x => x.destroy());
            this.parent.$chat_message.html('');
        }
        if (messages && messages instanceof Array) {
            if (messages.length > 0) {
                if (messages[0] instanceof Message) {
                    this.messages = messages;
                    this.messages.forEach(x => this.messages_ids.add(x.id));
                } else {
                    this.messages = [];
                    out = this.addClientMessage(messages);
                }
            } else {
                this.messages = [];
            }
        } else {
            this.messages = [];
        }
        return out
    },

    /**
     * Agrega un mensaje enviado por el usario odoo.
     *
     * @param {Message} msg Mensaje para agregar.
     */
    addCompanyMessage: function(msg) {
        if (!this.messages_ids.has(msg.id)) {
            if (this.messages.length) {
                let last_msg = this.messages[this.messages.length - 1];
                if (last_msg.getDate() != msg.getDate()) {
                    this.parent.$chat_message.append(msg.getDateTmpl());
                }
            } else {
                this.parent.$chat_message.append(msg.getDateTmpl());
            }
            this.messages.push(msg);
            msg.appendTo(this.parent.$chat_message).then(() => {
                if (this.needScroll()) {
                    this.scrollConversation();
                }
            })
        }
    },

    /**
     * Muestra todos los mensajes.
     *
     * @returns {Promise} Se resuelve cuandos termina de mostrar los mensajes
     */
    showMessages: function() {
        let conv_title = QWeb.render('acrux_chat_conv_title', { conversation: this });
        let def, $el = this.parent.$chat_message;

        this.parent.$chat_title.html(conv_title);
        $el.empty();
        if (this.messages.length) {
            def = this._syncLoop(0, this.messages, -1, $el).then(() => {
                setTimeout(() => this.scrollConversation(), 200);
            });
        } else {
            def = Promise.resolve();
        }
        this.$el.addClass('active');
        if (this.isMine()) {
            this.messageSeen();  // marca mensajes como visto
        }
        this.assigned = false;
        this.$('.o_acrux_assigned_conv').remove();
        return def;
    },

    /**
     * Agrega mensajes que viene del bus.
     *
     * @param {Array<Object>} messages Mensajes que se agregan.
     * @returns {Promise} Se resuelve cuandos termina de mostrar los mensajes
     */
    addClientMessage: function(messages) {
        let show = (this.parent.selected_conversation &&
            this.parent.selected_conversation.id == this.id);
        let def, $el = this.parent.$chat_message;
        if (messages) {
            messages = messages.map(r => new Message(this, r));
            messages = messages.filter(r => !this.messages_ids.has(r.id));
            if (show && messages.length) {
                def = this._syncLoop(0, messages, this.messages.length - 1, $el).then(() => {
                    // se espera a que se muestre el último mensaje para hacer scroll
                    if (this.needScroll()) {
                        this.scrollConversation();
                    }
                });
            }
            messages.forEach(r => {
                this.messages.push(r);
                this.messages_ids.add(r.id);
            });
        }
        return def ? def : Promise.resolve();
    },

    /**
     * Se agregan mensajes luego de consultarlos al servidor, la función se llama
     * cuando se hace scroll en la conversación
     *
     * @param {Array<Object>} messages Mensajes que se agregan.
     * @returns {Promise} Se resuelve cuandos termina de mostrar los mensajes
     */
    addExtraClientMessage: function(messages) {
        let show = (this.parent.selected_conversation &&
            this.parent.selected_conversation.id == this.id);
        let def = Promise.resolve(), $el = $('<div>');
        if (messages) {
            messages = messages.map(r => new Message(this, r));
            messages = messages.filter(r => !this.messages_ids.has(r.id));
            if (show) {
                framework.blockUI();
                def = this._syncLoop(0, messages, -1, $el).then(() => {
                    if (messages.length) {
                        let last_msg = messages[messages.length - 1], first_msg;
                        if (this.messages.length) {
                            first_msg = this.messages[0];
                            if (first_msg.getDate() == last_msg.getDate()) {
                                if (first_msg.$el.prev().hasClass('o_acrux_date')) {
                                    first_msg.$el.prev().remove();
                                }
                            }
                        }
                        this.parent.$chat_message.prepend($el.contents())
                        messages.forEach(x => {
                            if (x.isAttachmentComponent()) {
                                x.res_model_obj.__callMounted();
                            }
                        });
                        last_msg.$el[0].scrollIntoView({block: 'nearest', inline: 'start' });
                    }
                }).finally(() => framework.unblockUI());
            }
            if (messages.length) {
                def.then(() => {
                    messages.forEach(r => this.messages_ids.add(r.id));
                    this.messages = messages.concat(this.messages);
                });
            }
        }
        return def;
    },

    /**
     * Ciclo recursivo sincronizado.
     *
     * @param {Number} i Indice actual
     * @param {Array<Message>} arr Array a mostrar
     * @param {Number} last_index Indice del último mensaje
     * @param {Jquery} $el Donde se mostrará
     * @returns {Promise} Del último mensaje mostrado 
     */
    _syncLoop: function(i, arr, last_index, $el) {
        let out;
        if (i < arr.length) {
            out = this._syncShow(i, arr, last_index, $el).then(() =>
                this._syncLoop(i + 1, arr, last_index, $el))
        } else {
            out = Promise.resolve();
        }
        return out;
    },

    /**
     * Sincroniza como se muestran los mensajes en el chat, para conservar el
     * orden, funciona con Deffered para organizarse.
     *
     * @private
     * @param {Number} i Indice del mensaje que se va a mostrar
     * @param {Array<Message>} arr Array donde esta el mensaje que se va a mostrar
     * @param {Number} last_index Indice del último mensaje
     * @param {Jquery} $el Donde se mostrará
     * @returns {Promise} Del mensaje que se va a mostrar
     */
    _syncShow: function(i, arr, last_index, $el) {
        let out_def, r = arr[i];
        if (i) {
            if (r.getDate() != arr[i - 1].getDate()) {
                $el.append(r.getDateTmpl());
            }
            out_def = r.appendTo($el);
        } else {
            if (last_index >= 0) {
                if (this.messages[last_index].getDate() != r.getDate()) {
                    $el.append(r.getDateTmpl())
                }
            } else {
                $el.append(r.getDateTmpl());
            }
            out_def = r.appendTo($el)
        }
        return out_def;
    },

    /**
     * Se agrega motivos de error a los mensajes y se muestra.
     *
     * @param {Array<Object>} messages Mensajes con error.
     * @returns {Array<Message>} Lista de mensaje con error.
     */
    setMessageError: function(messages) {
        let out = [];
        if (messages && this.messages.length) {
            let show = (this.parent.selected_conversation &&
                this.parent.selected_conversation.id == this.id);
            messages.forEach(r => {
                let msg = this.messages.find(x => x.id == r.id);
                if (msg) {
                    out.push(msg);
                    msg.setErrorMessage(r.error_msg);
                    if (show) {
                        msg.replace();
                    }
                }
            });
        }
        return out;
    },

    /**
     * Actualiza los datos de los mensajes
     *
     * @param {Array<Object>} messages Mensajes a actualizar
     * @returns {void}
     */
    updateMessages: function(messages) {
        if (messages && this.messages && this.messages.length) {
            let show = (this.parent.selected_conversation &&
                this.parent.selected_conversation.id == this.id);
            messages.forEach(r => {
                let msg = this.messages.find(x => x.id == r.id);
                if (msg) {
                    msg.update(r)
                    if (show) {
                        msg.replace();
                    }
                }
            })
        }
    },

    /**
     * Se sincroniza mensajes antiguos en la conversación.
     */
    syncMoreMessage: function() {
        if (this.messages.length >= 22) {
            this._rpc({
                model: 'acrux.chat.conversation',
                method: 'build_dict',
                args: [[this.id], 22, this.messages.length],
                context: this.context,
            }).then(result => {
                this.addExtraClientMessage(result[0].messages);
            });
        }
    },

    /**
     * Se verifica la posición del scroll, si esta cerca de la base retorna true
     *
     * @returns {Boolean} Necesita hacer scroll.
     */
    needScroll: function() {
        return this.calculateScrollPosition() >= 0.75;
    },

    /**
     * Calcula la posición en porcentaje del scroll
     *
     * @returns {Number} Numero flotante entre 0 y 1 
     */
    calculateScrollPosition: function() {
        let scroll_postion = this.parent.$chat_message.height();
        scroll_postion += this.parent.$chat_message.scrollTop();
        return scroll_postion / this.parent.$chat_message[0].scrollHeight;
    },

    /**
     * Hace scroll hacia el mensaje más nuevo.
     */
    scrollConversation: function() {
        if (this.parent.$chat_message.children().length) {
            let element = this.parent.$chat_message.children().last();
            if (element.children().length) {
                element = element.children().last();
            }
            element[0].scrollIntoView({block: 'nearest', inline: 'start' });
        }
    },

    /**
     * Incrementa el número de mensajes nuevos.
     */
    incressNewMessage: function() {
        this.count_new_msg += 1;
        if (this.$number_new_msg) {
            if (this.count_new_msg >= 1) {
                this.$number_new_msg.removeClass('o_hidden');
            }
            this.$number_new_msg.text(this.count_new_msg);
        }
    },

    /**
     * Crea un objeto Message y lo envía al servidor.
     *
     * @param {Object} options Datos del mensaje
     * @returns {Promise} La promesa retorna el mensaje
     */
    createMessage: function(options) {
        let msg = new Message(this, options);
        let json_data = msg.export_to_vals();
        if (options.custom_field) {
            json_data[options.custom_field] = true;
        }
        return new Promise((resolve, reject) => {
            this._rpc({
                model: 'acrux.chat.conversation',
                method: 'send_message',
                args: [[this.id], json_data],
                context: this.context,
            }).then(result => {
                msg.update(result[0]);
                this.addCompanyMessage(msg);
                resolve(msg);
            }, result => {
                reject(result);
            });
        });
    },

    /**
     * Marca mensaje con leídos y envía petición al servidor.
     * La petición es asíncrona
     */
    messageSeen: function() {
        this._rpc({
            model: 'acrux.chat.conversation',
            method: 'conversation_send_read',
            args: [[this.id]],
            context: this.context,
        }, {
            shadow: true
        })
        this.count_new_msg = 0;
        this.$number_new_msg.addClass('o_hidden');
    },

    /**
     * Retonar si una conversacion la estoy atendiendo yo
     *
     * @returns {Boolean}
     */
    isMine: function() {
        return this.status == 'current' && this.agent_id && this.agent_id[0] == session.uid;
    },

    /**
     * Retorna la clase para mostrar el icono
     */
    getIconClass: function() {
        let out = ''
        if (['apichat.io', 'chatapi', 'gupshup'].includes(this.connector_type)) {
            out = 'acrux_whatsapp'
        }
        return out
    },

    /**
     * Borra una conversacion de chatroom
     */
    close: function() {
        this.parent.deleteConversation({id: this.id})
    }
})

return Conversation
})
