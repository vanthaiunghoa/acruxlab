/** @odoo-module **/

require('@mail/models/chatter/chatter');
import { registry } from '@mail/model/model_core'

var factoryBak = registry['mail.chatter'].factory;

/**
 * Esto seguro deberia estar hecho con alguna funcion de mail de path la clase
 * pero funciona y no vale la pena cambiarno a hora
 */ 
registry['mail.chatter'].factory = (dependencies) => {
    let outClass = factoryBak(dependencies);
    class Chatter extends outClass {
        
        create(vals) {
            let data = {}
            Object.assign(data, vals);
            if (data.originalState) {
                delete data.originalState;
            }
            return super.create(data);
        }
        
        update(vals) {
            let data = {}
            Object.assign(data, vals);
            if (data.originalState) {
                delete data.originalState;
            }
            return super.update(data);
        }

        /**
         *  @override
         */        
        onClickLogNote() {
            super.onClickLogNote()
            if (this.componentChatterTopbar) {
                // el campo __owl__ no deberi usarse pero aja no supe como hacerlo
                this.componentChatterTopbar.__owl__.parent.hideWhatsappTalk()
            }
        }

        /**
         *  @override
         */
        onClickSendMessage(ev) {
            super.onClickSendMessage(ev)
            if (this.componentChatterTopbar) {
                // el campo __owl__ no deberi usarse pero aja no supe como hacerlo
                this.componentChatterTopbar.__owl__.parent.hideWhatsappTalk()
            }
        }
        
        _onClickWhatsappTalk() {
            // el campo __owl__ no deberi usarse pero aja no supe como hacerlo
            if (this.componentChatterTopbar) {
                return this.componentChatterTopbar.__owl__.parent._onClickWhatsappTalk()
            }
        }
    }
    Object.assign(Chatter, outClass);
    
    return Chatter; 
}

