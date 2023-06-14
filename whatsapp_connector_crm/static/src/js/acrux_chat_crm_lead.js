odoo.define('whatsapp_connector_crm.crm_lead', function(require) {
"use strict";

var session = require('web.session');
var FormView = require('whatsapp_connector.form_view');

/**
 * Widget que maneja el formulario del CRM
 *
 * @class
 * @name ResPartnerForm
 * @extends whatsapp.FormView
 * @see whatsapp.FormView
 */
var CrmLeadForm = FormView.extend({
    /**
     * @override
     * @see Widget.init
     */
    init: function(parent, options) {
        if (options) {
            options.model = 'crm.lead';
            options.record = options.crm_lead;
        }
        this._super.apply(this, arguments);

        this.parent = parent;
        const default_values = {
            default_partner_id: this.parent.selected_conversation.res_partner_id[0],
            default_phone: this.parent.selected_conversation.number_format,
            default_mobile: this.parent.selected_conversation.number_format,
            default_name: this.parent.selected_conversation.connector_id[1] + ': ' + this.parent.selected_conversation.name,
            default_contact_name: this.parent.selected_conversation.name,
            default_user_id: session.uid,
        }
        if (this.parent.selected_conversation.team_id[0]) {
            default_values['default_team_id'] = this.parent.selected_conversation.team_id[0]
        }
        _.defaults(this.context, default_values);
        this._context_hook()
    },

    /**
     * @override
     * @see FormView.start
     */
    start: function() {
        return this._super().then(() => this.parent.product_search.minimize());
    },

    /**
     * @override
     * @see FormView.recordUpdated
     * @returns {Promise}
     */
    recordUpdated: function(record) {
        return this._super(record).then(() => {
            if (record && record.data && record.data.id) {
                let crm_key, partner_key, partner_id, localData;
                crm_key = this.acrux_form_widget.handle;
                localData = this.acrux_form_widget.model.localData;
                if (crm_key) {
                    partner_key = localData[crm_key].data.partner_id;
                }
                if (partner_key) {
                    partner_id = localData[partner_key];
                }
                this.parent.setNewPartner(partner_id);
            }
        });
    },

    /**
     * @override
     * @see FormView.recordChange
     * @returns {Promise}
     */
    recordChange: function(crm_lead) {
        return Promise.all([
            this._super(crm_lead),
            this._rpc({
                model: this.parent.model,
                method: 'write',
                args: [[this.parent.selected_conversation.id], {crm_lead_id: crm_lead.data.id}],
                context: this.context
            }).then(isOk => {
                if (isOk) {
                    let result = [crm_lead.data.id, crm_lead.data.name];
                    this.parent.selected_conversation.crm_lead_id = result;
                    this.record = result;
                }
            })
        ]);
    },

    /**
     * @override
     * @see FormView._getOnSearchChatroomDomain
     * @returns {Array<Array<Object>>}
     */
    _getOnSearchChatroomDomain: function() {
        /** @type {Array} */
        let domain = this._super()
        domain.push(['conversation_id', '=', this.parent.selected_conversation.id])
        if (this.parent.selected_conversation.res_partner_id && this.parent.selected_conversation.res_partner_id[0]) {
            domain.unshift('|')
            domain.push(['partner_id', '=', this.parent.selected_conversation.res_partner_id[0]])
        }
        return domain
    },

})

return CrmLeadForm
})
