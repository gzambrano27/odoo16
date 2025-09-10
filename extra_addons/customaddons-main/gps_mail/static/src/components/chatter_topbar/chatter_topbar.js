/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { ChatterTopbar } = owl;

export class ChatterTopbar extends Component {

    /**
     * @returns {ChatterTopbar}
     */
    get ChatterTopbar() {
        return this.props.record;
    }

}

Object.assign(ChatterTopbar, {
    props: { record: Object },
    template: 'mail.ChatterTopbar',
});

registerMessagingComponent(ChatterTopbar);
