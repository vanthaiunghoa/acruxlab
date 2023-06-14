odoo.define('whatsapp_connector.toolbox', function(require) {
"use strict";

require('@whatsapp_connector/components/toolbox')
const { getMessagingComponent } = require('@mail/utils/messaging_component');
const ToolBoxComponent = getMessagingComponent('ToolBoxComponent')

var Widget = require('web.Widget');
var core = require('web.core');
var Emojis = require('whatsapp_connector.emojis');
var session = require('web.session');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var BooleanToggle = require('web.basic_fields').BooleanToggle;

var QWeb = core.qweb;
var _t = core._t;


/**
 * Representa la entrada para la conversación, maneja, el envio de mensajes 
 * y documentos adjuntos
 *
 * @class
 * @name ToolBox
 * @extends Widget
 */
var ToolBox = Widget.extend(StandaloneFieldManagerMixin, {
    template: 'acrux_chat_toolbox',
    events: {
        "click .o_chat_toolbox_send": "sendMessage",
        "keypress .o_chat_toolbox_text_field": "onKeypress",
        "keydown .o_chat_toolbox_text_field": "onKeydown",
        "paste .o_chat_toolbox_text_field": "onPaste",
        "click .o_chat_button_add_attachment": "clickAddAttachment",
        "click .o_attachment_delete": "deleteAttachment",
        "click .o_chat_button_emoji": "toggleEmojis",
        "click span.o_acrux_emoji": "addEmoji",
        "change input.o_input_file": "changeAttachment",
        "click .o_attachment_view": "viewAttachment",
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
        
        StandaloneFieldManagerMixin.init.call(this);
        
        this.signing_active = this.options.signing_active || false;
    },

    /**
     * @override
     * @see Widget.willStart
     */
    willStart: function() {
        return this._super()
        .then(() => this.getUserPreference())
        .then(() => this.processUserPreference());
    },

    /**
     * @override
     * @see Widget.start
     */
    start: function() {
        return this._super().then(() => this._initRender());
    },

    /**
     * Hace trabajos de render
     *
     * @private
     * @returns {Promise} Para indicar que termino
     */
    _initRender: function() {
        let classes = ['o_chat_toolbox_done', 'o_chat_toolbox_container',
                       'o_chat_toolbox_send', 'o_chat_button_add_attachment',
                       'o_chat_button_emoji', 'o_chat_toolbox_user_preference']
        classes = '.' + classes.join(', .')
        this.$input = this.$('.o_chat_toolbox_text_field');
        this.$attachment_button = this.$('.o_chat_button_add_attachment');
        this.$attachment_zone = this.$('.o_toolbox_file_uploader');
        this.$other_inputs = this.$(classes);
        this.$write_btn = this.$('.o_chat_toolbox_write');
        this.$write_btn.click(() => this.blockClient());
        this.$send_btn = this.$('.o_chat_toolbox_send')
        this.$('.o_chat_toolbox_done').click(() => this.releaseClient());
        this.$input.on('input', function () {
            this.style.height = '15px';
            this.style.height = (this.scrollHeight) + 'px';
        });
        this.$emoji_btn = this.$('.o_chat_button_emoji')
        let emoji_html = QWeb.render('acrux_chat_emojis');
        let emoji_list = Emojis.data.map(emoji => `<span data-source="${emoji}" class="o_acrux_emoji">${emoji}</span>`)
        this.$el.popover({
            trigger: 'manual',
            animation: true,
            html: true,
            title: function () {
                return 'nada';
            },
            container: this.$el,
            placement: 'top',
            content: `<div class="o_acrux_emoji_container">${emoji_list.join('\n')}</div>`,
            template: emoji_html,
        }).on('inserted.bs.popover', () => {
            setTimeout(() => this.fix_popover_position(), 20);
        });
        $(window).resize(() => {
            this.fix_popover_position()
        })
        this.$user_preference = this.$('.o_chat_toolbox_user_preference')
        this.$message_signing = this.$('.o_chat_toolbox_message_signing')
        this.$toolbox_container = this.$('.o_chat_toolbox_container')
        this.$write_done_btn = this.$('.o_chat_write_done_btn')
        return Promise.resolve()
            .then(() => this.signingWidget.appendTo(this.$message_signing))
    },

    /**
     * @override
     */
    destroy: function() {
        if (this.component) {
            this.component.destroy();
            this.component = undefined;
        }
        return this._super.apply(this, arguments);
    },

    /**
     * Cuando se termina de adjuntar el dom
     */
    on_attach_callback: function() {
        if (this.component) {
            return;
        }
        let props = {parent_widget: this};
        this.component = new ToolBoxComponent(null, props);
        this.component.mount(this.$attachment_zone[0]);
    },

    /**
     * Toma una conversación para ser atendida por el cliente. Si la conversacion
     * puede ser tomada se mueve de sección sino se borra.
     *
     * @returns {Promise}
     */
    blockClient: function() {
        let out;
        if (this.parent.selected_conversation) {
            out = this._rpc({
                model: this.parent.model,
                method: 'block_conversation',
                args: [[this.parent.selected_conversation.id]],
                context: this.context
            }).then(conv => {
                this.$write_btn.addClass('o_hidden');
                this.$other_inputs.removeClass('o_hidden');
                this.check_component_visibility();
                this.parent.selected_conversation.update(conv[0]);
                this.parent.selected_conversation.showMessages();
                this.parent.selected_conversation.prependTo(this.parent.$current_chats);
                this.parent.selected_conversation.$el.addClass('active');
                this.parent.tabsClear();
            }, () => {
                if (this.parent.selected_conversation.status == 'new') {
                    this.parent.removeSelectedConversation()
                }
            });
        } else {
            out = Promise.reject();
        }
        return out;
    },

    /**
     * Libera una conversación
     *
     * @returns {Promise}
     */
    releaseClient: function() {
        let out;
        if (this.parent.selected_conversation &&
            this.parent.selected_conversation.isMine()) {
            out = this._rpc({
                model: this.parent.model,
                method: 'release_conversation',
                args: [[this.parent.selected_conversation.id]],
                context: this.context
            }).then(() => {
                this.parent.removeSelectedConversation();
                this.parent.showConversationPanel();
            });
        } else {
            out = Promise.reject();
        }
        return out;
    },

    /**
     * Muestra el toolbox si la conversación es "current"
     * @override
     */
    do_show: function() {
        this._super();
        if (this.parent.selected_conversation) {
            if (this.parent.selected_conversation.isMine()) {
                this.$write_btn.addClass('o_hidden');
                this.$other_inputs.removeClass('o_hidden');
                this.check_component_visibility();
            } else  {
                if (this.parent.selected_conversation.status !== 'current') {
                    this.$write_btn.removeClass('o_hidden');
                } else {
                    this.$write_btn.addClass('o_hidden');
                }
                this.$other_inputs.addClass('o_hidden');
                if (this.component && this.component.attachment.value) {
                    this.component._onAttachmentRemoved({})
                }
            }
        } else {
            this.$write_btn.removeClass('o_hidden');
            this.$other_inputs.addClass('o_hidden');
            if (this.component && this.component.attachment.value) {
                this.component._onAttachmentRemoved({})
            }
        }
        this.$el.popover("hide")
    },

    /**
     * Revisa la visibilidad de los componentes.
     */
    check_component_visibility: function() {
        if (this.parent.selected_conversation.allow_signing) {
            this.$message_signing.removeClass('o_hidden');
        } else {
            this.$message_signing.addClass('o_hidden');
        }
    },

    /**
     * Funcion llamada al presionar clic en enviar o presionar enter. 
     * Se encarga de decidir el tipo del mensaje y los datos que contendrá éste,
     * el mesnaje es enviado al servidor y mostrado en la conversación
     * @param {Event} [event] Evento
     *
     * @returns {Promise<Message>}
     */
    sendMessage: async function(event) {
        this.$input.prop('disabled', true);
        this.$send_btn.prop('disabled', true);
        let out = Promise.resolve();
        let options = { from_me: true }
        let text = this.$input.val().trim();
        
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        if ("" != text) {
            options.ttype = 'text';
            options.text = text;
        }
        if (this.component.attachment.value) {
            let attachment = this.component.attachment.value;
            if (attachment.mimetype.includes('image')) {
                options.ttype = 'image';
            } else if (attachment.mimetype.includes('audio')) {
                options.ttype = 'audio';
            } else if (attachment.mimetype.includes('video')) {
                options.ttype = 'video';
            } else {
                options.ttype = 'file';
            }
            options.res_model = 'ir.attachment';
            options.res_id = attachment.id;
            options.res_model_obj = attachment;
        }
        if (options.ttype) {  // el tipo decide si se envía o no el mensaje
            options = this.sendMessageHook(options)
            out = this.parent.selected_conversation.createMessage(options).then(msg => {
                this.$input.prop('disabled', false);
                this.$input.val('');
                this.$input.height('15px');
                this.$input.focus();
                this.component.attachment.value = null;
                this.enableDisplabeAttachBtn();
                return msg;
            })
        }
        return out.finally(() => {
            this.$input.prop('disabled', false)
            this.$send_btn.prop('disabled', false)
        });
    },

    /**
     * Hook para modificar los datos antes de crear el mensaje
     * @param {Object} options diccionario para crear un mensaje
     * @returns {Object} diccionario para crear un mensaje
     */
    sendMessageHook: function(options) {
        return options
    },

    /**
     * Para enviar mensaje presionando Enter
     *
     * @param {Event} event Evento
     */
    onKeypress: function(event) {
        if (event.which === 13 && !event.shiftKey) {
            event.preventDefault();
            event.stopPropagation();
            this.sendMessage();
        }
    },

    /**
     * Funcion geneerica para keydown
     *
     * @param {Event} event Evento
     */
    onKeydown: function(event) {},
    
    /**
     * Funcion que maneja el evento de pegar
     * @param {Event} event evento
     */
    onPaste: function(event) {
        let clipboardData = event.originalEvent.clipboardData || window.clipboardData;
        if (clipboardData) {
            var items = clipboardData.items;
            for (let index in items) {
                const item = items[index];
                if (item.kind === 'file') {
                    event.stopPropagation();
                    event.preventDefault();
                    if (!this.component.attachment.value) {
                        this.component.uploadFile({target: { files: [item.getAsFile()] }})
                    }
                    break
                }
            }
        }
    },
    
    toggleEmojis: function() {
        this.$el.popover("toggle")
        setTimeout(() =>
            this.$('.o_acrux_emoji_popover:visible').on('mouseleave', () => {
                this.$el.popover("hide")
            })
        , 50);
    },
    
    addEmoji: function(event) {
        this.$input.val(this.$input.val() + $(event.target).data('source'))
        if (this.$input.length) {
            // esto esta aqui por el text area multilinea
            // debio cambiar a div, para que lo hiciera solo pero aja.
            this.$input[0].style.height = '15px';
            this.$input[0].style.height = (this.$input[0].scrollHeight) + 'px';
            this.$input.focus();
        }
    },

    /**
     * corrige la posicion del popover
     */
    fix_popover_position: function() {
        let popover = this.$('.o_acrux_emoji_popover');
        if (popover.length) {
            let popover_data = popover[0].getBoundingClientRect()
            let el_data = this.$el[0].getBoundingClientRect()
            let msg_data = this.parent.$chat_message[0].getBoundingClientRect()
            if (popover_data.height > msg_data.height) {
                popover.css('max-height', msg_data.height)
                popover.css('height', msg_data.height)
                popover.offset({top: el_data.top - msg_data.height})
            } else if (popover_data.height < msg_data.height) { 
                popover.css('max-height', '')
                popover.css('height', '')
                popover.offset({top: el_data.top - popover.height()})
            }
            popover.css('z-index', 100) // los emoticones sale sobre los wizards
        }
    },

    /**
     * Consula las preferencias del usuario
     *
     * @returns {Promise} De la solicitud al servidor
     */
    getUserPreference: function() {
        return this._rpc({
            model: 'res.users',
            method: 'read',
            args: [[session.uid], ['chatroom_signing_active']],
            context: this.context,
        }).then(result => {
            this.signing_active = result[0].chatroom_signing_active
        })
    },

    /**
     * Cambia el estatus usuario, invocado desde el servidor por notificación.
     *
     * @param {Object} data Data Json del servidor
     */
    changeStatusNotify: function(data) {
        this.signing_active = !!data.signing_active
        this.signingNoUpdate = true  // es para evitar que _confirmChange llame al servidor
        this.signingWidget._setValue(this.signing_active).then(() => this.signingNoUpdate = false)
    },

    /**
     * Crea los fields que tendrá el toolbox
     * @returns {Promise}
     */
    processUserPreference: function() {
        return this.model.makeRecord('res.users', [{
            name: 'signing_active',
            type: 'boolean',
            value: this.signing_active,
        }]).then(recordID => {
            const record = this.model.get(recordID);
            this.signingWidget = new BooleanToggle(this, 'signing_active', record, {
                attrs: {
                    modifiers: {},
                    string: _t('Sign Message')
                },
            })
            this._registerWidget(recordID, 'signing_active', this.signingWidget);
        })
    },

    /**
     * This method will be called whenever a field value has changed and has
     * been confirmed by the model.
     *
     * @private
     * @override
     * @returns {Promise}
     */
    _confirmChange: function () {
        var result = StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
        return result.then(() => {
            let out = Promise.resolve() 
            if (!this.signingNoUpdate) {
                out = this._rpc({
                    model: 'res.users',
                    method: 'write',
                    args: [[session.uid], { chatroom_signing_active: this.signingWidget.value }],
                    context: this.context,
                })
            }
            return out
        })
    },

    /** ## Envio de archivos adjuntos ## */
    clickAddAttachment: function() {
        this.component.openBrowserFileUploader();
    },

    /**
     * Condicion para deshabilitar la entrada de texto
     * @param {Object} attachment
     * @returns {Boolean}
     */
    needDisableInput: function(attachment) {
        return !(attachment.isImage || attachment.isVideo)
    },

    /**
     * Habilita y deshabilita la entrada de texto cuando se adjunta un archivo
     */
    enableDisplabeAttachBtn: function() {
        this.$attachment_button.prop('disabled', Boolean(this.component.attachment.value));
        if (this.component.attachment.value) {
            let attachment = this.component.attachment.value;
            if (this.needDisableInput(attachment)) {
                this.$input.val('');
                this.$input.prop('disabled', true);
                this.$emoji_btn.prop('disabled', true);
            }
        } else {
            this.$emoji_btn.prop('disabled', false);
            this.$input.prop('disabled', false);
            this.$input.focus();
        }
    },

    /**
     * Set some text to input field.
     * @param {String} text
     */
    setInputText: function(text) {
        if (! (this.$input.prop('disabled') || this.$input.prop('readonly'))) {
            this.$input.val(text);
        }
    },
    /** ## Find de archivos adjuntos ##  */

})

return ToolBox
})
