from odoo import api, fields, models
from odoo.exceptions import UserError

class WizardGeneratePR(models.TransientModel):
    _name = 'wizard.generate.pr'
    _description = 'Generar PR desde Macro Requisición'

    request_id = fields.Many2one('macro.purchase.request', required=True, readonly=True)
    line_ids = fields.One2many('wizard.generate.pr.line', 'wizard_id', string='Líneas')

    def action_generate_pr_acceptance(self):
        if not self.line_ids:
            raise UserError("Debe seleccionar al menos un producto para generar la aceptación.")

        acceptance = self.env['request.acceptance'].create({
            'request_id': self.request_id.id,
            'responsible_id': self.env.user.id,
            'date_due': fields.Datetime.now(),
            'picking_type_id': self.request_id.picking_type_id.id,
        })

        for line in self.line_ids.filtered(lambda l: l.quantity_to_accept > 0):
            self.env['request.acceptance.line'].create({
                'pr_id': acceptance.id,
                'product_id': line.product_id.id,
                'name': line.product_id.display_name,
                'product_qty': line.quantity_to_accept,
                'product_uom': line.product_uom_id.id,
                'price_unit': 0.0,
                'purchase_line_id': line.original_line_id.id,
                'analytic_distribution': line.analytic_distribution,
                'tipo_costo': line.tipo_costo,
                'rubro': line.rubro,
                "costo_uni_apu":line.costo_uni_apu,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'request.acceptance',
            'view_mode': 'form',
            'res_id': acceptance.id,
            'target': 'current',
        }


class WizardGeneratePRLine(models.TransientModel):
    _name = 'wizard.generate.pr.line'
    _description = 'Línea del Wizard para PR'

    wizard_id = fields.Many2one('wizard.generate.pr', ondelete='cascade')
    original_line_id = fields.Many2one('macro.purchase.request.line', readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string="UoM", readonly=True)
    quantity_requested = fields.Float(readonly=True)
    quantity_to_accept = fields.Float(string="Cantidad a Aceptar", default=0.0)
    analytic_distribution = fields.Json(readonly=True)
    tipo_costo = fields.Char(readonly=True)
    rubro = fields.Char(readonly=True)
    costo_uni_apu = fields.Float('Costo U. Apu', digits=(16,4))

    @api.onchange('original_line_id')
    def _onchange_original_line_id(self):
        if self.original_line_id:
            self.product_id = self.original_line_id.product_id.id
            self.product_uom_id = self.original_line_id.product_uom_id.id
            self.quantity_requested = self.original_line_id.product_qty
            self.tipo_costo = self.original_line_id.tipo_costo
            self.rubro = self.original_line_id.rubro