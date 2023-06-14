/** @odoo-module **/

import { ActionContainer } from "@web/webclient/actions/action_container"
import { browser } from "@web/core/browser/browser"


const superRender = ActionContainer.prototype.render

async function render(force=false) {
    let callSuper = false
    let out
    try {
        if (this.info.componentProps.context && 
            this.info.componentProps.context.is_acrux_chat_room && 
            this.info.componentProps.action.target === 'inline') {
            this.info.Component.env.services = Object.assign({}, this.env.services, this.info.Component.env.services)
            const comp = new this.info.Component(null, this.info.componentProps)
            const tmp = document.createElement("div")
            await comp.mount(tmp)
            const current_action = browser.sessionStorage.getItem("current_action");
            const url_origin = browser.location.href
            comp.mounted()
            browser.sessionStorage.setItem("current_action", current_action);
            browser.setTimeout(() => {
                browser.history.replaceState({}, "", url_origin)
            })
            const currentController =  this.env.services.action.currentController
            currentController.acrux_comp = comp
            out = Promise.resolve()
        } else {
            callSuper = true
        }
        
    } catch (err) {
        console.log(err)
        callSuper = true
    }
    if (callSuper) {
        out = superRender.apply(this, arguments)
    }
    return out
}

ActionContainer.prototype.render = render
