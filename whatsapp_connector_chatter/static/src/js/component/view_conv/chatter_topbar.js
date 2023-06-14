/** @odoo-module **/

import { ChatterTopbar } from '@mail/components/chatter_topbar/chatter_topbar'


Object.assign(ChatterTopbar.props, {
    isWhatsappTalkVisible: Boolean,
    isChatroomInstalled: Boolean,
    isInAcruxChatRoom: Boolean,
})

