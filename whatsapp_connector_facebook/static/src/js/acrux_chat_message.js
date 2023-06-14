odoo.define('whatsapp_connector_facebook.message', function(require) {
"use strict";

var Message = require('whatsapp_connector.message')
var Dialog = require('web.Dialog');
var core = require('web.core')
var _t = core._t;

/**
 * @class
 * @name Message
 * @extends Message
 */
Message.include({
    events: _.extend({}, Message.prototype.events, {
        'click .o_acrux_story_image': 'openStoryImage',
    }),
    /**
     * @param {Object} options datos a actualizar
     * @override
     */
    update: function(options) {
        this._super(options)
        this.url_due = options.url_due || false
        this.custom_url = options.custom_url || ''
        if (this.ttype === 'url' && this.text) {
            const sub_types = {
                story_mention: _t('A story mention you.')
            }
            if (this.text in sub_types) {
                this.text = sub_types[this.text]
            }
        }
    },

    /**
     * @override
     * @returns {Promise}
     */
    willStart: function() {
        let def = false
        if (this.ttype === 'url') {
            if(!this.url_due) {
                def = this._rpc({
                    model: 'acrux.chat.message',
                    method: 'check_url_due',
                    args: [this.id],
                    context: this.context
                }).then(data => {
                    this.url_due = data.url_due
                    if (this.url_due) {
                        this.res_model_obj = { display_name: _t('Story not found') }
                        this.res_model_obj.filename = this.res_model_obj.display_name;                    
                    } else {
                        this.res_model_obj = data
                    }
                })
            } else {
                this.res_model_obj = { display_name: _t('Story not found') }
                this.res_model_obj.filename = this.res_model_obj.display_name;
            }
        }
        return Promise.all([this._super(), def]);
    },

    /**
     * Renderiza un objeto personalizado en el area de los adjuntos
     * @returns {String}
     */
    _renderCustomObject: function() {
        let out = ''
        if (this.ttype === 'url' && !this.url_due) {
            if (this.res_model_obj.mime.startsWith('image')) {
                out = `
<div href=""
    style="background-image:url('data:${this.res_model_obj.mime};base64,${this.res_model_obj.data}'); background-size: auto; cursor: pointer;"
    data-mimetype="${this.res_model_obj.mime}" class="o_Attachment_image o_image o-attachment-viewable o-details-overlay o-medium o_acrux_story_image">
</div>
                `
            } else if (this.res_model_obj.mime.startsWith('video')) {
                out = `
<video width="200" height="200" controls controlsList="nodownload">
  <source src="data:${this.res_model_obj.mime};base64,${this.res_model_obj.data}" type="${this.res_model_obj.mime}">
</video>
                `
            } else {
                out = `<i>${_t('Story not found.')}</i>`
            }
        } else {
            out = this._super()
        }
        return out
    },

    /**
     * Abre la imagen en un dialogo
     */
    openStoryImage: function() {
        var buttons = [{
            text: _t("Ok"),
            close: true,
        }];
        const url = `data:${this.res_model_obj.mime};base64,${this.res_model_obj.data}`
        return new Dialog(this.conversation, {
            size: 'large',
            buttons: buttons,
            $content: $(`
<main style="text-align: center;">
    <div href=""
        style="background-image:url('${url}');width: auto;height: auto;"
        data-mimetype="${this.res_model_obj.mime}" class="o_Attachment_image o_image o-attachment-viewable o-details-overlay o-medium o_acrux_story_image">
        <img src="${url}" style="visibility: hidden;max-width: 100%; max-height: calc(100vh/1.5);" />
    </div>
</main>
            `),
            title: _t("Alert"),
            fullscreen: true,
        },).open({shouldFocusButtons:true});
    },

    /**
     * Permite activar o desactivar la opcion de responder mensaje
     * @return {Boolean}
     */
    canBeAnswered: function() {
        return this._super() && (!this.conversation.isOwnerFacebook() || this.conversation.isWabaExtern())
    },

    /**
     * Permite activar o desactivar la opcion de borrar mensaje
     * @return {Boolean}
     */    
    canBeDeleted: function() {
        return this._super() && !this.conversation.isOwnerFacebook()
    },

})

return Message

})
