from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class ThDecimosRun(models.Model):
    _name = 'th.decimos.run'
    _description = 'Decimos Run'

    user_id = fields.Many2one('res.users', string='User', store=True, default=lambda self: self.env.uid, readonly=True)
    name = fields.Char('Name', size=64, default='Registro de Decimo')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('approve', 'Aprobado'),
        ('paid', 'Pagado'),
        ('cancel', 'Cancelado'),
    ], default='draft')
    date_start = fields.Date('Date From')
    date_end = fields.Date('Date To')
    reference = fields.Char('Reference', size=64, default='Registro de Decimo')
    type = fields.Selection([('DEC-TERC', 'Decimo Tercero'), ('DEC-CUARTO', 'Decimo Cuarto')], 'type')
    company_id = fields.Many2one('res.company', 'Company')
    line_ids = fields.One2many('th.decimos.run.lines', 'decimo_run_id', string='Lines Decimos')
    line_dter_ids = fields.One2many('th.decimos.run.dter.lines', 'decimo_run_id', string='Lines Decimos')
    total_decimos = fields.Float(string='Total Decimos')
    total_decimos_ter = fields.Float(string='Total Decimos')
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True)
    move_dter_id = fields.Many2one('account.move', 'Accounting Entry Dec Tercero', readonly=True)
    journal_id = fields.Many2one('account.journal', 'Expense Journal')
    currency_id = fields.Many2one('res.currency', 'Currency')
    pagos_ids = fields.Many2many('account.payment', string="Pagos Decimos", copy=False, readonly=True)
    has_pagos = fields.Boolean(help="Technical field used for usability purposes")
    csv_export_file = fields.Binary('CSV File')
    csv_export_filename = fields.Char('CSV Filename', size=50, readonly=True)
    date_registro = fields.Date('Fecha Registro', default=fields.Date.context_today)
    residual = fields.Float('Residual', digits=(16, 2))
    residual_ter = fields.Float('Residual', digits=(16, 2))
    val_pagado = fields.Float('Valor Pagado', digits=(16, 2))
    val_pagado_ter = fields.Float('Valor Pagado', digits=(16, 2))
    payments_widget = fields.Text()
    payments_widget_ter = fields.Text()
    total_retencion = fields.Float('Retencion', digits=(16, 2))
    total_retencion_ter = fields.Float('Retencion', digits=(16, 2))


class ThDecimosRunLines(models.Model):
    _name = 'th.decimos.run.lines'
    _description = 'Detalle de Decimos'
    
    name = fields.Char('Name', size=256, readonly=False)
    decimo_run_id = fields.Many2one('th.decimos.run', string='Decimo')
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=False)
    code = fields.Char('Decimo')
    dias = fields.Integer('Dias')
    retencion = fields.Float('Retencion')
    amount = fields.Float('Amount', digits=(16, 2), readonly=False)
    state = fields.Selection([("draft", "Draft"), ("approve", "Approve"), ("paid", "Paid"), ("cancel", "Cancel")], "State", readonly=True)
    transferencia = fields.Boolean('Es transferencia', default=True)

class ThDecimosRunLineDter(models.Model):
    _name = 'th.decimos.run.dter.lines'
    _description = 'Detalle de Decimos Tercero'
    
    name = fields.Char('Name', size=256, readonly=False)
    decimo_run_id = fields.Many2one('th.decimos.run', string='Decimo')
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=False)
    code = fields.Char('Decimo')
    dias = fields.Integer('Dias')
    retencion = fields.Float('Retencion')
    amount = fields.Float('Amount', digits=(16, 2), readonly=False)
    prestamo_id = fields.Many2one('th.discount', 'Prestamo')
    valor_prestamo = fields.Float(related="prestamo_id.amount", string='Valor Prestamo', store=True)
    state = fields.Selection([("draft", "Draft"), ("approve", "Approve"), ("paid", "Paid"), ("cancel", "Cancel")], "State", readonly=True)
    transferencia = fields.Boolean('Es transferencia', default=True)
