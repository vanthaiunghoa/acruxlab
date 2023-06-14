odoo.define('whatsapp_connector.user_status', function(require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var session = require('web.session');

var _t = core._t;

/**
 * Widget que maneja el estatus (activo/inactivo) del chat
 *
 * @class
 * @name UserStatus
 * @extends web.Widget
 */
var UserStatus = Widget.extend({
    template: 'acrux_chat_user_status',
    events: {
        'click label#chat_status_active': 'changeStatus',
        'click label#chat_status_inactive': 'changeStatus',
        'click .acrux_simple_create_new_conv': 'openSimpleNewConversation',
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

        this.acrux_chat_active = this.options.acrux_chat_active;

    },

    /**
     * @override
     * @see Widget.willStart
     */
    willStart: function() {
        return Promise.all([
            this._super(),
            this.getUserStatus(),
        ]);
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
        let label_active = 'label#chat_status_active';
        let label_inactive = 'label#chat_status_inactive';

        this.$lables_status = this.$(label_active + ', ' + label_inactive);
        if (this.acrux_chat_active) {
            this.$(label_active).addClass('active');
        } else {
            this.$(label_inactive).addClass('active');
        }
        return Promise.resolve();
    },

    /**
     * Consula el estado del usuario al servidor
     *
     * @returns {Promise} De la solicitud al servidor
     */
    getUserStatus: function() {
        return this._rpc({
            model: 'res.users',
            method: 'read',
            args: [[session.uid], ['acrux_chat_active']],
            context: this.context
        }).then(result => {
            this.acrux_chat_active = result[0].acrux_chat_active;
        });
    },

    /**
     * Cambia el estatus del usuario, invocado por la vista.
     * El nuevo estatus es informado al servidor
     *
     * @param {Event} event
     */
    changeStatus: function(event) {
        let $target = $(event.target), toggle = false;
        if ($target.prop('id') == 'chat_status_active') {
            if (!this.acrux_chat_active) {
                toggle = true;
            }
        } else {
            if (this.acrux_chat_active) {
                toggle = true;
            }
        }
        if (toggle) {
            this.$lables_status.toggleClass('active');
            this.acrux_chat_active = !this.acrux_chat_active;
            this._rpc({
                model: 'res.users',
                method: 'set_chat_active',
                args: [[session.uid], { acrux_chat_active: this.acrux_chat_active }],
                context: this.context
            });
        }
    },

    /**
     * Cambia el estatus usuario, invocado desde el servidor por notificación.
     *
     * @param {Object} data Data Json del servidor
     */
    changeStatusNotify: function(data) {
        if (this.acrux_chat_active != data.status) {
            this.$lables_status.toggleClass('active');
        }
        this.acrux_chat_active = data.status;
    },

    /**
     * Retorna si el usuario esta activo
     *
     * @returns {Boolean}
     */
    isActive: function() {
        return this.acrux_chat_active;
    },
    
    /**
     * abre el wizard para crear / buscar una conversacion
     */
    openSimpleNewConversation: function() {
        let action = {
            type: 'ir.actions.act_window',
            name: _t('Search'),
            view_type: 'form',
            view_mode: 'form',
            res_model: 'acrux.chat.simple.new.conversation.wizard',
            views: [[false, 'form']],
            target: 'new',
            context: this.context,
        }
        this.do_action(action)
    },
});

return UserStatus;
});
