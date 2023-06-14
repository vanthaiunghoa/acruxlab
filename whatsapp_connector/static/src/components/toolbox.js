/** @odoo-module **/

import { link } from '@mail/model/model_field_command'
import { registerMessagingComponent } from '@mail/utils/messaging_component'


const { Component } = owl;
const { useRef, useState } = owl.hooks;


export class ToolBoxComponent extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.attachment = useState({value: null});
        this._parent_widget = this.props.parent_widget;
        this._fileUploaderRef = useRef('fileUploader');
    }
    
    get attachments() {
        let out = []
        if (this.attachment.value) {
            out.push(this.attachment.value.localId);
        }
        return out
    }

    /**
     * Get an object which is passed to FileUploader component to be used when
     * creating attachment.
     *
     * @returns {Object}
     */
    get newAttachmentExtraData() {
        return {}
    }
    
    openBrowserFileUploader() {
        this._fileUploaderRef.comp.openBrowserFileUploader();
        this._parent_widget.$input.focus();
    }
    
    /**
     * @private
     * @param {CustomEvent} ev
     * @param {Object} ev.detail
     * @param {mail.attachment} ev.detail.attachment
     */
    _onAttachmentCreated(ev) {
        const attachment = ev.detail.attachment
        const AttachmentList = this.messaging.models['mail.attachment_list']
        const attch_list = AttachmentList.insert({isAcrux: true, acruxMessageId: 0})
        attachment.update({attachmentLists: link(attch_list)})
        this.attachment.value = attachment
        this._parent_widget.enableDisplabeAttachBtn();
        if (this.createdResolve) {
            this.createdResolve()
        }
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onAttachmentRemoved(ev) {
        this.attachment.value = null;
        this._parent_widget.enableDisplabeAttachBtn();
    }

    /**
     * @param {CustomEvent} ev
     */
    async uploadFile(ev) {
        const prom = new Promise(resolve => this.createdResolve = resolve)
        await this._fileUploaderRef.comp._onChangeAttachment(ev)
        await prom
    }
}

Object.assign(ToolBoxComponent, {
    props: {
        parent_widget: Object,
    },
    template: 'acrux_chat_toolbox_component',
});

registerMessagingComponent(ToolBoxComponent)

