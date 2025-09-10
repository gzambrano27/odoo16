from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class SplitMO(models.TransientModel):
    _name = "split.mo.wizard"

    split_mo_by = fields.Selection([('by_no', 'Number of split'), ('by_qty', 'Split By Quantity')], required=True)
    split_mo_no = fields.Integer('Split No/Qty', required=True)

    def btn_split(self):
        mrp_obj = self.env['mrp.production']
        active_id = self.env.context.get('active_id')

        current_mrp_data = mrp_obj.search([('id', '=', active_id)])

        if self.split_mo_by == 'by_no':
            split_mo_no = self.split_mo_no

            for i, _n in enumerate(range(0, split_mo_no), start=1):
                mrp_line_data = []

                mrp_vals = {
                    'name': current_mrp_data.name + '-00' + str(i),
                    'product_id': current_mrp_data.product_id.id,
                    'product_qty': current_mrp_data.product_qty / split_mo_no,
                    'date_planned_start': current_mrp_data.date_planned_start,
                    'company_id': current_mrp_data.company_id.id,
                    'origin': current_mrp_data.name,
                    'bom_id': current_mrp_data.bom_id.id,
                    'product_uom_id': current_mrp_data.product_uom_id.id,
                    'picking_type_id': current_mrp_data.picking_type_id.id,
                    'location_src_id': current_mrp_data.location_src_id.id,
                    'location_dest_id': current_mrp_data.location_dest_id.id
                }

                for mo_line in current_mrp_data.bom_id.bom_line_ids:
                    line_vals = {'product_id': mo_line.product_id.id,
                                 'name': mo_line.product_id.name,
                                 'product_uom_qty': (
                                         mo_line.product_qty * (current_mrp_data.product_qty / split_mo_no)),
                                 'location_id': current_mrp_data.location_src_id.id,
                                 'location_dest_id': current_mrp_data.location_dest_id.id,
                                 'product_uom': mo_line.product_uom_id.id}
                    mrp_line_data.append((0, 0, line_vals))

                    mrp_vals.update({'move_raw_ids': mrp_line_data})

                mrp_obj.create(mrp_vals)

            current_mrp_data.do_unreserve()
            current_mrp_data.state = 'cancel'

        elif self.split_mo_by == 'by_qty':
            split_mo_qty = self.split_mo_no
            print('split_mo_qty+++++++++', split_mo_qty)
            qty = int(current_mrp_data.product_qty) - int(split_mo_qty)

            change_production_qty_wizard_id = self.env['change.production.qty'].create({'product_qty': qty})
            change_production_qty_wizard_id.change_prod_qty()

            mrp_line_data = []

            mrp_vals = {
                'name': current_mrp_data.name + '-001',
                'product_id': current_mrp_data.product_id.id,
                'product_qty': split_mo_qty,
                'date_planned_start': current_mrp_data.date_planned_start,
                'company_id': current_mrp_data.company_id.id,
                'origin': current_mrp_data.name,
                'bom_id': current_mrp_data.bom_id.id,
                'product_uom_id': current_mrp_data.product_uom_id.id,
                'picking_type_id': current_mrp_data.picking_type_id.id,
                'location_src_id': current_mrp_data.location_src_id.id,
                'location_dest_id': current_mrp_data.location_dest_id.id
            }

            for mo_line in current_mrp_data.bom_id.bom_line_ids:
                line_vals = {'product_id': mo_line.product_id.id,
                             'name': mo_line.product_id.name,
                             'product_uom_qty': (mo_line.product_qty * split_mo_qty),
                             'location_id': current_mrp_data.location_src_id.id,
                             'location_dest_id': current_mrp_data.location_dest_id.id,
                             'product_uom': mo_line.product_uom_id.id}
                mrp_line_data.append((0, 0, line_vals))

                mrp_vals.update({'move_raw_ids': mrp_line_data})

            mrp_obj.create(mrp_vals)

