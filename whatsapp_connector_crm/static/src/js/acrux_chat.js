odoo.define('whatsapp_connector_crm.acrux_chat', function(require) {
"use strict";

var chat = require('whatsapp_connector.chat_classes');
var AcruxChatAction = require('whatsapp_connector.acrux_chat').AcruxChatAction
var core = require('web.core');

var _t = core._t;
var QWeb = core.qweb;

/**
 * @class
 * @name AcruxChatAction
 * @extends whatsapp.AcruxChatAction
 */
AcruxChatAction.include({
    events: _.extend({}, AcruxChatAction.prototype.events, {
        'click li#tab_crm_lead': 'tabCrmLead',
    }),

    /**
     * Hace trabajos de render
     *
     * @private
     * @returns {Promise} Para indicar que termino
     */
    _initRender: function() {
        return this._super().then(() => {
            this.$tab_content_lead = this.$('div#tab_content_crm_lead > div.o_group');
        });
    },

    /**
     * Cuando se hace clic en el tab de CRM, se muestra un formulario
     * de crm.lead
     *
     * @param {Event} _event
     * @param {Object} data
     * @return {Promise}
     */
    tabCrmLead: function(_event, data) {
        let out = Promise.reject()
        
        if (this.selected_conversation) {
            if (this.selected_conversation.isMine()) {
                let lead_id = this.selected_conversation.crm_lead_id;
                this.saveDestroyWidget('crm_lead_form')
                let options = {
                    context: this.action.context,
                    crm_lead: lead_id,
                    action_manager: this.action_manager,
                    searchButton: true,
                    title: _t('CRM'),
                }
                this.crm_lead_form = new chat.CrmLeadForm(this, options)
                this.$tab_content_lead.empty()
                out = this.crm_lead_form.appendTo(this.$tab_content_lead);
            } else {
                this.$tab_content_lead.html(QWeb.render('acrux_empty_tab', {notYourConv: true}))
            }
        } else {
            this.$tab_content_lead.html(QWeb.render('acrux_empty_tab'))
        }
        out.then(() => data && data.resolve && data.resolve())
        out.catch(() => data && data.reject && data.reject())
        return out
    },

    /**
     * @override
     * @see AcruxChatAction.tabsClear
     */
    tabsClear: function() {
        this._super();
        this.saveDestroyWidget('crm_lead_form')
    },
    
    /**
     * @override
     * @see AcruxChatAction._getMaximizeTabs
     */
    _getMaximizeTabs: function() {
        let out = this._super();
        out.push("#tab_content_crm_lead")
        return out;
    },

    /**
     * Devuelve si el controlador es parte de chatroom, es util para los tabs
     * @param {String} jsId id del controllador
     * @returns {Boolean}
     */
    isChatroomTab: function(jsId) {
        return this._super(jsId) || this._isChatroomTab('crm_lead_form', jsId)
    },
})

return AcruxChatAction

})
