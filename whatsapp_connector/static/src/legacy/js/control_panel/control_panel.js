odoo.define('whatsapp_connector.ControlPanel', function (require) {
    "use strict";
    const ControlPanel = require('web.ControlPanel');
    var core = require('web.core');
    
    const superTrigger = ControlPanel.prototype.trigger;
    let chatroom = null;
    
    core.bus.on('chatroom:create', {}, chat => chatroom = chat)
    core.bus.on('chatroom:destroy', {}, () => chatroom = null)
    
    function trigger(eventType, payload) {
        if (chatroom && eventType === 'breadcrumb-clicked' && payload && payload.controllerID) {
            if (chatroom.isChatroomTab(payload.controllerID)) {
                // esto falsea el controller hacia el controller de chatroom
                payload.controllerID = this.props.breadcrumbs[0].controllerID
            }
        }
        return superTrigger.call(this, eventType, payload)
    } 
    
    ControlPanel.prototype.trigger = trigger
    
    return ControlPanel
})