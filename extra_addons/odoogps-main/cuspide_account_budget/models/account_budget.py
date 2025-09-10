from odoo import fields, models, _


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    filename = fields.Char()
    add_file = fields.Binary(string="Add file")
    balance = fields.Monetary(
        compute='_compute_balance', string='Balance')

    def _compute_balance(self):
        for line in self:
            line.balance = line.planned_amount - line.practical_amount

    def _compute_percentage(self):
        for line in self:
            if line.theoritical_amount != 0.00:
                line.percentage = float((line.practical_amount or 0.0) / line.planned_amount)
            else:
                line.percentage = 0.00