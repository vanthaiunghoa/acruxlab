odoo.define('whatsapp_connector.ListController', function (require) {
"use strict";

var core = require('web.core');
var ListController = require('web.ListController');
var _t = core._t;

ListController.include({
    
    renderButtons: function ($node) {
        let out = this._super($node)
        if (this.renderer.state.context.chatroom_wizard_search && $node) {
            // se pregunta por $node para solo renderizar select en el fotter
            $node.html(`<button type="button" class="btn btn-primary btn-chatroom-wizard-select">${_t('Select')}</button>`)
            $node.find('.btn-chatroom-wizard-select').attr('disabled', 'disabled');
            $node.find('.btn-chatroom-wizard-select').click(this._chatroomSelectRow.bind(this))
            this.$acrux_footer = $node
        }
        return out
    },
    
    _onSelectionChanged: function(event) {
        this._super(event)
        if (this.renderer.state.context.chatroom_wizard_search) {
            if (this.selectedRecords && this.selectedRecords.length == 1) {
                this.$acrux_footer.find('.btn-chatroom-wizard-select').removeAttr('disabled');
            } else {
                this.$acrux_footer.find('.btn-chatroom-wizard-select').attr('disabled', 'disabled');
            }
        }
    },

    _chatroomSelectRow: function(event) {
        event.preventDefault();
        if (this.selectedRecords && this.selectedRecords.length == 1) {
            const record = this.model.get(this.selectedRecords[0], {env: false})
            if (record) {
                this.getParent().props.viewParams.action._chatroomSelectRecord(record)
            }
        }
    },
    
    _onOpenRecord: function (ev) {
        if (!this.renderer.state.context.chatroom_wizard_search) {
            this._super(ev)
        } else {
            ev.stopPropagation()
        }
    }
})

return ListController
})