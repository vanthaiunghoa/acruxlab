odoo.define('whatsapp_connector.tree_view', function(require) {
"use strict";

var FormView = require('whatsapp_connector.form_view');
var dom = require('web.dom');

/**
 * Widget para poder agregar tree odoo en el chat 
 *
 * @class
 * @name FormView
 * @extends web.Widget
 */
var TreeView = FormView.extend({
    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, options) {
        this._super.apply(this, arguments);
    },

    /**
     * @override
     * @see Widget.start
     */
    start: function() {
        return this._super().then(action => {
            if (this.action.controllers.list) {
                this.acrux_form_widget = this.acruxComponent.acrux_comp.componentRef.comp.controllerRef.comp.widget;
                this.acrux_form_widget.acrux_widget = this;
                this._showAcruxFormView();
            }
            return action;
        });
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
            view_mode: 'list',
            res_model: this.model,
            views: [[this.form_name, 'list'], [false, 'search']],
            target: 'inline',
            context: this.context,
            flags: this.getDoActionFlags(),
        };
    },

    /**
     * Construye diccionario con los flags para la acción
     *
     * @returns {Object}
     */
    getDoActionFlags: function() {
        let flags = {
            withControlPanel: true,
            footerToButtons: false,
            hasSearchView: true,
            hasSidebar: false,
            searchMenuTypes: ['filter', 'groupBy'],
            withSearchPanel: true,
            withSearchBar: true,
        };
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
     * Muestra vista
     *
     * @returns {Promise}
     */
    _showAcruxFormView: function() {
        dom.append(this.$el, this.acrux_form_widget.$el, {
            in_DOM: true,
            callbacks: [{ widget: this }, { widget: this.acrux_form_widget }],
        });
        return Promise.resolve();
    },

    /**
     * Funcion que se llama luego de mostrar la vista en patalla, 
     * es llamada por el dom
     */
    on_attach_callback: function() {
        this.$('.breadcrumb').hide();
    },

    /**
     * Devuelve si el jsId es de mi controlador
     * @param {String} jsId id del controllador
     * @returns {Boolean}
     */
    isMyController: function(jsId) {
        return this.action && this.action.controllers && this.action.controllers.list && this.action.controllers.list.jsId === jsId
    },

});

return TreeView;
});