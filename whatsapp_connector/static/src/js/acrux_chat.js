odoo.define('whatsapp_connector.acrux_chat', function(require) {
"use strict";

require('bus.BusService');
var core = require('web.core');
var AbstractAction = require('web.AbstractAction');
var session = require('web.session');
var chat = require('whatsapp_connector.chat_classes');
var config = require('web.config');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');

var _t = core._t;
var chat_is_read_resolve = null;
var chat_is_read = new Promise(r => chat_is_read_resolve = r);
var QWeb = core.qweb;

/**
 * Clase principal que se encarga de administrar todo el chat room
 *
 * @class
 * @name AcruxChatAction
 * @extends Widget
 * @todo Debería dividirse esta clase, es muy grande
 */
var AcruxChatAction = AbstractAction.extend({
    contentTemplate: 'acrux_chat_action',
    hasControlPanel: false,
    events: {
        'click .o_acrux_chat_notification .fa-close': '_onCloseNotificationBar',
        'click .o_acrux_chat_request_permission': '_onRequestNotificationPermission',
        'click .o_acrux_chat_item': 'selectConversation',
        'click .navbar-toggler.show_thread': 'showChatPanel',
        'click .navbar-toggler.show_conv': 'showConversationPanel',
        'click .navbar-toggler.show_option': 'showRightPanel',
        'click .navbar-toggler.hide_option': 'hideRightPanel',
        'click li#tab_partner': 'tabPartner',
        'click li#tab_conv_info': 'tabConvInfo',
        'click div#acrux_chat_main_view': 'globalClick',
    },

    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, action, options) {
        this._super.apply(this, arguments);
        this.action_manager = parent;
        this.env = parent.env
        this.model = 'acrux.chat.conversation';
        this.domain = [];
        this.action = action;
        this.options = options || {};
        this.notification_bar = (window.Notification && window.Notification.permission === "default");
        this.selected_conversation = this.options.selected_conversation;
        this.conversation_used_fields = [];
        this.conversations = this.options.conversations || [];
        this.default_answers = this.options.default_answers || [];
        this.context = this.action.context
        this.defaultChannelID = this.options.active_id ||
            this.action.context.active_id ||
            this.action.params.default_active_id ||
            'acrux_chat_live_id';
        let widget_options = { context: this.context };
        
        this.toolbox = new chat.ToolBox(this, widget_options);
        this.product_search = new chat.ProductSearch(this, widget_options);
        this.init_conversation = new chat.InitConversation(this, widget_options);
        this.user_status = new chat.UserStatus(this, widget_options);
        if (odoo.debranding_new_name) {
            this.company_name = odoo.debranding_new_name;
        } else {
            this.company_name = 'Odoo';
        }
        this.load_more_message = false;
    },

    /**
     * Para iniciar el bus de las notifiaciones.
     * Se abre un canal publico y uno privido. El publico es para las difuciones,
     * es decir, notificación que llegan a todos los usuarios del chat,
     * la privada es para las conversaciones con los clientes
     */
    startBus: function() {
        this.call('bus_service', 'onNotification', this,
            notifications => this.onNotification(notifications))
    },

    /**
     * @override
     * @see Widget.willStart
     */
    willStart: function() {
        return Promise.all([this._super(), session.is_bound]).then(() => {
            this.current_company_id = session.user_context.allowed_company_ids[0]
            return Promise.all([
                this.getDefaultAnswers(),
                this.getRequiredViews(),
                this.getCurrency(),
                this.getConversationUsedFields()
            ])
        })
        
    },

    /**
     * @override
     * @see Widget.start
     */
    start: function() {
        return this._super()
        .then(() => this._initRender())
        .then(() => this.startBus())
        .then(() => {
            if (this.user_status.isActive()) {
                return this.changeStatusView();
            }
        })
        .then(() => chat_is_read_resolve(this))
        .then(() => core.bus.trigger('chatroom:create', this))
    },

    /**
     * Hace trabajos de render
     *
     * @private
     * @returns {Promise} Para indicar que termino
     */
    _initRender: function() {
        this._buildJqueryObjects();
        this.$chat_message.on('scroll', (event) => {
            // cuando se hace scroll en la conversacion se cargan mensajes viejos
            if ($(event.target).scrollTop() == 0 && this.selected_conversation &&
                this.load_more_message) {
                return this.selected_conversation.syncMoreMessage();
            }
        });
        // evento para marcar mensajes vistos
        core.bus.on('acrux_chat_msg_seen', this, this.chatMessageSeen);
        if (config.device.isMobile) {
            this.showConversationPanel();
        }
        this.$('.o_sidebar_right').find('ul.nav.nav-tabs').find('li > a').click(e => {
            // si hace clic en alguna pestaña que no sea el de cliente
            // el div de los productos vuelve al tamaño normal
            if (!this._getMaximizeTabs().includes($(e.target).attr('href'))) {
                this.product_search.maximize();
            }
        });
        this.onResizeWindow();
        this.onWindowShow();
        return Promise.all([
            this.toolbox.appendTo(this.$chat_content),
            this.product_search.prependTo(this.$sidebar_right),
            this.init_conversation.appendTo(this.$tab_init_chat),
            this.user_status.appendTo(this.$sidebar_left.find('.o_acrux_group').first()),
            this.showDefaultAnswers(),
            this.addChatroomPopover(),
        ]).then(() => {
            /** se vuelve a buscar el titulo porque uno de los componentes agrega
            otra div con o_conv_title y los quiero a ambos */
            this.$chat_title = this.$('.o_conv_title'); 
            this.toolbox.do_hide();
        });
    },

    /**
     * Crea todos los objectos jquery para renderizar.
     * 
     * @private
     */
    _buildJqueryObjects: function() {
        this.$chat_content = this.$('.o_acrux_chat_content');
        this.$sidebar_left = this.$('.o_sidebar_left');
        this.$sidebar_right = this.$('.o_sidebar_right');
        this.$first_main_tab = this.$('.o_sidebar_right').find('ul.nav.nav-tabs').children('li').first().find('a');
        this.$first_content_tab = this.$('.o_sidebar_right #acrux_tabs .tab-content div').first()
        this.$chat_message = this.$('div.o_chat_thread');
        this.$current_chats = this.$('.o_acrux_chat_items.o_current_chats');
        this.$new_chats = this.$('.o_acrux_chat_items.o_new_chats');
        this.$chat_title = this.$('.o_conv_title');
        this.$tab_default_answer = this.$('div#tab_content_default_answer > div.o_group');
        this.$tab_init_chat = this.$('div#tab_content_init_chat');
        this.$tab_content_partner = this.$('div#tab_content_partner > div.o_group');
        this.$tab_content_conv_info = this.$('div#tab_content_conv_info > div.o_group');
        this.$first_main_tab.addClass('active')
        this.$first_content_tab.addClass('active')
    },

    /**
     * @override
     */
    destroy: function() {
        if (this.$el) {
            this.$chat_message.off('scroll');
            core.bus.off('acrux_chat_msg_seen');
        }
        core.bus.trigger('chatroom:destroy')
        return this._super.apply(this, arguments);
    },
    
    /**
     * @override
     */
    do_show: function() {
        this._super.apply(this, arguments);
        this.action_manager.do_push_state({
            action: this.action.id,
        });
    },

    /**
     * @override
     */
    on_attach_callback: function() {
        this._super(...arguments);
        if (this.toolbox) {
            this.toolbox.on_attach_callback();
        }
    },

    /**
     * Consulta al servidor las conversaciones nuevas y actuales.
     *
     * @returns {Promise}
     */
    getServerConversation: function() {
        return this._rpc({
            model: this.model,
            method: 'search_active_conversation',
            args: [],
            context: this.context
        }).then(result => {
            result.forEach(r => {
                this.conversations.push(new chat.Conversation(this, r));
            });
        });
    },

    /**
     * Consulta al servidor la moneda de la empresa, esto debería estar en 
     * algún variable de ambiente, pero no la encontré
     *
     * @returns {Promise}
     */
    getCurrency: function() {
        return this._rpc({
            model: 'res.company',
            method: 'read',
            args: [[this.current_company_id], ['currency_id']],
            context: this.context
        }).then(result => {
            this.currency_id = result[0].currency_id[0];
            this.currency = session.get_currency(this.currency_id);
        });
    },

    /**
     * Consulta al servidor todas las respuestas predeterminadas
     *
     * @returns {Promise}
     */
    getDefaultAnswers: function() {
        return this._rpc({
            model: 'acrux.chat.default.answer',
            method: 'get_for_chatroom',
            args: [],
            context: this.context
        }).then(result => {
            result.forEach(r => this.default_answers.push(new chat.DefaultAnswer(this, r)));
        });
    },

    /**
     * Consulta la vista a utilizar.
     *
     * @returns {Promise}
     */
    getRequiredViews: function() {
        return this._rpc({
            model: this.model,
            method: 'check_object_reference',
            args: ['', 'view_whatsapp_connector_conversation_chatroom_form'],
            context: this.context
        }).then(result => {
            this.conversation_info_forms = result[1];
        });
    },
    
    /**
     * Consulta los campos que se utilizan siempre en la conversacion
     *
     * @returns {Promise}
     */
    getConversationUsedFields: function() {
        return this._rpc({
            model: this.model,
            method: 'get_fields_to_read',
            args: [],
            context: this.context
        }).then(result => {
            this.conversation_used_fields = result;
        })
    },

    /**
     * Formatea un numero con la moneda de la empresa
     *
     * @returns {String} Numero formateado
     */
    format_monetary: function(val) {
        val = field_utils.format.monetary(val, null, { currency: this.currency });
        return $('<span>').html(val).text()
    },

    /**
     * Marca los mensajes de la conversación seleccionada como vistos.
     * Esta función es llamada desde un evento cuando la página se muestra,
     * esta pensada para no marcar los mensajes visto si no está en la página 
     * de odoo
     */
    chatMessageSeen: function() {
        if (this.selected_conversation && this.selected_conversation.isMine()) {
            this.selected_conversation.messageSeen();
        }
    },

    /**
     * Actualiza la vista dependiendo del tamaño de la pantalla, esta pensada
     * para el caso mobile pero también funciona pra maximizar de una pantalla
     * de escritorio
     */
    onResizeWindow: function() {
        let original_device = config.device.isMobile;
        $(window).resize(() => {
            if (config.device.isMobile != original_device) {
                if (config.device.isMobile) {
                    this.showConversationPanel();
                } else {
                    this.showChatPanel();
                    this.$sidebar_left.removeClass('d-none');
                }
                original_device = config.device.isMobile;
            }
        });
    },

    /**
     * Cuando cambia de pestaña en el navegador y sale de la pestaña odoo, el
     * document (html) se colo invisible, cuando vuelve el documento vuelve
     * a ser visible, esto 
     */
    onWindowShow: function() {
        document.addEventListener('visibilitychange', function(_ev) {
            if (!document.hidden) {
                core.bus.trigger('acrux_chat_msg_seen');
            }
        });
    },

    /**
     * Realiza los cambios visuales cuando hay un cambio de estatus del chat
     * (activo/inactivo).
     * activo -> inactivo, se borran las conversaciones y se liberan los objectos.
     * inactivo -> activo, se consultan las conversaciones al servidor y se muestran
     * @returns {Promise}
     */
    changeStatusView: function() {
        let out = Promise.resolve()
        this.conversations.forEach(x => x.destroy());
        this.conversations = [];
        if (this.user_status.isActive()) {
            out = this.getServerConversation().then(() => this.showConversations());
        }
        this.selected_conversation = null;
        this.toolbox.do_hide();
        this.tabsClear();
        return out
    },

    /**
     * Muestra todas las conversaciones en el chat
     *
     * @returns {Promise}
     */
    showConversations: function() {
        let defs = [];
        this.$new_chats.html('');
        this.getNewConversation().forEach(x => defs.push(this.renderNewConversation(x)));
        this.$current_chats.html('');
        this.getCurrentConversation().forEach(x => defs.push(x.appendTo(this.$current_chats)));
        return Promise.all(defs);
    },

    /**
     * Renderiza una conversacion en la seccion de nuevas conversaciones
     *
     * @param {Conversation} conv Conversación a renderizar
     * @returns {Promise}
     */
    renderNewConversation: function(conv) {
        return conv.appendTo(this.$new_chats);
    },

    /**
     * Solo mobile
     * Muestra la lista de conversaciones.
     * Oculta el resto
     */
    showConversationPanel: function() {
        if (config.device.isMobile) {
            this.$chat_content.hide();
        }
        this.$sidebar_left.removeClass('d-none');
    },

    /**
     * Solo mobile
     * Muestra los mensajes de la conversación actual
     * Oculta el resto
     */
    showChatPanel: function() {
        if (config.device.isMobile) {
            this.$sidebar_left.addClass('d-none');
        }
        this.$chat_content.show();
    },

    /**
     * Solo mobile
     * Muestra el area de los formularios
     * Oculta el resto
     */
    showRightPanel: function() {
        if (!config.device.isMobile) {
            this.$sidebar_left.addClass('d-none');
        }
        this.$chat_content.hide();
    },

    /**
     * Solo mobile
     * Oculta el area de los formularios
     * Muestra el resto
     */
    hideRightPanel: function() {
        if (!config.device.isMobile) {
            this.$sidebar_left.removeClass('d-none');
        }
        this.$chat_content.show();
    },

    /**
     * Muestra las respuestas predeterminadas
     * @returns {Promise}
     */
    showDefaultAnswers: async function() {
        const target = this.$('div.default_table_answers')
        return this._showDefaultAnswers(this.default_answers, target)
    },

    /**
     * Muestra las respuestas predeterminadas
     * @param {Array<Object>} default_answers
     * @param {Jquery} target
     * @returns {Promise}
     */
    _showDefaultAnswers: async function(default_answers, target) {
        let index = 0, row = $('<div class="row-default">'), row_size = 2;
        let padding = default_answers.length % row_size;
        padding = row_size - padding;
        let func_default_answer = (arr) => {
            if (index < arr.length) {
                return arr[index].appendTo(row).then(() =>{
                    ++index;
                    if (index % row_size == 0) {
                        row.appendTo(target);
                        row = $('<div class="row-default">')
                    }
                    return func_default_answer(arr);
                })
            } else if (padding) {
                for(let i = 0; i < padding; ++i) {
                    $('<div class="cell-default">').appendTo(row);
                }
                row.appendTo(target);
            }
            return Promise.resolve();
        }
        return func_default_answer(default_answers);
    },

    /**
     * Returna la lista de mensajes nuevos
     *
     * @returns {Array<Conversation>}
     */
    getNewConversation: function() {
        return this.conversations.filter(x => x.status == 'new');
    },

    /**
     * Returna la lista de mensajes NO nuevos, como está actualmente el chat
     * solo retorna conversaciones actuales (estado "current") pero también
     * podría retornar terminadas (estado "done")
     *
     * @returns {Array<Conversation>}
     */
    getCurrentConversation: function() {
        return this.conversations.filter(x => x.isMine());
    },

    /**
     * Selecciona una conversacion si esposible
     *
     * @param {Event} event
     * @returns {Promise} Para indicar que terminó el proceso de mostrar los mensajes
     */
    selectConversation: function(event) {
        let finish;
        let id = $(event.currentTarget).data('id');
        let conv_id = this.conversations.find(x => x.id == id);

        if (conv_id && this.selected_conversation != conv_id) {
            if (this.selected_conversation) {
                this.selected_conversation.$el.removeClass('active');
            }
            this.selected_conversation = conv_id;
            this.load_more_message = false;
            finish = this.selected_conversation.showMessages();
            finish.then(() => this.load_more_message = true)
            this.tabsClear();
        } else {
            finish = Promise.resolve();
        }
        this.toolbox.do_show();
        this.toolbox.$input.focus();
        this.showChatPanel();
        return finish;
    },

    /**
     * Guarda el nuevo partner en la conversacion
     *
     * @param {Object} partner_id El partner a guardar
     */
    setNewPartner: function(partner_id) {
        if (partner_id && partner_id.data && partner_id.data.id
            && partner_id.data.id != this.selected_conversation.res_partner_id[0]) {
            partner_id = Object.assign({}, partner_id);
            partner_id.data.name = partner_id.data.display_name;
            if (this.res_partner_form) {
                this.res_partner_form.recordChange(partner_id).then(() => {
                    this.saveDestroyWidget('res_partner_form')
                });
            } else {
                let tmp_widget = new chat.ResPartnerForm(this, {});
                tmp_widget.recordChange(partner_id).then(() => {
                    tmp_widget.destroy();
                });
            }
        }
    },

    /**
     * Devuelve si el controlador es parte de chatroom, es util para los tabs
     * @param {String} jsId id del controllador
     * @returns {Boolean}
     * @todo agregar esta funcion en todos los modulos que agregan tabs con formularios o tree
     */
    isChatroomTab: function(jsId) {
        return this._isChatroomTab('res_partner_form', jsId)
    },

    /**
     * Funcion generica para comprobar si el controlador se instancio desde el chat
     * @param {String} name Nombre del formulario o vista tree
     * @param {String} jsId id del controllador
     * @returns {Boolean}
     */
    _isChatroomTab: function(name, jsId) {
        let out = false
        if (this && this[name]) {
            let tmp_form = this[name]
            out = tmp_form.isMyController(jsId)
        }
        return out
    },

    /**
     * Cuando se hace clic en el tab de cliente, se muestra un formulario
     * de res.partner
     *
     * @param {Event} _event
     * @param {Object} data
     * @return {Promise}
     */
    tabPartner: function(_event, data) {
        let out = Promise.reject()

        if (this.selected_conversation) {
            let partner_id = this.selected_conversation.res_partner_id;
            this.saveDestroyWidget('res_partner_form')
            let options = {
                context: _.extend({conversation_id: this.selected_conversation.id},
                                   this.context),
                res_partner: partner_id,
                action_manager: this.action_manager,
                searchButton: true,
                searchButtonString: _t('Match with Existing Partner'),
                title: _t('Partner'), /** @todo nuevo campo agregar a todos los modulos que agregan formulario o tree */
            }
            this.res_partner_form = new chat.ResPartnerForm(this, options)
            this.$tab_content_partner.empty()
            out = this.res_partner_form.appendTo(this.$tab_content_partner);
        } else {
            this.$tab_content_partner.html(QWeb.render('acrux_empty_tab'))
        }
        out.then(() => data && data.resolve && data.resolve())
        out.catch(() => data && data.reject && data.reject())
        return out
    },

    /**
     * Cuando se hace clic en el tab info, se muestra un formulario
     * de conversation
     *
     * @param {Event} _event
     * @param {Object} data
     * @return {Promise}
     */
    tabConvInfo: function(_event, data) {
        let out = Promise.reject()

        if (this.selected_conversation) {
            if (this.selected_conversation.isMine()) {
                let conv_info = [this.selected_conversation.id, this.selected_conversation.name];
                this.saveDestroyWidget('conv_info_form')
                let options = {
                    context: this.context,
                    conv_info: conv_info,
                    action_manager: this.action_manager,
                    form_name: this.conversation_info_forms
                }
                this.conv_info_form = new chat.ConversationForm(this, options)
                this.$tab_content_conv_info.empty()
                out = this.conv_info_form.appendTo(this.$tab_content_conv_info);
            } else {
                this.$tab_content_conv_info.html(QWeb.render('acrux_empty_tab', {notYourConv: true}))
            }
        } else {
            this.$tab_content_conv_info.html(QWeb.render('acrux_empty_tab'))
        }
        out.then(() => data && data.resolve && data.resolve())
        out.catch(() => data && data.reject && data.reject())
        return out
    },

    /**
     * Agrega el popover del chatroom
     * @returns {Promise}
     */
    addChatroomPopover: function() {
        let emoji_html = QWeb.render('acrux_chat_popover');
        this.$el.popover({
            trigger: 'manual',
            animation: true,
            html: true,
            title: function () {
                return 'nada';  // no tiene titulo
            },
            container: this.$('div#acrux_chat_main_view'),
            placement: 'left',  // no importa se situa con la funcion fixPopoverPosition
            content: this.popoverOptions.bind(this),
            template: emoji_html,
        }).on('show.bs.popover', () => {
            setTimeout(this.fixPopoverPosition.bind(this), 10);
        })
        $(window).resize(this.fixPopoverPosition.bind(this))
        return Promise.resolve()
    },

    /**
     * Corrige la posición del popover cerca del click del ratón
     */
    fixPopoverPosition: function() {
        if (!this.popoverOption) { return ''; }  // esto no debe pasar
        let popover = this.$('.o_acrux_chat_popover');
        if (popover.length) {
            let popover_data = popover[0].getBoundingClientRect()
            let msg_data = this.popoverOption.event.currentTarget.getBoundingClientRect()
            let position = {
                top: msg_data.top + msg_data.height,
                left: msg_data.left + msg_data.width
            }
            // si sobrepasa la pantalla se cambia de lugar
            if (position.top + popover_data.height > window.visualViewport.height) {
                position.top = msg_data.top - msg_data.height - popover_data.height
            }
            // si sobrepasa la pantalla se cambia de lugar
            if (position.left + popover_data.width > window.visualViewport.width) {
                position.left = msg_data.left - msg_data.width - popover_data.width
            }
            popover.offset(position)
            popover.css('z-index', 100) // para que no salga arriba de los wizard
        }
    },

    /**
     * El popover esta hecho genérico, entonces esta funcion agrega u contenido.
     * @returns {String}
     */
    popoverOptions: function() {
        return ''
    },

    /**
     * Ataja el click global en el chatroom para cerrar el popover
     * @param {Event} e evento
     */
    globalClick: function(e) {
        const ignoreIdList = this.globalClickIgnoreIdList();
        this.$('div.popover').each(function () {
            // hide any open popovers when the anywhere else in the body is clicked
            if (!$(this).is(e.target) && $(this).has(e.target).length === 0 && $('.popover').has(e.target).length === 0 &&
                    !ignoreIdList.includes($(e.target).attr('id'))) {
                $(this).popover('hide');
            }
        });
    },

    globalClickIgnoreIdList: function() {
        return ['o_chat_button_emoji'];
    },

    /**
     * Esta función se llama cuando llegan las notificaciones. Es la única funcion
     * que maneja las notificaiones y debería continuar así.
     *
     * @param {Array<Object>} data Lista de notificaciones
     */
    onNotification: function(data) {
        if (data) {
            data.forEach(d => this.notifactionProcessor(d));
        }
    },

    /**
     * Funcion parte de onNotification
     *
     * @param {Object} data Notificación
     */
    notifactionProcessor: function(data) {
        if (data.type === 'delete_conversation' && this.user_status.isActive()) {
            data.payload.forEach(m => this.onDeleteConversation(m))
        }
        if (data.type === 'delete_taken_conversation' && this.user_status.isActive()) {
            data.payload.forEach(m => this.onDeleteTakenConversation(m))
        }
        if (data.type === 'new_messages' && this.user_status.isActive()) {
            data.payload.forEach(m => this.onNewMessage(m));
        }
        if (data.type === 'init_conversation' && this.user_status.isActive()) {
            data.payload.forEach(m => this.onInitConversation(m));
        }
        if (data.type === 'change_status') {
            data.payload.forEach(m => this.onChangeStatus(m))
        }
        if (data.type === 'update_conversation' && this.user_status.isActive()) {
            data.payload.forEach(m => this.onUpdateConversation(m))
        }
        if (data.type === 'assign_conversation' && this.user_status.isActive()) {
            data.payload.forEach(m => this.addConversation(m));
        }
        if (data.type === 'error_messages' && this.user_status.isActive()) {
            this.onErrorMessages(data.payload)
        }
    },

    /**
     * Mensaje nuevo desde notificación el servidor
     * si la conversación no está, se agrega.
     * si la conversación está, se agrega los mensajes que vengan en la notificación
     * También envía una notificación de escritorio en caso de que no esté
     * posicionado en la pestaña con odoo
     *
     * @param {Object} d Data de la conversación, esta se pasará directamente
     *                   al constructor de Conversation
     * @returns {Promise}
     */
    onNewMessage: function(d) {
        let conv = this.conversations.find(x => x.id == d.id), def_out;
        if (conv) {
            conv.update(d);
            def_out = conv.addClientMessage(d.messages).then(() => {
                conv.incressNewMessage();
                if (this.selected_conversation === conv && !document.hidden && conv.isMine()) {
                    conv.messageSeen(); // marca mensaje como visto
                }
            })
        } else if (d.status == 'new') {
            conv = new chat.Conversation(this, d);
            this.conversations.unshift(conv);
            def_out = this.renderNewConversation(conv).then(() => {
                conv.incressNewMessage();
            })
        } else {
            def_out = Promise.resolve();
        }
        def_out.then(() => {
            if (conv && document.hidden) {
                if ('all' === d.desk_notify || ('mines' === d.desk_notify && conv.agent_id &&
                    conv.agent_id[0] == session.uid)) {
                    const msg = d.messages.filter(x => !x.from_me)
                    if (msg && msg.length) {
                        this.call('bus_service', 'sendNotification',
                            {title: _t('New messages from ') + conv.name} )
                    }
                }
            }
        })
        return def_out.then(() => conv);
    },

    /**
     * Actualiza los datos de la conversacion
     *
     * @param {Object} d Data de la conversación
     * @returns {Promise} con la conversacion dentro
     */
    onUpdateConversation: function(d) {
        let conv = this.conversations.find(x => x.id == d.id);
        if (conv) {
            let old_partner =  conv.res_partner_id;
            conv.update(d);
            conv.replace();
            if (this.$tab_content_partner.parent().hasClass('active') &&
                    this.selected_conversation == conv) {
                if (conv.res_partner_id[0] != old_partner[0]) {
                    this.tabPartner({currentTarget: false});
                } else {
                    this.res_partner_form.acrux_form_widget.reload();
                }
            }
            if (this.$tab_content_conv_info.parent().hasClass('active')) {
                this.conv_info_form.acrux_form_widget.reload();
            }
        }
        
        return Promise.resolve(conv);
    },

    /**
     * Elimina una conversación del chat, esto es requerido en caso como:
     * Si la conversación es nuevo y pasa a ser atendida por un usuario,
     * la conversación se borra del resto de los usuarios
     *
     * @param {Object} conv_data Conversación a eliminar
     * @returns {Promise}
     */
    onDeleteConversation: function(conv_data) {
        let out;
        if (conv_data.agent_id[0] != session.uid) {
            out = this.deleteConversation(conv_data);
        } else {
            out = Promise.resolve();
        }
        return out;
    },

    /**
     * Elimina una conversación del chat, esto es requerido en caso como:
     * Si el usuario tarda mucho en responder al cliente, el servidor determina
     * que la conversación debe ser liberada para que algún otro usuario la 
     * atienda, entonces, se borra la conversación del chat.
     *
     * @param {Object} conv_data Conversación a eliminar
     * @returns {Promise}
     */
    onDeleteTakenConversation: function(conv_data) {
        let out;
        if (conv_data.agent_id[0] == session.uid) {
            out = this.deleteConversation(conv_data);
        } else {
            out = Promise.resolve();
        }
        return out;
    },

    /**
     * Esta función agrega una conversación y la selección como actual.
     * En general es llamada por una notifiación del servidor y permite
     * inicir conversaciones por parte del chat.
     *
     * @param {Object} conv_data Conversación a iniciar.
     * @returns {Promise<chat.Conversation>}
     */
    onInitConversation: function(conv_data) {
        return this.addConversation(conv_data).then(conv => {
            this.showConversationPanel()
            return this.selectConversation({ currentTarget: conv.el }).then(() => conv)
        })
    },
    
    /**
     * Agrega una conversaciones
     *
     * @param {Object} conv_data Conversación a iniciar.
     * @returns {Promise<chat.Conversation>}
     */
    addConversation: function(conv_data) {
        let conv = this.conversations.find(x => x.id == conv_data.id), def;

        if (conv) {
            if (conv.status == 'new') {
                this.deleteConversation(conv);
                conv = null;
            } else {
                if (this.selected_conversation
                    && this.selected_conversation.id != conv.id) {
                    conv.setMessages(conv_data.messages);
                }
            }
        }
        if (!conv) {
            conv = new chat.Conversation(this, conv_data);
            this.conversations.unshift(conv);
            if (conv.status == 'new') {
                def = this.renderNewConversation(conv);
            } else {
                if (conv.isMine()) {
                    def = conv.appendTo(this.$current_chats);
                } else {
                    def = this.renderNewConversation(conv);
                }
            }
        } else {
            conv.update(conv_data);
            def = Promise.resolve();
        }
        return def.then(() => conv);
    },

    /**
     * Cuando el chat cambia a activo/inactivo se genera una notificación,
     * para el caso que tenga el chat en varias pestañas, se inactivan/activan
     * todas las instancias
     *
     * @param {Object} data El usuario que cambia de estatus.
     */
    onChangeStatus: function(data) {
        if (data.agent_id[0] == session.uid) {
            this.user_status.changeStatusNotify(data);
            this.toolbox.changeStatusNotify(data);
            this.changeStatusView();
        }
    },

    /**
     * Llega notificación de conversaciones con mensajes con errores.
     * Se agrega a cada notificación el motivio del error en el mensaje 
     * correspondiente y si la entre las conversaciones con error no está
     * presente la conversación por la que se está escribiendo. Se muestra
     * un mensaje de error y al presionar "ok", se selecciona la conversación
     * con error y se hace scroll hasta el mensaje con error.
     * Funciona muy bien con una conversación con error y un mensaje.
     * En caso que haya más de una conversación se selecciona cualquiera.
     *
     * @param {Object} error_messages Conversaciones con errores
     */
    onErrorMessages: function(error_messages) {
        let conv_found = [], message_found, show_conv = true;
        let conv_to_show, msg_to_show;
        error_messages.forEach(conv_data => {
            let conv = this.conversations.find(x => x.id == conv_data.id);
            if (conv) {
                conv.update(conv_data);
                message_found = conv.setMessageError(conv_data.messages);
                conv_found.push(conv);
                if (this.selected_conversation && this.selected_conversation.id == conv.id) {
                    show_conv = false;
                } else if (conv.status == 'current') {
                    conv_to_show = conv;
                    if (message_found.length) {
                        msg_to_show = message_found[0];
                    }
                }
            }
        });
        if (conv_found.length) {
            let msg = _t('Error in conversation with ');
            conv_found.forEach((val, index) => {
                if (index) {
                    msg += ', ';
                }
                msg += val.name;
            });
            Dialog.alert(this, msg, {
                confirm_callback: () => {
                    if (show_conv && conv_to_show) {
                        this.selectConversation({ currentTarget: conv_to_show.el }).then(() => {
                            msg_to_show.el.scrollIntoView({block: 'nearest', inline: 'start' });
                        });
                    }
                }
            });
        }
    },

    /**
     * Borra una conversación de la lista de conversaciones.
     *
     * @param {Object} conv_data Conversación a borrar
     * @returns {Promise}
     */
    deleteConversation: function(conv_data) {
        let conv = this.conversations.find(x => x.id == conv_data.id);
        this.conversations = this.conversations.filter(x => x.id != conv_data.id);
        if (conv) {
            if (conv == this.selected_conversation) {
                this.removeSelectedConversation();
            } else {
                conv.destroy();
            }
        }
        return Promise.resolve(conv);
    },

    /**
     * Borra la conversación seleccionada. Nota: en el chat solo puede haber una 
     * conversación seleccionada que es la que se están ateniendo.
     */
    removeSelectedConversation: function() {
        if (this.selected_conversation) {
            this.conversations = this.conversations.filter(x => x.id != this.selected_conversation.id);
            this.selected_conversation.destroy();
            this.selected_conversation = null;
        }
        this.toolbox.do_hide();
        this.tabsClear();
    },

    /**
     * Retorna si la tab actual tiene que recargarse.
     *
     * @returns {Boolean}
     */
    tabNeedReload: function() {
        return (!this.$tab_default_answer.parent().hasClass('active') &&
                    !this.$tab_init_chat.hasClass('active'));
    },

    /**
     * Trata de destruir un widget de forma segura
     */
    saveDestroyWidget: function(name) {
        if (this && this[name]) {
            let tmp_form = this[name]
            this[name] = null;
            tmp_form.destroy();
        }
    },

    /**
     * Posiciona el primer tab como activo y destruye la información innecesario
     * de los demás tabs, esto es para evita llamadas innecesarias al servidor
     * y siempre partir desde el mismo punto en cada conversación.
     */
    tabsClear: function() {
        if (this.tabNeedReload()) {
            this.$first_main_tab.trigger('click');
        }
        this.saveDestroyWidget('res_partner_form')
        this.saveDestroyWidget('conv_info_form')
    },

    /**
     * @see web.mail.chat_client_action.ChatAction._onCloseNotificationBar
     */
    _onCloseNotificationBar: function() {
        this.$(".o_acrux_chat_notification").slideUp();
    },

    /**
     * @see web.mail.chat_client_action.ChatAction._onRequestNotificationPermission
     */
    _onRequestNotificationPermission: function(event) {
        event.preventDefault();
        this.$(".o_acrux_chat_notification").slideUp();
        var def = window.Notification && window.Notification.requestPermission();
        if (def) {
            def.then((value) => {
                if (value !== 'granted') {
                    this.call('bus_service', 'sendNotification', {
                        title: _t('Permission denied'),
                        message: this.company_name + _t(' will not have the permission to send native notifications on this device.') 
                    });                    
                } else {
                    this.call('bus_service', 'sendNotification', {
                        title: _t('Permission granted'),
                        message: this.company_name + _t(' has now the permission to send you native notifications on this device.') 
                    });
                }
            });
        }
    },
    
    /**
     * Las tabs que se maximizan
     */
    _getMaximizeTabs: function() {
        return ["#tab_content_partner",
                "#tab_content_conv_info"];
    }

});

var CreateNewConversation = function (self, action, _options) {
    self.services.action.doAction({type: 'ir.actions.act_window_close'}).then(() =>
        chat_is_read.then(widget => widget.init_conversation.createConversation({context: action.context}))
    )
}

core.action_registry.add('acrux.chat.create_new_conversation', CreateNewConversation);

core.action_registry.add('acrux.chat.conversation_tag', AcruxChatAction);

return {AcruxChatAction: AcruxChatAction, is_ready: chat_is_read};
});
