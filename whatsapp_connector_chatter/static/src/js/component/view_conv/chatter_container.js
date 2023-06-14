/** @odoo-module **/

import { registerMessagingComponent, unregisterMessagingComponent } from '@mail/utils/messaging_component'
import { ChatterContainer as ChatterContainerBase } from '@mail/components/chatter_container/chatter_container'


export class ChatterContainer extends ChatterContainerBase {
    async _insertFromProps(props) {
        let newProps = props
        if (props && 'originalState' in props) {
            newProps = {...props}
            delete newProps['originalState']
        }
        return super._insertFromProps(newProps)
    }
}

Object.assign(ChatterContainer.props, ChatterContainerBase.props, {
    originalState: Object
})


unregisterMessagingComponent(ChatterContainerBase)
registerMessagingComponent(ChatterContainer)

