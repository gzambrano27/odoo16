from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class hr_discount_run(models.Model):
    _name = 'th.discount.run'
    _description = 'Anticipos Generales'
    
                    
      
    user_id = fields.Many2one('res.users', string='User',  store=True, default=lambda self: self.env.user.id, readonly=True)
    name = fields.Char('Name', size=64, default = 'Anticipo de Quincena ')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Aprobado'),
        ('paid', 'Pagado'),
        ('cancel', 'Cancelado'),
    ], default = 'draft',)
    date_start = fields.Date('Date From')
    date_end = fields.Date('Date To')
    reference = fields.Char('Reference', size=64, default = 'Anticipo de Quincena ')
    transaction_type_id = fields.Many2one('th.transaction.type', 'Motivo')
    type = fields.Selection([('discount','Discount'),('advance','Advance'),('loans','Loans'),],'type')
    # company_id = fields.Many2one('res.company', 'Company', default=lambda self: self._get_company())
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company.id)
    discount_ids = fields.One2many('th.discount', 'advance_run_id', 'Payslips')
    total_quincena = fields.Float(compute = '_calculate_total',string='Total de Quincena', digits = (16,2), multi='total')
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True)
    journal_id = fields.Many2one('account.journal', 'Expense Journal', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)#,default = _get_currency)
    #opciones de pago
    pagos_ids = fields.Many2many('account.payment', string="PagosAnticipos", copy=False, readonly=True)
    has_pagos = fields.Boolean(help="Technical field used for usability purposes")
    #para generar archivo
    csv_export_file = fields.Binary('CSV File')
    csv_export_filename = fields.Char('CSV Filename', size=50, readonly=True)
    #si es anticipo agricola
    date_registro = fields.Date('Fecha Registro',  default=fields.Date.context_today)
    anticipo_agricola = fields.Boolean('Agricola')
    anticipo_empaque = fields.Boolean('Empaque')
    anticipo_serv_prestados = fields.Boolean('Serv Prestados')
    residual = fields.Float('Residual', digits=(16,2), store= True)
    val_pagado = fields.Float('Valor Pagado', digits=(16,2))
    payments_widget = fields.Text()
    

    def button_payments_anticipos(self):
        return {
            'name': _('Pago de Anticipos del Personal'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.pagos_ids.ids)],
            'target': 'current',  # Optional: Defines if the window should replace the current one or open in a new tab
        }

    @api.depends('discount_ids')
    def _calculate_total(self):
        for advance in self:
            total = 0
            for line in advance.discount_ids:
                total += line.amount_to_paid
            advance.total_quincena = total

    def button_approve(self):
        discount_pool = self.env['th.discount']
        for advances in self:
            if not advances.discount_ids:
                raise ValidationError(_('Error! No puede aprobar, porque no tiene empleados seleccionados'))
            else:
                acum_anticipo = 0
                for anticipo in advances.discount_ids:
                    company = self.env.company
                    if not company.asientos_tot_rrhh:
                        discount_pool.browse([anticipo.id]).button_approve()
                    else:
                        discount = self.env['th.discount']
                        valor = discount_pool.button_approve_total([anticipo.id])
                        acum_anticipo += valor.get('descuento')
                        diario = valor.get('journal')
                # Insertar un solo registro
                if company.asientos_tot_rrhh:
                    move_pool = self.env['account.move']

                    name = self.env['ir.sequence'].next_by_id(diario.sequence_id.id)
                    ref = self.reference
                    move_id = move_pool.create({
                        'name': name,
                        'journal_id': diario,
                        'date': anticipo.date_from,
                        'ref': ref,
                        'company_id': anticipo.company_id.id,
                    })
                    # Crear líneas de asientos contables
                    self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'name': name or '/',
                        'debit': acum_anticipo,
                        'credit': 0,
                        'reference': ref,
                        'account_id': self.transaction_type_id.debit_account_id.id,
                        'move_id': move_id.id,
                        'journal_id': diario,
                        'partner_id': self.company_id.partner_id.id,
                        'date': anticipo.date_from,
                    })
                    self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'name': name or '/',
                        'debit': 0,
                        'credit': acum_anticipo,
                        'reference': ref,
                        'account_id': self.transaction_type_id.credit_account_id.id,
                        'move_id': move_id.id,
                        'journal_id': diario,
                        'partner_id': self.company_id.partner_id.id,
                        'date': anticipo.date_from,
                    })
                    move_id.post()
                self.write({'state': 'approve', 'move_id': move_id.id})
        return True
    def button_canceled(self):
        discount_pool = self.env['th.discount']
        move_pool = self.env['account.move']
        for advances in self:
            if not advances.discount_ids:
                raise ValidationError(_('Error! No puede cancelar, porque no tiene empleados seleccionados'))
            else:
                for anticipo in advances.discount_ids:
                    discount_pool.browse(anticipo.id).button_canceled()
                if advances.move_id:
                    if advances.move_id.state == 'posted':
                        advances.move_id.line_ids.remove_move_reconcile()
                        advances.move_id.button_draft()  # Se usa button_draft() en lugar de button_cancel() en Odoo 16
                        advances.move_id.unlink()
                    else:
                        # Eliminar el registro contable
                        advances.move_id.unlink()
                self.write({'state': 'cancel'})
            
            # Reversar los partes tomados en ese anticipo
            if advances.anticipo_agricola:
                fecha_ini = advances.date_start
                fecha_fin = advances.date_end
                for d in advances.discount_ids:
                    sql_parte = """
                        SELECT id FROM registro_partes_line
                        WHERE date BETWEEN %s AND %s
                        AND employee_id = %s
                    """
                    self.env.cr.execute(sql_parte, (fecha_ini, fecha_fin, d.employee_id.id))
                    results_parte = self.env.cr.dictfetchall()
                    for p in results_parte:
                        self.env['registro.partes.line'].browse(p['id']).write({'state': 'draft'})
        return True

    def button_set_draft(self):
        discount_pool = self.env['th.discount']
        for advances in self:
            if advances.discount_ids:
                for anticipo in advances.discount_ids:
                    discount_pool.browse(anticipo.id).button_set_draft()
            self.write({'state': 'draft'})
        return True