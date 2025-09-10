/** @odoo-module **/

import { AccountTypeSelection } from "@account/components/account_type_selection/account_type_selection";
import { patch } from "@web/core/utils/patch";
const session = require('web.session');
//    const patchMixin = require("web.patchMixin");
//    const PatchableAttachment = patchMixin(Attachment);

const {QWeb, Context} = owl;
patch(AccountTypeSelection.prototype, "account_type_view", {
    get hierarchyOptions() {
        const opts = this.options;
        return [
            { name: this.env._t('Balance Sheet') },
            { name: this.env._t('Assets'), children: opts.filter(x => x[0] && x[0].startsWith('asset')) },
            { name: this.env._t('Liabilities'), children: opts.filter(x => x[0] && x[0].startsWith('liability')) },
            { name: this.env._t('Equity'), children: opts.filter(x => x[0] && x[0].startsWith('equity')) },
            { name: this.env._t('Profit & Loss') },
            { name: this.env._t('Income'), children: opts.filter(x => x[0] && x[0].startsWith('income')) },
            { name: this.env._t('Expense'), children: opts.filter(x => x[0] && x[0].startsWith('expense')) },
            { name: this.env._t('Other'), children: opts.filter(x => x[0] && ['off_balance','view'].includes(x[0])) },
        ];
    }

});



