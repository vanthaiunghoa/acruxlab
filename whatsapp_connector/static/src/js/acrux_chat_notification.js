/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ActionDialog } from '@web/webclient/actions/action_dialog'

const superSetup = ActionDialog.prototype.setup
var currentAction = {}
var notifactions_hash = new Map()
var legacyEnv = {}
var actionService = {}


ActionDialog.prototype.setup = function() {
    currentAction = this
    return superSetup.apply(this, arguments)
}

    
 export const processNotification = {
    /**
     * Muestra la notificacion en el navegador
     * @param {Array<Array<Object>>} data
     */
     process: function(data) {
        let msg = null

        data.forEach(row => {
            if (row.type === 'new_messages') {
                msg = this.processNewMessage({ new_messages: row.payload })
            } else if (row.type === 'opt_in') {
                this.processOptIn({ opt_in: row.payload })
            } else if(row.type === 'error_messages') {
                this.processErrorMessage({ error_messages: row.payload })
            }
        })
        if (msg) {
            if (msg.messages && msg.messages.length && msg.messages[0].ttype == 'text') {
                legacyEnv.services.bus_service.sendNotification({
                    title: legacyEnv._t('New Message from ') + msg.name,
                    message: msg.messages[0].text  
                })
            } else {
                legacyEnv.services.bus_service.sendNotification({
                    title: legacyEnv._t('New Message from ') + msg.name,
                    message: ''  
                })
            }
        }
    },

    /** 
     * get message to notify
     * @param {Object} row
     * @returns {Object}
     */
    processNewMessage: function(row) {
        row.new_messages.forEach(conv => {
            if (conv.messages) {
                conv.messages = conv.messages.filter(msg => !msg.from_me)
            } else {
                conv.messages = []
            }
        })
        let msg = row.new_messages.find(conv => conv.desk_notify == 'all' && conv.messages.length)
        if (!msg) {
            msg = row.new_messages.find(conv =>
                conv.desk_notify == 'mines'&&
                conv.agent_id &&
                conv.agent_id[0] == legacyEnv.session.uid &&
                conv.messages.length)
        }
        return msg
    },

    /**
     * Procesa la notificación de opt-in
     * @param {Object} row
     */
    processOptIn: function(row) {
        const notify = {
            type: row.opt_in.opt_in ? 'success' : 'warning',
            title: legacyEnv._t('Opt-in update'),
            message: row.opt_in.name + ' ' + (row.opt_in.opt_in ? legacyEnv._t('activate') : legacyEnv._t('deactivate')) + ' opt-in.',
            sticky: true,
        }
        legacyEnv.services.bus_service.sendNotification(notify)
        if (actionService?.currentController) {
            const state = actionService.currentController.getLocalState()
            if (actionService.currentController.action.res_model === 'acrux.chat.conversation') {
                state.__legacy_widget__.reload().catch(() => {})
            }
            if (currentAction?.el) {
                const styles = window.getComputedStyle(currentAction.el)
                if (!(styles.display === 'none' || styles.visibility === 'hidden') && currentAction.el.checkVisibility()) {
                    if (currentAction.props.actionProps.resModel === 'acrux.chat.message.wizard') {
                        if (currentAction.isLegacy) {
                            const componentController = currentAction.actionRef.comp;
                            const controller = componentController.componentRef.comp;
                            const viewAdapter = controller.controllerRef.comp;
                            const widget = viewAdapter.widget;
                            const record = widget.model.get(widget.handle, {env: false})
                            if (record?.data?.conversation_id?.data?.id === row.opt_in.conv) {
                                widget.reload().catch(() => {})
                            }
                        }
                    }
                    
                }
                
            }
        }
    },

    /**
     * Procesa mensaje de error 
     * @param {Object} row
     */
    processErrorMessage: function(row) {
        const msgList = []
        for (const conv of row.error_messages) {
            for (const msg of conv.messages) {
                if (msg.user_id[0] === legacyEnv.session.uid) {
                    const newMsg = Object.assign({}, msg)
                    newMsg.name = conv.name
                    newMsg.number = conv.number_format
                    msgList.push(newMsg)
                }
            }
        }
        for (const msg of msgList) {
            let complement = ''
            if (msg.text && '' !== msg.text) {
                complement += legacyEnv._t('<br> Message: ') + msg.text
            }
            const notify = {
                type: 'danger',
                title: legacyEnv._t('Message with error in <br>') + `${msg.name} (${msg.number})`,
                message: legacyEnv._t('Error: ') + msg.error_msg + complement,
                sticky: true,
            }
            legacyEnv.services.bus_service.sendNotification(notify)
        }
    }
}

/**
 * Indica si la pestaña es una pestaña de chatroom
 * @returns {Boolean}
 */
function isChatroomTab() {
    let out = false
    const currentController = actionService.currentController
    if (currentController) {
        if (currentController.action.tag) {
            out = currentController.action.tag === "acrux.chat.conversation_tag"
        } else {
            out = !!currentController.acrux_comp 
        }
    }
   return out
}

/**
 * Procesa las notificaciones que vienen del bus
 * @param {Array<Object>} notifications
 */
function onNotifaction(notifications) {
    /** @type {Array} */
    var data = notifications
    if (data && data.length) {
        let json = JSON.stringify(data)
        if (isChatroomTab()) {
            /** 
                Si hay una pestaña de chatroom abierta entonces
                se notifica a las demas pestañas que no deben mostrar la 
                notificacion 
            */
            legacyEnv.services.local_storage.setItem('chatroom_notification', json);
        } else {
            /**
                Se almacena en un Map, el json de la notificacion y un timeout
                para mostrar esta notificaciones.
                Si el timeout no se cancela entonces muestra la notifiacion.
             */
            notifactions_hash.set(json, setTimeout(() => {
                processNotification.process(data)
                notifactions_hash.delete(json);
            }, 50)) /** @bug posible bug con el timeout */ 
        }
    }
}

/**
 * Procesa el evento de almacenar.
 * Este evento se lanza cuando se recibe una notificion y se esta en la pestaña
 * de chatroom, basicamente es para evitar que se muestre la notificacion
 *
 * @param {OdooEvent} event
 * @param {string} event.key
 * @param {string} event.newValue
 */
function onStorage(event) {
    if (event.key === 'chatroom_notification') {
        const value = JSON.parse(event.newValue)
        if (notifactions_hash.has(value)) {  // si la notificacion esta esperando para mostrarse
            clearTimeout(notifactions_hash.get(value))  // no mostra notificaion
            notifactions_hash.delete(value)
        }
    }
}

export const chatroomNotificationService = {
    dependencies: ['action'],

    start(env, {action}) {
        legacyEnv = owl.Component.env
        actionService = action
        env.bus.on("WEB_CLIENT_READY", null, async () => {
            legacyEnv.services.bus_service.onNotification(this, onNotifaction)
            /** @bug en web/legacy/utils.js */
            $(window).on('storage', e => {
                var key = e.originalEvent.key
                var newValue = e.originalEvent.newValue
                try {
                    JSON.parse(newValue)
                    onStorage({
                        key: key,
                        newValue: newValue,
                    })
                } catch (error) {
                    // ignore
                }
            });
            legacyEnv.services.bus_service.startPolling()
        })
    },
}

registry.category("services").add("chatroomNotification", chatroomNotificationService)
