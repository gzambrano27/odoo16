# -*- coding: utf-8 -*-
#from addons.l10n_fr_pos_cert.models.pos import LINE_FIELDS
from odoo import fields, models, tools, api
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_requisition_request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Requisition',
    )

    @api.onchange('custom_requisition_request_id')
    def _onchange_custom_requisition_request_id(self):
        if self.custom_requisition_request_id:
            if self.custom_requisition_request_id.line_ids:
                requisition_line_ids = self.custom_requisition_request_id.line_ids
                for line in requisition_line_ids:
                    analytic = line.analytic_distribution
                    # copiar la distribuicion de la requisicion a las lineas del picking
                    if line.product_id.detailed_type == 'product':
                        #move_id=self.env['stock.move'].create_move()
                        #self.env['stock.move.line'].create_move(self)
                        #return {
                        self.move_ids.create({
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'description_picking': line.name,
                            'quantity_done': line.product_qty,
                            'product_uom': line.product_uom_id.id,
                            'location_id': self.location_id.id,
                            'location_dest_id': self.location_dest_id.id,
                            'picking_type_id': self.picking_type_id.id,
                            'company_id': self.company_id.id,
                            'picking_id': self.id,
                            'analytic_distribution': line.analytic_distribution,
                        }
                        )
                        #self.move_line_ids.create({
                        #    'product_id': line.product_id.id,
                        #    'qty_done': line.product_qty,
                        #    'product_uom_id': line.product_uom_id.id,
                        #    'location_id': self.location_id.id,
                        #    'location_dest_id': self.location_dest_id.id,
                        #    'picking_type_id': self.picking_type_id.id,
                        #    'company_id': self.company_id.id,
                        #    'picking_id': self.id,
                        #    'analytic_distribution': line.analytic_distribution,
                        #}
                        #)  # 'custom_requisition_line_id': line.id,
                self.analytic_distribution = analytic
            else:
                self.analytic_distribution = False
        else:
            self.analytic_distribution = {}


    @api.constrains('custom_requisition_request_id', 'analytic_distribution')
    def _check_analytic_account_match_req(self):
        for record in self:
            ro = record.custom_requisition_request_id
            if ro and record.analytic_distribution != False:
                requisition_line_ids = self.custom_requisition_request_id.line_ids
                for line in requisition_line_ids:
                    analytic = line.analytic_distribution
                    break
                #distribution = {str(ro.analytic_account_id.id): 100.0}
                distribution = analytic
                if distribution != record.analytic_distribution:
                    raise ValidationError("La cuenta analitica de la requisicion de compra no coincide con la del registro actual.")
            if ro and not record.analytic_distribution:
                raise ValidationError("La cuenta analitica de la requisicion de compra no coincide con la del registro actual.")

