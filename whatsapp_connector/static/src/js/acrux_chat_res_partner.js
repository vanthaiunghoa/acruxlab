odoo.define('whatsapp_connector.res_partner', function(require) {
"use strict";

var session = require('web.session');
var FormView = require('whatsapp_connector.form_view');


/**
 * Widget que maneja el formulario del cliente
 *
 * @class
 * @name ResPartnerForm
 * @extends web.Widget.FormView
 * @see acrux_chat.form_view
 */
var ResPartnerForm = FormView.extend({
    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, options) {
        if (options) {
            options.model = 'res.partner';
            options.record = options.res_partner;
        }
        this._super.apply(this, arguments);

        this.parent = parent;
        _.defaults(this.context, {
            default_mobile: this.parent.selected_conversation.number_format,
            default_phone: this.parent.selected_conversation.number_format,
            default_name: this.parent.selected_conversation.name,
            default_user_id: session.uid,
        });
        this._context_hook()
    },

    /**
     * @override
     * @see FormView.start
     */
    start: function() {
        return this._super().then(() => {
            this.parent.product_search.minimize();
        });
    },

    /**
     * @override
     * @see FormView.recordChange
     * @returns {Promise}
     */
    recordChange: function(res_partner) {
        return Promise.all([
            this._super(res_partner),
            this._rpc({
                model: this.parent.model,
                method: 'write',
                args: [[this.parent.selected_conversation.id], {res_partner_id: res_partner.data.id}],
                context: this.context
            }).then(() => this._rpc({
                model: this.parent.model,
                method: 'read',
                args: [[this.parent.selected_conversation.id], ['image_url']],
                context: this.context
            }).then(img_url => {
                let result = [res_partner.data.id, res_partner.data.name];
                this.record = result;
                this.parent.selected_conversation.res_partner_id = result;
                this.parent.selected_conversation.image_url = img_url[0].image_url;
                this.parent.selected_conversation.replace();
            }))
        ]);
    },

    /**
     * @override
     * @see FormView.recordSaved
     * @returns {Promise}
     */
    recordSaved: function(record) {
        return this._super(record).then(() => {
            return this._rpc({
                model: this.parent.model,
                method: 'update_conversation_bus',
                args: [[this.parent.selected_conversation.id]],
                context: this.context
            });
        });
    },

})

return ResPartnerForm
})
