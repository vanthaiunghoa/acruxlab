/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component'
import { ComponentAdapter } from 'web.OwlCompatibility'


export class WhatsappConversation extends ComponentAdapter {

    renderWidget() {
        return this.widget.render();
    }

    updateWidget(nextProps) {
        return this.widget.update(nextProps);
    }
    
    async queryConversations() {
        return this.widget.queryConversation();
    }
 
}

Object.assign(WhatsappConversation, {
    props: {
        modelName: String,
        recId:  Number,
        fieldName: String,
        chatterLocalId: String,
        isWhatsappTalkVisible: Boolean,
        Component: Function,
        widgetArgs: Array,
        originalState: Object,
    },
})

registerMessagingComponent(WhatsappConversation)
