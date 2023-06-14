/** @odoo-module **/

import { registerMessagingComponent, unregisterMessagingComponent } from '@mail/utils/messaging_component'
import { Chatter as ChatterBase }  from '@mail/components/chatter/chatter'
import { clear } from '@mail/model/model_field_command'
const WhatsappChatter = require('whatsapp_connector_chatter.Chatter');
const { useState } = owl.hooks;
const { useRef } = owl.hooks;


export class Chatter extends ChatterBase {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        let state = this.state || {};
        Object.assign(state, {
            isWhatsappTalkVisible: false,
        });
        this.state = useState(state);
        this._whatsappConversationRef = useRef('whatsappConversationRef');
        if (!this.widgetComponents) {
            this.widgetComponents = {}
        } 
        Object.assign(this.widgetComponents, {
            WhatsappChatter,
        });
    }

    showWhatsappTalk() {
         this.state.isWhatsappTalkVisible = true;
    }
    
    hideWhatsappTalk() {
         this.state.isWhatsappTalkVisible = false;
    }
    
    /**
     *  Cuando hace click en ver la conversacion de whatsapp
     */
    async _onClickWhatsappTalk() {
        if (this.state.isWhatsappTalkVisible){
            this.state.isWhatsappTalkVisible = false;
        } else {
            if (this._whatsappConversationRef.comp) {
                await this._whatsappConversationRef.comp.queryConversations()
                this.state.isWhatsappTalkVisible = true;
                this.chatter.update({ composerView: clear() });
            }
        }
    }

}

Object.assign(Chatter.props, {
    originalState: Object,
    isChatroomInstalled: Boolean,
    isInAcruxChatRoom: Boolean,
})

unregisterMessagingComponent(ChatterBase)
registerMessagingComponent(Chatter)

