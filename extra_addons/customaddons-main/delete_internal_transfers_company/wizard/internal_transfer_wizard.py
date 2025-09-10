from odoo import models, fields, api

class InternalTransferWizard(models.TransientModel):
    _name = 'internal.transfer.wizard'
    _description = 'Wizard to manage internal transfers'

    company_id = fields.Many2one('res.company', string="Compañía", required=True)
    transfer_line_ids = fields.One2many('internal.transfer.line.wizard', 'wizard_id', string="Líneas de Transferencias")

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            # Elimina el filtro 'picking_type_id.code' para traer todas las transferencias
            transfers = self.env['stock.picking'].search([
                ('company_id', '=', self.company_id.id),
                ('state', 'in', ['done','assigned']), 
            ])
            transfer_lines = [(5, 0, 0)]  # Limpia las líneas existentes
            for transfer in transfers:
                transfer_lines.append((0, 0, {
                    'transfer_id': transfer.id,
                    'picking_name': transfer.name,
                    'scheduled_date': transfer.scheduled_date,
                    'state': transfer.state,
                }))
            self.transfer_line_ids = transfer_lines
        else:
            self.transfer_line_ids = [(5, 0, 0)]  # Limpia las líneas si no hay compañía seleccionada


    def action_delete_stock_picking_line(self):
        
        for line in self.transfer_line_ids:
            picking_name = line.transfer_id.name

            # Eliminar líneas analíticas relacionadas
            self.env.cr.execute("""
                DELETE FROM account_analytic_line
                WHERE name LIKE %s
            """, (picking_name + '%',))

            # Eliminar las líneas de movimiento (stock_move_line)
            self.env.cr.execute("""
                DELETE FROM stock_move_line
                WHERE move_id IN (
                    SELECT id FROM stock_move WHERE picking_id IN (
                        SELECT id FROM stock_picking WHERE name = %s
                    )
                )
            """, (picking_name,))
            
            #eliminar los registros contables
            self.env.cr.execute("""
                DELETE FROM account_move am
                WHERE stock_move_id IN (
                    select id FROM stock_move
                        WHERE picking_id IN (
                            SELECT id FROM stock_picking WHERE name = %s
                        )
                )
            """, (picking_name,))
            
            #elimino los registros de valuacion
            self.env.cr.execute("""
                DELETE FROM stock_valuation_layer am
                WHERE stock_move_id IN (
                    select id FROM stock_move
                        WHERE picking_id IN (
                            SELECT id FROM stock_picking WHERE name = %s
                        )
                )
            """, (picking_name,))
            

            # Eliminar los movimientos de stock (stock_move)
            self.env.cr.execute("""
                DELETE FROM stock_move
                WHERE picking_id IN (
                    SELECT id FROM stock_picking WHERE name = %s
                )
            """, (picking_name,))

            # Eliminar los registros de inventario (stock_quant)
            self.env.cr.execute("""
                DELETE FROM stock_quant
                WHERE product_id IN (
                    SELECT product_id FROM stock_move_line
                    WHERE move_id IN (
                        SELECT id FROM stock_move WHERE picking_id IN (
                            SELECT id FROM stock_picking WHERE name = %s
                        )
                    )
                )
                AND location_id IN (
                    SELECT location_id FROM stock_move_line
                    WHERE move_id IN (
                        SELECT id FROM stock_move WHERE picking_id IN (
                            SELECT id FROM stock_picking WHERE name = %s
                        )
                    )
                )
                OR location_id IN (
                    SELECT location_dest_id FROM stock_move_line
                    WHERE move_id IN (
                        SELECT id FROM stock_move WHERE picking_id IN (
                            SELECT id FROM stock_picking WHERE name = %s
                        )
                    )
                )
            """, (picking_name, picking_name, picking_name))

            # Eliminar el picking (stock_picking)
            self.env.cr.execute("""
                DELETE FROM stock_picking
                WHERE name = %s
            """, (picking_name,))

class InternalTransferLineWizard(models.TransientModel):
    _name = 'internal.transfer.line.wizard'
    _description = 'Líneas de Transferencias Internas'

    wizard_id = fields.Many2one('internal.transfer.wizard', string="Wizard", required=True)
    transfer_id = fields.Many2one('stock.picking', string="Transferencia Interna", required=True)
    picking_name = fields.Char(string="Referencia", related="transfer_id.name", readonly=True)
    scheduled_date = fields.Datetime(string="Fecha Programada", related="transfer_id.scheduled_date", readonly=True)
    state = fields.Selection(related="transfer_id.state", string="Estado", readonly=True)



