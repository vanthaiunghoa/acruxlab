/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';

registerInstancePatchModel('mail.attachment_image', 'change_width', {

    /**
     * @override
     */
    _computeWidth() {
        let val
        if (this.attachmentList && this.attachmentList.isAcrux) {
            val = 100;
        } else {
            val = this._super()
        }
        return val;
    },
    
    _computeHeight() {
        let val
        if (this.attachmentList && this.attachmentList.isAcrux) {
            val = 100;
        } else {
            val = this._super()
        }
        return val;
    }
});

