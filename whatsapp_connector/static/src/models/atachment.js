/** @odoo-module **/

import { registerInstancePatchModel, registerFieldPatchModel } from '@mail/model/model_core'
import { attr } from '@mail/model/model_field'


registerFieldPatchModel('mail.attachment', 'acrux_field', {
    /**
     * Para decir si es acruxlab
     */
    isAcrux: attr({
        default: false,
    }),
});


registerInstancePatchModel('mail.attachment', 'acrux_linked', {

    _computeIsEditable() {
        let val = false
        if (this.isAcrux) {
            if (this.attachmentLists && this.attachmentLists.length) {
                val = this.attachmentLists[0].acruxMessageId <= 0
            } else {
                val = true
            }
        } else {
            val = this._super()
        }
        return val
    },

});

