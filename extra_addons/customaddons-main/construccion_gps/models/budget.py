from odoo import models, fields, api

class Budget(models.Model):
    _name = 'budget.apu'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Presupuesto con APU'

    name = fields.Char(string='Nombre del presupuesto', required=True, tracking=True)
    total_cost = fields.Float(string='Costo total', compute='_compute_total_cost', store=True, digits=(16,4), tracking=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Finalizado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)
    date_start = fields.Date(string='Fecha de inicio', tracking=True)
    date_end = fields.Date(string='Fecha de finalización', tracking=True)
    line_ids = fields.One2many('budget.line', 'budget_id', string='Líneas de presupuesto')

    @api.depends('line_ids.total_cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = sum(line.total_cost for line in record.line_ids)

    def confirm_budget(self):
        self.write({'state': 'confirmed'})

    def finalize_budget(self):
        self.write({'state': 'done'})

    def cancel_budget(self):
        self.write({'state': 'cancelled'})

    def reset_to_draft(self):
        self.write({'state': 'draft'})

    @api.model
    def _expand_states(self, states, domain, order):
        return ['draft', 'confirmed', 'done', 'cancelled']

class BudgetLine(models.Model):
    _name = 'budget.line'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Línea de Presupuesto'

    name = fields.Char(string='Descripción', required=True, tracking=True)
    quantity = fields.Float(string='Cantidad', required=True, tracking=True, digits=(16,4))
    unit_price = fields.Float(string='Precio unitario', required=True, tracking=True, digits=(16,4))
    total_cost = fields.Float(string='Costo total', compute='_compute_total_cost', store=True, tracking=True, digits=(16,4))
    budget_id = fields.Many2one('budget.apu', string='Presupuesto')
    apu_id = fields.Many2one('apu.apu', string='APU', onchange='_onchange_apu_id')
    description = fields.Text(string='Descripción detallada', tracking=True)
    analysis = fields.Text(string='Análisis', help='Análisis detallado del APU seleccionado.')  # Nuevo campo para análisis
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Cuenta analítica',
        help='Cuenta analítica asociada a esta línea de presupuesto.'
    )

    @api.depends('quantity', 'unit_price')
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.quantity * line.unit_price

    @api.onchange('apu_id')
    def _onchange_apu_id(self):
        """
        Actualiza los valores de la línea de presupuesto y genera un análisis
        detallado del APU seleccionado.
        """
        if self.apu_id:
            # Actualiza el nombre de la línea basado en el APU
            self.name = self.apu_id.name

            # Calcula la cantidad total a partir de las líneas del APU
            total_quantity = sum(line.quantity for line in self.apu_id.line_ids)
            self.quantity = total_quantity

            # Calcula el precio unitario promedio de las líneas del APU
            total_cost = sum(line.total_cost for line in self.apu_id.line_ids)
            if total_quantity > 0:
                self.unit_price = total_cost / total_quantity
            else:
                self.unit_price = 0.0

            # Asigna la cuenta analítica del APU (si existe)
            self.analytic_account_id = self.apu_id.analytic_account_id

            # Genera el análisis del APU y lo guarda en el campo `analysis`
            self.analysis = self._generate_apu_analysis()

    def _generate_apu_analysis(self):
        """
        Genera un análisis detallado del APU seleccionado.
        """
        if not self.apu_id:
            return "No hay un APU seleccionado para analizar."

        analysis = "Análisis del APU: {}\n".format(self.apu_id.name)
        analysis += "========================================\n"

        for line in self.apu_id.line_ids:
            analysis += "Recurso: {} | Tipo: {} | Cantidad: {} | Precio Unitario: {} | Costo Total: {}\n".format(
                line.name, line.type, line.quantity, line.unit_price, line.total_cost
            )
        analysis += "---------------------------------------------------------------------------------\n"
        analysis += "Costo Total del APU: {}\n".format(self.apu_id.total_cost)

        return analysis