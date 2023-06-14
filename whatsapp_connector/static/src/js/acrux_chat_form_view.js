odoo.define('whatsapp_connector.form_view', function(require) {
"use strict";

var Widget = require('web.Widget');
var dom = require('web.dom');
var core = require('web.core');

var _t = core._t;

/**
 * Widget para poder agregar formularios odoo en el chat 
 *
 * @class
 * @name FormView
 * @extends web.Widget
 */
var FormView = Widget.extend({
    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, options) {
        this._super.apply(this, arguments);

        this.parent = parent;
        this.options = _.extend({}, options);
        this.context = _.extend({}, this.parent.context || {}, this.options.context);
        if (this.parent.selected_conversation) {
            this.context.default_conversation_id = this.parent.selected_conversation.id;
        }
        this.model = this.options.model;
        this.form_name = this.options.form_name;
        this.record = this.options.record;
        this.action_manager = this.options.action_manager;
        this.title = this.options.title;
        this.acrux_form_widget = null;
        this.action = {};
        this.created_date = new Date();
        this.env = this.parent.env
    },

    /**
     * @override
     * @see Widget.start
     */
    start: function() {
        return this._super()
        .then(() => this.do_action(this.getDoActionDict(),this.getOptions()))
        .then(() => {
            const currentController =  this.action_manager.actionService.currentController;
            this.action = currentController.action
            this.acruxComponent = currentController
            if (this.action.controllers.form) {
                this.acrux_form_widget = currentController.acrux_comp.componentRef.comp.controllerRef.comp.widget;
                this.acrux_form_widget.acrux_widget = this;
                this._showAcruxFormView();
            }
            return currentController.action
        })
    },

    /**
     * @override
     */
    destroy: function() {
        return this._super();
    },

    /**
     * Construye el diccionario para llamar a la acción de odoo
     *
     * @returns {Object}
     */
    getDoActionDict: function() {
        return {
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'form',
            res_model: this.model,
            views: [[this.form_name, 'form']],
            target: 'inline',
            context: this.context,
            res_id: this.record[0],
            flags: this.getDoActionFlags(),
            name: this.title,
        };
    },

    /**
     * Construye diccionario con los flags para el formulario
     *
     * @returns {Object}
     */
    getDoActionFlags: function() {
        let flags = {
            withControlPanel: false,
            footerToButtons: false,
            hasSearchView: false,
            hasSidebar: false,
            mode: 'edit',
            searchMenuTypes: false,
        };
        if (this.record[0]) {
            flags.mode = 'readonly';
        }
        return flags;
    },

    /**
     * Construye las opciones para las acciones
     *
     * @returns {Object}
     */
    getOptions: function() {
        const out = {
            clearBreadcrumbs: false,
        }
        const currentController =  this.action_manager.actionService.currentController;
        if (currentController.acrux_comp) {
            out.stackPosition = 'replaceCurrentAction'
        }
        return out
    },

    /**
     * Muestra el formulario
     *
     * @returns {Promise}
     */
    _showAcruxFormView: function() {
        let $buttons = $('<div>');
        dom.append(this.$el, this.acrux_form_widget.$el, {
            in_DOM: true,
            callbacks: [{ widget: this }, { widget: this.acrux_form_widget }],
        });
        this.acrux_form_widget.renderButtons($buttons)
        $buttons.find('.o_form_button_create').click(() => this._onCreate());
        $buttons.find('.o_form_button_edit').click(() => this._onEdit());
        this.$el.prepend($buttons.contents());
        // estilo para la barra de los botones
        this.$el.children().first().css('padding', '5px');
        this.$el.children().first().css('background', 'white');
        if (this.options.searchButton) {
            this._addSearchButton()
        }
        if (this.makeDropable()) {
            this.makeFormDragAndDrop()
        }
        return Promise.resolve();
    },

    /**
     * Permite lanzar cosas al formulario
     * @return {Boolean}
     */
    makeDropable: function() {
        return false
    },

    /**
     * Retorna si se acepta el objeto a lanzar
     * @param {Jquery} ui Elemento jquery
     * @returns {Boolean}
     */
    acceptDrop: function(_ui) {
        return false
    },

    /**
     * Se encarga los objetos que se lanzan 
     * @param {Event} event evento de arrastre
     * @param {Jquery} ui Elemento jquery
     * @returns {Promise}
     */
    handlerDradDrop: function(_event, _ui) {
        return Promise.resolve()
    },

    /** 
     * Hace que la seccion de formularios sea drag an drop
     */
    makeFormDragAndDrop: function() {
        this.$el.css('padding', '0.5em');
        this.$el.droppable({
            drop: (event, ui) => this.handlerDradDrop(event, ui),
            accept: (ui) => this.acceptDrop(ui),
            activeClass: 'drop-active',
            hoverClass: 'drop-hover',
        });
    },

    /**
     * Agrega el boton buscar a la vistas formulario si se pasa por opciones.
     * @private
     */
    _addSearchButton: function() {
        this.$el.children().first().children().append(
        '<button type="button" class="btn btn-primary o_form_button_search">'
            + (this.options.searchButtonString || _t('Search')) +
        '</button>'
        );
        this.$el.find('.o_form_button_search').click(() => this._onSearchChatroom());
    },

    /**
     * Maneja el evento del boton buscar en la vista formualio
     * @private
     * @return {Promise}
     */
    _onSearchChatroom: function() {
        let context = _.extend({ chatroom_wizard_search: true }, this.context);

        let action = {
            type: 'ir.actions.act_window',
            view_type: 'form',
            view_mode: 'list',
            res_model: this.model,
            domain: this._getOnSearchChatroomDomain(),
            views: [[false, 'list']],
            target: 'new',
            context: context,
            flags: {
                action_buttons: false,
                withBreadcrumbs: false,
            },
            _chatroomSelectRecord: (record) => {
                if (record) {
                    return this.recordUpdated(record)
                        .then(() => this.replace())
                        .then(() => this._onSearchChatroomCallBack(record))
                        .then(record)
                }
            }
        }
        return this.do_action(action)
    },

    /**
     * Retorna el domain para el boton buscar el los formularios.
     * Esta pensado para que cada formulario los reescriba con su domain
     * @private
     * @returns {Array<Array<Object>>}
     */
    _getOnSearchChatroomDomain: function() {
        return []
    },

    /**
     * Esa funcion se llama luego de que se lecciona una registro la accion de buscar
     * @private
     * @param {Object} record un registro de odoo tipo record.data
     * @returns {Promise}
     */
    _onSearchChatroomCallBack: function(record) {
        return Promise.resolve()
    },

    /**
     * Funcion que se llama luego de mostrar el formulario en patalla, 
     * es llamada por el dom
     */
    on_attach_callback: function() {
        this.$el.css('height', '100%');
        this.$el.children().first().css('position', 'relative');
        this.$el.children().first().css('height', '92%');
        this.$el.children().first().css('overflow', 'auto');
        this._fix_attach();
    },

    /**
     * Corrige el css de sheet
     */
    _fix_attach: function() {
        this.$('.o_form_sheet').eq(0).css('padding', '0 1em');
        this.$('.o_form_sheet').children().first().css('margin', '0');
        this.$('.o_FormRenderer_chatterContainer').hide();
    },

    /**
     * Luego de identificar el formulario que se actualizó se llama esta fución
     *
     * @param {Object} record Record actualizado
     * @returns {Promise}
     */
    recordUpdated: function(record) {
        this._fix_attach();
        if (record && record.data && this.record && this.record[0] != record.data.id) {
            return this.recordChange(record);
        }
        return Promise.resolve();
    },

    /**
     * Se llama si el registro cambió, debería guardar el dato
     *
     * @param {Object} record Registro con la información del formulario
     * @returns {Promise}
     */
    recordChange: function(record) {
        return Promise.resolve();
    },

    /**
     * Se llama si el registro se guardó
     *
     * @param {Object} record Registro con la información del formulario
     * @returns {Promise}
     */
    recordSaved: function(record) {
        return Promise.resolve();
    },

    /**
     * Se trata de no actualizar el formulario del mismo cliente repetidas veces.
     * Se pone un límite de 3 horas para actualizarlo con los datos del servidor.
     */
    isExpired: function() {
        let hour = 3;
        let hour_mili = hour * 60 * 60 * 1000;
        let now = new Date();
        return (now - this.created_date) >= hour_mili;
    },

    /**
     * Retorna si el id por parametros es el mismo que el del record del widget
     *
     * @param {Number} record_id Id para comparar
     * @returns {Boolean}
     */
    isSameRecord: function(record_id) {
        return this.record[0] == record_id;
    },

    /**
     * Cuando se presiona el botón crear en el formulario se llama esta funcion
     */
    _onCreate: function() {
        this.old_record = Array.from(this.record);
    },

    /**
     * Cuando se presiona el botón editar en el formulario se llama esta funcion
     */
    _onEdit: function() {
        this.old_record = null;
    },

    /**
     * Esta función es invocada por un evento que se lanza cuando se descarta,
     * los datos en el formulario, pare el caso del chat, se reacarga el formulario
     * con los datos del antiguo registro que se estaba editando.
     */
    discardChange: function() {
        if (this.old_record) {
            let options = this.getDoActionFlags();
            options.currentId = this.old_record[0];
            options.ids = [this.old_record[0]];
            options.context = this.context;
            options.modelName = this.model;
            options.mode = 'readonly';
            this.acrux_form_widget.reload(options);
            this.old_record = null;
        }
    },

    /**
     * Actualiza la vista ford con el ID que se le pasa
     * @param {Number} Id para actualizar el formulario
     * @returns {Promise}
     */
    update: function(recordId) {
        let out = Promise.resolve() 
        if (this.acrux_form_widget) {
            // no parece hacer falta pero me dio error en un momento
            out = this.acrux_form_widget.update({currentId: recordId})
        }
        return out
    },

    /**
     * hook para procesar el context
     * @private
     */
    _context_hook: function() {
        
    },

    /**
     * Devuelve si el jsId es de mi controlador
     * @param {String} jsId id del controllador
     * @returns {Boolean}
     */
    isMyController: function(jsId) {
        return this.action && this.action.controllers && this.action.controllers.form && this.action.controllers.form.jsId === jsId
    }
});

return FormView;
});
