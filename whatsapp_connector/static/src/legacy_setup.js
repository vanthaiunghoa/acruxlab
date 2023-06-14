/** @odoo-module **/

import { legacySetupProm } from "@web/legacy/legacy_setup"
import { WarningDialog } from "@web/core/errors/error_dialogs"
import { registry } from "@web/core/registry"


export function fixLegacyCrashManagerService(legacyEnv) {
    return {
        dependencies: ["dialog"],
        start(env) {
            legacyEnv.services.crash_manager.show_warning = (error) => {
                const message = error.data ? error.data.message : error.message
                env.services.dialog.add(WarningDialog, {message: message})
            }
        },
    }
}


legacySetupProm.then(legacyEnv => {
    const serviceRegistry = registry.category("services")
    serviceRegistry.add("fix_crash_manager", fixLegacyCrashManagerService(legacyEnv))
    return legacyEnv
})
