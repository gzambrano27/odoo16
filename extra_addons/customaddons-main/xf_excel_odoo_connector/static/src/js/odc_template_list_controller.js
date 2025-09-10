/** @odoo-module */

import {patch} from "@web/core/utils/patch";
import {ListController} from '@web/views/list/list_controller';

patch(ListController.prototype, 'odc_template_list', {
    async onCreateODCTemplate() {
        const self = this;
        let template_fields = [];
        this.archInfo.columns.forEach(function (column, i) {
            if (column.type === 'field') {
                let field = self.model.root.activeFields[column.rawAttrs.name];
                template_fields.push([0, false, {
                    sequence: i + 1,
                    model: self.props.resModel,
                    field_name: field.name,
                    name: field.string,
                    export_type: self.get_export_type(field),
                }]);
            }
        });

        this.actionService.doAction('xf_excel_odoo_connector.odc_template_modal_window', {
            additionalContext: {
                default_name: self.actionService.currentController.displayName,
                default_model: self.props.resModel,
                default_domain: JSON.stringify(self.model.root.domain),
                default_field_ids: template_fields,
            },
            props: {
                onSave: (record, params) => {
                    // do nothing
                }
            }
        });
    },

    get_export_type(field) {
        const NUMBER_TYPES = new Set(['integer', 'float', 'monetary', 'boolean']);
        const DATE_TYPES = new Set(['date']);
        const DATETIME_TYPES = new Set(['datetime']);


        if ([...new Set(field.FieldComponent.supportedTypes)].filter(x => NUMBER_TYPES.has(x)).length > 0) {
            return 'number';
        }
        if ([...new Set(field.FieldComponent.supportedTypes)].filter(x => DATE_TYPES.has(x)).length > 0) {
            return 'date';
        }
        if ([...new Set(field.FieldComponent.supportedTypes)].filter(x => DATETIME_TYPES.has(x)).length > 0) {
            return 'datetime';
        }
        return 'text';
    }
});

