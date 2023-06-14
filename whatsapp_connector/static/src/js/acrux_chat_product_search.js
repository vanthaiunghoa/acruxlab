odoo.define('whatsapp_connector.product_search', function(require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');
var field_utils = require('web.field_utils');
var _t = core._t;

var QWeb = core.qweb;

/**
 * Widget para buscar y mostrar los productos en el chat
 *
 * @class
 * @name ProductSearch
 * @extends web.Widget
 */
var ProductSearch = Widget.extend({
    template: 'acrux_chat_product_search',
    events: {
        'click .o_button_product_search': 'searchProduct',
        'keypress .product_search': 'onKeypress',
        'click .acrux-product-send-btn': 'productOptions',
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

        this.product_list = this.options.product_list || [];
        this.is_minimize = false
        this.env = this.parent.env
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
        this.$el.resizable({
            handles: 's',
            stop: (e, ui) => {
                this.calculateFomrSize(ui.element.height())
            }
         }); // para redimensionar el div de los productos
        this.$input_search_product = this.$('input.product_search');
        this.$input_search_product.focus(() => this.maximize());
        this.$product_items = this.$('.o_acrux_chat_product_items');
        this.makeProductDragAndDrop();
        return Promise.resolve();
    },

    /**
     * Permite arrastrar el producto al chat
     */
    makeProductDragAndDrop: function() {
        this.parent.$chat_message.droppable({
            drop: (_event, ui) => {
                if (this.parent.selected_conversation &&
                    this.parent.selected_conversation.isMine()) {
                    let product = this.find(ui.draggable.data('id'));
                    if (product) {
                        this.sendProduct(product);
                    }
                }
            },
            accept: '.o_product_record',
            activeClass: 'drop-active',
            hoverClass: 'drop-hover',
        });
    },

    /**
     * Envía al cliente el producto que fue arrastrado al chat
     *
     * @param {Object} product Producto que se enviará
     * @returns {Promise} de la creación del producto
     */
    sendProduct: function(product) {
        let options = {
            from_me: true, ttype: 'product', res_model: 'product.product',
            res_id: product.id, res_model_obj: product,
        };
        return this.parent.selected_conversation.createMessage(options);
    },

    /**
     * Busca los productos y los muestra
     * @return {Promise}
     */
    searchProduct: function() {
        let val = this.$input_search_product.val() || '';
        return this._rpc({
            model: this.parent.model,
            method: 'search_product',
            args: [val.trim()],
            context: this.context
        }).then(result => {
            result.forEach(x => {
                x.lst_price = this.parent.format_monetary(x.lst_price);
                x.write_date = field_utils.parse.datetime(x.write_date);
                x.unique_hash_image = field_utils.format.datetime(x.write_date).replace(/[^0-9]/g, '');
                x.show_product_text = true
            })
            let html = QWeb.render('acrux_chat_product_list', { product_list: result });
            this.product_list = result;
            this.$product_items.html(html);
            this.$product_items.children().draggable({
                revert: true,
                revertDuration: 0,
                containment: this.parent.$el,
                appendTo: this.parent.$el,
                helper: 'clone',
            });
        });
    },

    /**
     * Busca los productos cuando se presiona enter
     *
     * @param {Event} event
     */
    onKeypress: function(event) {
        if (event.which === 13) {
            if ($(event.currentTarget).hasClass('product_search')) {
                event.preventDefault();
                this.searchProduct();
            }
        }
    },

    /**
     * Minimza la zona de productos 
     */
    minimize: function() {
        if (!this.is_minimize) {
            const height = this.$('.o_acrux_chat_sidebar_title').height()
            this.$el.animate({ height: height }, 500)
            this.calculateFomrSize(height)
        }
    },

    /**
     * Calcula el tamaño del area de las pestañas
     * @param {Number} offset 
     */
    calculateFomrSize: function(offset) {
        let headSize = $(".o_acrux_chat .o_acrux_group > .o_notebook > .o_notebook_headers").height()
        $(".o_acrux_chat .o_acrux_group > .o_notebook > .tab-content").css({'height': `calc(100% - ${headSize}px)`})
        $(".o_acrux_chat .o_acrux_group > .o_notebook > .tab-content").parent().parent().css({'height': `calc(100% - ${offset}px)`})
        this.is_minimize = true;
    },

    /**
     * Maximiza la zona de productos
     */
    maximize: function() {
        if (this.is_minimize) {
            this.$el.animate({ height: '30%' }, 500)
            $(".o_acrux_chat .o_acrux_group > .o_notebook > .tab-content").parent().parent().css({'height': '70%'})
            $(".o_acrux_chat .o_acrux_group > .o_notebook > .tab-content").css({'height':'calc(100% - 3em)'})
            this.is_minimize = false
        }
    },

    /**
     * Encuentra un producto por su id
     *
     * @param {Integer} product_id Id del producto
     * @returns {Object} Producto encontrado
     */
    find: function(product_id) {
        return this.product_list.find(x => x.id == product_id);
    },
    
    /**
     * Funcion que se llama desde el botón opciones en el producto del chat
     *
     * @param {Event} event Evento de ratón
     * @returns {Promise} Promesa de la acción.
     */   
    productOptions: function(event) {
        let $el = $(event.target);
        let product_id = $el.parent().parent().data('id');
        let out

        if (this.parent.selected_conversation) {
            if (this.parent.selected_conversation.isMine()) {
                let product = this.find(product_id);
                if (product) {
                    out = this.doProductOption(product, event);
                } else {
                    out = Promise.resolve()
                }
            } else {
                this.env.services.crash_manager.show_warning({message: _t('Yoy are not writing in this conversation.')})
                out = Promise.reject();
            }
        } else {
            this.env.services.crash_manager.show_warning({message: _t('You must select a conversation.')})
            out = Promise.reject();
        }
        return out;
    },
    
    /**
     * Ejecuta la accion del boton en el producto
     * @param {String} product el producto a procesar
     * @param {Event} _event el evento que se ejecutó
     * @return {Promise}
     */
    doProductOption: function(product, _event) {
        return this.sendProduct(product).then(() => this.parent.hideRightPanel())
    }
});

return ProductSearch;
});
