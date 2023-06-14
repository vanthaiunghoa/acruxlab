/** @odoo-module **/

import { FileUploader } from '@mail/components/file_uploader/file_uploader'
import { registerMessagingComponent } from '@mail/utils/messaging_component'
import framework from 'web.framework'


export const geAttachmentNextTemporaryId = (function () {
    let tmpId = 0;
    return () => {
        tmpId += 1;
        return tmpId;
    };
})();


export class AcruxFileUploader extends FileUploader {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
    }

    /**
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    async uploadFiles(files) {
        try {
            framework.blockUI();
            await super.uploadFiles(files)
        } finally {
            framework.unblockUI();
        }
    }

    /**
     * @private
     * @param {FileList|Array} files
     * @returns {Promise}
     */
    async _performUpload({files}) {
        const uploadingAttachments = new Map();
        for (const file of files) {
            uploadingAttachments.set(file, this.messaging.models['mail.attachment'].insert({
                filename: file.name,
                id: geAttachmentNextTemporaryId(),
                isUploading: true,
                mimetype: file.type,
                name: file.name,
                originThread: undefined,
                isAcrux: true,
            }));
        }
        for (const file of files) {
            const uploadingAttachment = uploadingAttachments.get(file);
            if (!uploadingAttachment.exists()) {
                // This happens when a pending attachment is being deleted by user before upload.
                continue;
            }
            try {
                const response = await this.env.browser.fetch('/web/binary/upload_attachment_chat', {
                    method: 'POST',
                    body: this._createFormData({ file }),
                    signal: uploadingAttachment.uploadingAbortController.signal,
                });
                const attachmentData = await response.json();
                if (uploadingAttachment.exists()) {
                    uploadingAttachment.delete();
                }
                this._onAttachmentUploaded({ attachmentData });
            } catch (e) {
                if (e.name !== 'AbortError') {
                    throw e;
                }
            }
        }
    }
}

Object.assign(AcruxFileUploader, {
    props: {
        attachmentLocalIds: Array,
        newAttachmentExtraData: Object,
    },
});

registerMessagingComponent(AcruxFileUploader)
