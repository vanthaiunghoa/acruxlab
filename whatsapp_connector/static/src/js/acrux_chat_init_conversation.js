odoo.define('whatsapp_connector.init_conversation', function(require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var Conversation = require('whatsapp_connector.conversation')

var QWeb = core.qweb;
var _t = core._t;

/**
 * Widget para buscar conversaciones y comenzar a chatear
 *
 * @class
 * @name InitConversation
 * @extends web.Widget
 */
var InitConversation = Widget.extend({
    template: 'acrux_chat_init_conversation',
    events: {
        'click .o_button_conv_search': 'searchConversation',
        'keypress .conv_search': 'onKeypress',
        'click .o_button_create_conversation': 'createConversation',
        'click .o_acrux_chat_conv_items > .o_conv_record': 'selectConversation',
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
        this.conv_list = this.options.conv_list || [];
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
        this.$input_search = this.$('input.conv_search');
        this.$conv_items = this.$('.o_acrux_chat_conv_items');
        this.renderConvList();
        return Promise.resolve();
    },
    
    /**
     * Identifica si la conversacion está en la lista, actualiza la conversacion
     *
     * @param {Object} new_conv Conversación a actualizar
     */
    update: function(new_conv) {
        if (this.conv_list) {
            let conv = this.conv_list.find(x => x.id == new_conv.id);
            if (conv) {
                let tmp = this.postProcessorResult([Object.assign({}, new_conv)])[0];
                Object.assign(conv, tmp);
            }
        }
    },
    
    /**
     * Muestra la lista de los mensajes
     */
    renderConvList: function() {
        let html = QWeb.render('acrux_chat_conv_list', {conv_list: this.conv_list});
        this.$conv_items.html(html);
    },

    /**
     * Domain para consultar las conversaciones
     * @returns {List<Object>} Lista con las condiciones
     */
    getSearchDomain: function() {
        let val = this.$input_search.val().trim();
        return ['|', '|', ['name', 'ilike', val],
                          ['number_format', 'ilike', val],
                          ['number', 'ilike', val]];
    },

    /**
     * Busca los conversaciones y los muestra
     * @returns {Promise}
     */
    searchConversation: function() {
        let val = this.$input_search.val(), domain;
        if (val && '' != val.trim()) {
            domain = this.getSearchDomain();
        } else {
            domain = []
        }
        return this._rpc({
            model: this.parent.model,
            method: 'search_read',
            args: [domain, this.parent.conversation_used_fields, 0, 100],
            context: this.context
        }).then(result => {
            result = this.postProcessorResult(result);
            this.conv_list = result
            this.renderConvList();
        })
    },
    
    /**
     * Hace un post processor de los resultaso solo para hacer en la demo
     */
    postProcessorResult: function(result) {
        return result.map(conv => {
            conv.getIconClass = Conversation.prototype.getIconClass.bind(conv)
            return conv
        })
    },

    /**
     * Luego de seleccionar la conversación trata de seleccionarla
     *
     * @param {Event} event
     * @returns {Promise}
     */
    selectConversation: function(event) {
        let conversation_id = $(event.currentTarget).data('id');
        return this.initAndNotify(conversation_id);
    },

    /**
     * Envia solicitud al servidor para iniciar una conversacion
     * @param {Itenger} conversation_id El ID de la conversacion
     * @returns {Promise}
     */
    initAndNotify: function(conversation_id) {
        return this._rpc({
            model: this.parent.model,
            method: 'init_and_notify',
            args: [[conversation_id]],
            context: this.context
        });
    },

    /**
     * Busca los conversaciones cuando se presiona enter
     *
     * @param {Event} event
     */
    onKeypress: function(event) {
        if (event.which === 13) {
            if ($(event.currentTarget).hasClass('conv_search')) {
                event.preventDefault();
                this.searchConversation();
            }
        }
    },

    /**
     * Vacia los datos del widget
     */
    empty: function() {
        this.$input_search.val('');
        this.$conv_items.html('');
        this.conv_list = [];
    },

    /**
     * Abre dialogo para crear una conversación.
     *
     * @param {Event} event
     * @returns {Promise} 
     */
    createConversation: function(event) {
        let context 
        if (event && event.context) {
            context = event.context
        } else {
            context = this.context
        }
        let action = {
            type: 'ir.actions.act_window',
            name: _t('Create'),
            view_type: 'form',
            view_mode: 'form',
            res_model: this.parent.model,
            views: [[false, 'form']],
            target: 'new',
            context: context,
            acrux_init_conv: (recordID) => {
                if (recordID) {
                    this.initAndNotify(recordID).then(() => {
                        this.do_action({type: 'ir.actions.act_window_close'})
                    })
                }
            }
        }
        return this.do_action(action)
    },
})

return InitConversation
})
