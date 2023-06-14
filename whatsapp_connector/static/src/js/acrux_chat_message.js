odoo.define('whatsapp_connector.message', function(require) {
"use strict";

const { getMessagingComponent } = require('@mail/utils/messaging_component');
const components = {
    AttachmentImage: getMessagingComponent('AttachmentImage'),
    AttachmentCard: getMessagingComponent('AttachmentCard'),
}
const { link } = require('@mail/model/model_field_command')

const { Component } = owl;

var core = require('web.core');
var Widget = require('web.Widget');
var field_utils = require('web.field_utils');
var session = require('web.session');
var AudioPlayer = require('whatsapp_connector.audio_player')
var MessageMetadata = require('whatsapp_connector.message_metadata')

var QWeb = core.qweb;
var _t = core._t;


/**
 * Representa el modelo mensaje
 *
 * @class
 * @name Message
 * @extends web.Widget
 */
var Message = Widget.extend({
    template: 'acrux_chat_message',
    events: {},

    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, options) {
        this._super.apply(this, arguments);

        this.parent = parent;
        if (!this.conversation) {
            this.conversation = parent;
        }
        this.options = _.extend({}, options);
        this.context = _.extend({}, this.parent.context || {}, this.options.context);
        this.update(this.options);
    },

    /**
     * Actualiza los campos del mensaje
     * @param {Object} options datos a actualizar
     */
    update: function(options) {
        this.options = options
        this.id = options.id;
        this.ttype = options.ttype || 'text';
        this.from_me = options.from_me || false;
        this.text = options.text || '';
        this.res_model = options.res_model || false;
        this.res_id = options.res_id || false;
        this.error_msg = options.error_msg || false;
        this.show_product_text = options.show_product_text || false;
        this.res_model_obj = options.res_model_obj;
        this.date_message = options.date_message || moment();
        this.convertDate('date_message')
        if (this.ttype == 'location') {
            this.createLocationObj();
        }
        if (['image', 'video', 'file'].includes(this.ttype) && this.res_model_obj) {
            if (!this.isAttachmentComponent()) {
                this.res_model_obj = this.createAttachComponent(this.res_model_obj)
            }
        }
        this.title_color = options.title_color || '#000000';
        this.title_color = this.title_color != '#FFFFFF' ? this.title_color : '#000000';
        this.metadata_type = options.metadata_type || null
        this.metadata_json = options.metadata_json || null
    },

    /**
     * Si no tiene el objeto adjunto se lee del servidor y se crea.
     *
     * @override
     * @see Widget.willStart
     */
    willStart: function() {
        let def = false;
        if (this.res_model && !this.res_model_obj) {
            def = this._rpc({
                model: this.res_model,
                method: 'read_from_chatroom',
                args: [this.res_id],
                context: this.context
            }).then(result => {
                if (result.length > 0) {
                    this.res_model_obj = result[0];
                    if (this.res_model == 'product.product') {
                        let price = this.res_model_obj.lst_price;
                        price = this.conversation.parent.format_monetary(price);
                        this.res_model_obj.lst_price = price;
                        this.res_model_obj.show_product_text = this.show_product_text
                    } else {
                        let filename = this.res_model_obj.display_name || _t('Unnamed');
                        this.res_model_obj.filename = filename;
                        if (this.ttype != 'audio') {
                            const Attachment = Component.env.services.messaging.modelManager.models['mail.attachment']
                            let tmp;
                            tmp = Attachment.findFromIdentifyingData(this.res_model_obj);
                            if (!tmp) {
                                tmp = Attachment.insert(this.res_model_obj);
                            }
                            this.res_model_obj = this.createAttachComponent(tmp)
                        }
                    }
                } else {
                    if (this.res_model == 'product.product') {
                        this.res_model_obj = { display_name: _t('Product not found') }
                    } else {
                        this.res_model_obj = { display_name: _t('File not found') }
                        this.res_model_obj.filename = this.res_model_obj.display_name;
                    }
                }
            });
        }
        return Promise.all([this._super(), def]);
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
        let def = Promise.resolve();
        if (this.res_model_obj) {
            if (this.res_model == 'product.product') {
                this.$('.oe_product_details > ul > li').last().remove();
            } else {
                this.$('div.caption').html('');
                if (this.ttype == 'audio') {
                    def = this.audioController();  // muestra los controles de audio
                }
                if (this.isAttachmentComponent()) {
                    def = this.res_model_obj.mount(this.$('div#o_attach_zone')[0]);
                } else {
                    if (this.res_model_obj) {
                        this.$('div#o_attach_zone').html(this._renderCustomObject())
                    }
                }
            }
        }
        if (this.metadata_type === 'apichat_preview_post') {
            def.then(() => this.messageMetadataController())
        }
        return Promise.all([def]).then(() => this.makeMessageDragAndDrop());
    },

    /**
     * Renderiza un objeto personalizado en el area de los adjuntos
     * @returns {String}
     */
    _renderCustomObject: function() {
        let out = ''
        if (this.res_model_obj.display_name) {
            out = `<i>${this.res_model_obj.display_name}</i>`
        }
        return out
    },

    /**
     * Retorna clases css para modificar el contenido del mensaje
     * @returns {String}
     */
    message_css_class: function() {
        /** @type {Array<String>} */
        const list = this.message_css_class_list()
        return list.join(' ');
    },

    /**
     * Retorna una lista de las classes CSS para aplicarlas al contendio del mensaje
     * @returns {Array<String>}
     */
    message_css_class_list: function() {
        return []
    },

    /**
     * Indica que tipo de mensajes se puede hacer arrastrables
     * @returns {Boolean}
     */
    isToDrop: function() {
        return false;
    },

    /**
     * Esto hace los menajes sean arrastrables
     */
    makeMessageDragAndDrop: function() {
        if (this.isToDrop()) {
            this.$el.draggable({
                revert: true,
                revertDuration: 0,
                containment: this.conversation.parent.$el,
                appendTo: this.conversation.parent.$el,
                helper: 'clone',
            });
        }
    },

    /**
     * @override
     */
    destroy: function() {
        return this._super.apply(this, arguments);
    },

    /**
     * Se crea un objeto jsonable para enviar al servidor.
     *
     * @returns {Object}
     */
    export_to_json: function() {
        let out = {};
        out.text = this.text;
        out.from_me = this.from_me;
        out.ttype = this.ttype;
        out.res_model = this.res_model;
        out.res_id = this.res_id;
        if (this.id) {
            out.id = this.id
        }
        out.title_color = this.title_color;
        if (this.metadata_type) {
            out.metadata_type = this.metadata_type
        }
        if (this.metadata_json) {
            out.metadata_json = this.metadata_json
        }
        return out;
    },

    /**
     * Retorna un object jsonable con los campos para el create 
     * @returns {Object}
     */
    export_to_vals: function() {
        let out = this.export_to_json()
        delete out.title_color
        return out;
    },

    /**
     * Estable el motivo del error en el mensaje
     *
     * @param {String} error_msg Mensaje de error
     */
    setErrorMessage: function(error_msg) {
        this.error_msg = error_msg;
    },

    /**
     * Construye un html con la fecha del mensaje
     *
     * @returns {String}
     */
    getDateTmpl: function() {
        return QWeb.render('acrux_chat_chat_date', { widget: this });
    },

    /**
     * Devuelve la fecha que se mostrar en el chat
     *
     * @returns {String}
     */
    getDate: function() {
        return field_utils.format.date(this.date_message, {type: 'datetime'}, {timezone: true});
    },

    /**
     * Devuelve la hora el formato militar.
     *
     * @returns {String}
     */
    getHour: function() {
        let value = this.date_message.clone();
        value.add(session.getTZOffset(value), 'minutes');
        return value.format("HH:mm");
    },

    /**
     * Controlador de auido
     * @returns {Promise}
     */
    audioController: function() {
        if (this.audioPlayerWidget) {
            this.audioPlayerWidget.destroy()
        }
        let options = { 
            context: this.context,
            src: `/web/chatresource/${this.res_model_obj.id}`
        }
        this.audioPlayerWidget = new AudioPlayer(this, options)
        return this.audioPlayerWidget.appendTo(this.$('#audio_player'))
    },

    /**
     * Crea un objeto necesario para visualiar los mensaje de tipo location,
     * se muestra una imagen estatica y si espera un formato exacto de mensaje,
     * si el formato no se correcto se muestra un mensaje de error en la conversación
     */
    createLocationObj: function() {
        if (this.text) {
            try {
                let text = this.text.split('\n');
                let loc_obj = {};
                loc_obj.display_name = text[0].trim();
                loc_obj.address = text[1].trim();
                loc_obj.coordinate = text[2].trim();
                text = loc_obj.coordinate.replace('(', '').replace(')', '');
                text = text.split(',');
                loc_obj.coordinate = { x: text[0].trim(), y: text[1].trim() }
                loc_obj.map_url = 'https://maps.google.com/maps/search/';
                loc_obj.map_url += `${loc_obj.display_name}/@${loc_obj.coordinate.x},${loc_obj.coordinate.y},17z?hl=es`;
                loc_obj.map_url = encodeURI(loc_obj.map_url);
                this.location = loc_obj;
            } catch (err) {
                console.log('error location');
                console.log(err);
            }
        }
    },
    
    /**
     * convierte un campo tipo string a fecha
     * @param {String} field el campo a convertir
     */
    convertDate: function(field) {
        if (this[field] &&
            (this[field] instanceof String || typeof this[field] === "string")) {
            this[field] = field_utils.parse['datetime'](this[field]);
        }
    },

    /**
     * Retorna si el componente es un adjunto
     * @returns {Boolean}
     */
    isAttachmentComponent: function() {
        return this.res_model_obj && (
                this.res_model_obj instanceof components.AttachmentImage || 
                this.res_model_obj instanceof components.AttachmentCard)
    },

    /**
     * Crea el componente para los adjuntos
     * @param {Object} attachment es el adjunto que se maneja en mail
     * @returns {components.AttachmentImage|components.AttachmentCard}
     */
    createAttachComponent: function(attachment) {
        let props = {}, comp = null, attch_list
        const AttachmentList = Component.env.services.messaging.modelManager.models['mail.attachment_list']
        const Attachment = Component.env.services.messaging.modelManager.models['mail.attachment']
        const vals = {
            isAcrux: true,
            acruxMessageId: this.id,
        }
        attachment = Attachment.findFromIdentifyingData(attachment)
        if (!attachment.attachmentLists || attachment.attachmentLists.length === 0) {
            attch_list = AttachmentList.insert(vals)
        } else {
            attch_list = AttachmentList.get(attachment.attachmentLists[0].localId)
            attch_list.update(vals)
        }
        const attachVals = this.getAttachVals()
        attachVals.attachmentLists = link(attch_list)
        attachment.update(attachVals)
        
        /* siempre entra a una sola interacion de alguno de los cliclos
                   nunca deberia entrar a mas de uno. */
        for (const attachmentImage of attachment.attachmentImages) {
            props.attachmentImageLocalId = attachmentImage.localId
            comp = new components.AttachmentImage(null, props);
        }
        for (const attachmentCard of attachment.attachmentCards) {
            props.attachmentCardLocalId = attachmentCard.localId
            comp = new components.AttachmentCard(null, props);
        }
        
        return comp
    },

    /**
     * Permite activar o desactivar la opcion de responder mensaje
     * Para poder heredarlo se coloca aqui
     * @returns {Boolean}
     */
    canBeAnswered: function() {
        return true
    },

    /**
     * Permite activar o desactivar la opcion de borrar mensaje
     * Para poder heredarlo se coloca aqui
     * @returns {Boolean}
     */    
    canBeDeleted: function() {
        return true
    },

    /**
     * Retorna si el mensaje tiene titulo
     * @returns {Boolean}
     */
    hasTitle: function() {
        return false;
    },
    
    /**
     * Controlador de auido
     * @returns {Promise}
     */
    messageMetadataController: function() {
        if (this.messageMetadataWidget) {
            this.messageMetadataWidget.destroy()
        }
        let options = { 
            metadata_type: this.metadata_type,
            metadata_json: this.metadata_json
        }
        this.messageMetadataWidget = new MessageMetadata(this, options)
        this.$('.o_message_metadata_preview').removeClass('o_hidden')
        return this.messageMetadataWidget.appendTo(this.$('.o_message_metadata_preview'))
    },

    /**
     * Retorna los valores para actualizar el adjunto
     * @returns {Object}
     */
    getAttachVals: function() {
        return {isAcrux: true}
    },
    
})

return Message
})
