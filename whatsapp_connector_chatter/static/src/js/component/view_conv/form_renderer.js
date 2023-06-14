
/** @odoo-module **/

require('@mail/widgets/form_renderer/form_renderer');
import FormRenderer from 'web.FormRenderer';

FormRenderer.include({
    _makeChatterContainerProps() {
        let out = this._super.apply(this, arguments);
        out['originalState'] = this.state;
        return out;
    }
})


