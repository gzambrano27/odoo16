/** @odoo-module **/
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { TaxTotalsComponent, TaxGroupComponent } from "@account/components/tax_totals/tax_totals";

/**
 * Tax totals component specific to withholds.
 * In withholds, is not included in the total.
 * The base may be displayed to keep accountants happy, for example as part of the formatted values.
 */
export class TaxTotalsComponentForWithhold extends TaxTotalsComponent {
    setup() {
        super.setup();
    }

    _computeTotalsFormat() {
        // Prevents super's formatting method from running
        // (its logic is not compatible with withholds)
        return;
    }
}

TaxTotalsComponentForWithhold.template = "account.TaxTotalsField";
TaxTotalsComponentForWithhold.components = { TaxGroupComponent };
TaxTotalsComponentForWithhold.props = standardFieldProps;
registry.category("fields").add("account-tax-totals-field-for-withhold", TaxTotalsComponentForWithhold);
