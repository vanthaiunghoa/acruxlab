odoo.define('whatsapp_connector.BasicController', function(require) {
"use strict";

var BasicController = require('web.BasicController');

/**
 * Se extiende para poder retornar al registro previo a darle al botón
 * crear en los formulrios.
 *
 * @class
 * @name BasicController
 * @extends web.BasicController.BasicController
 */
BasicController.include({
    /**
     * @override
     * @private
     * @see FieldOne2Many._setValue
     * @returns {Promise}
     */
    _discardChanges: function(recordID, options) {
        return this._super(recordID, options).then(_x => {
            if (this.acrux_widget) {
                let env = this.model.get(this.handle, {env: true});
                if (!recordID && !env.currentId) {
                    this.acrux_widget.discardChange();
                }
            }
            return _x;
        });
    },

    /**
     * @override
     * @returns {Promise}
     */
    update: function(params, options) {
        return this._super(params, options).then(_x => {
            if (this.acrux_widget) {
                let record = this.model.get(this.handle, {env: false});
                return this.acrux_widget.recordUpdated(record).then(() => {
                    return _x;
                });
            }
            return _x;
        });
    },

    /**
     * @override
     * @private
     */
    _pushState: function(state) {
        let context = this.model.get(this.handle).getContext();
        if (!context.is_acrux_chat_room) {
            this._super(state);
        }
    },

    /**
     * @override
     */
    saveRecord: function (recordID, options) {
        return this._super(recordID, options).then(_x => {
            let action = {}
            if (this.getParent().props && this.getParent().props.viewParams) {
                action = this.getParent().props.viewParams.action
            } 
            if (action.acrux_init_conv) {
                let env = this.model.get(this.handle, {env: true});
                action.acrux_init_conv(env.currentId);
            }
            if (this.acrux_widget) {
                let record = this.model.get(this.handle, {env: false});
                return this.acrux_widget.recordSaved(record).then(() => {
                    return _x;
                });
            }
            return _x;
        });
    },

    /**
     * @override
     * Para cuando se guarda un campo many2many se refresque la conversacion
     */
    _onFieldChanged: function (event) {
        if (event?.data?.dataPointID) {
            const model = event.data.dataPointID.split('_')[0]
            if (this.modelName !== model) {
                const backFunc = event.data.onSuccess || function() {}
                event.data.onSuccess = () => {
                    let prom
                    if (this.acrux_widget) {
                        let record = this.model.get(this.handle, {env: false});
                        prom = this.acrux_widget.recordSaved(record)
                    } else {
                        prom = Promise.resolve()
                    }
                    prom.then(backFunc)
                }
            }
        }
        return this._super(event)
    },

    /**
     * @override
     */
    _abandonRecord: function (recordID) {
        if (this.acrux_widget) {
            recordID = recordID || this.handle;
            if (recordID !== this.handle) { // se evita el history_back de la clase padre
                this._super(recordID)
            }
        } else {
            this._super(recordID)
        }
    }
});

return BasicController;
});
