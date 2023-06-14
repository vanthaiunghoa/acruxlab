/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component'
const { Component } = owl;


export class WhatsappTopbarButton extends Component {

    get chatter() {
        return this.messaging && this.messaging.models['mail.chatter'].get(this.props.chatterLocalId);
    }

    _onClickWhatsappTalk() {
        if (this.chatter) {
            return this.chatter._onClickWhatsappTalk()
        }
    }
}

Object.assign(WhatsappTopbarButton, {
    props: {
        chatterLocalId: String,
        isWhatsappTalkVisible: Boolean
    },
    template: 'whatsapp.connector.WhatsappTopbarButton',
})

registerMessagingComponent(WhatsappTopbarButton)

