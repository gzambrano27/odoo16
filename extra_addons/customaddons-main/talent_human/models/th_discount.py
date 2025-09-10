from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class th_discount(models.Model):
    
    
    _name = 'th.discount' 
    
    name = fields.Many2one('th.transaction.type', 'Nombre', readonly=True)
    type = fields.Selection([('discount','Discount'),('advance','Advance'),('loans','Loans'),],'type')
    user_id = fields.Many2one('res.users', string='User',  store=True, default=lambda self: self.env.uid, readonly=True)
    #generate_lines_employee  = fields.related('name', 'generate_lines_employee', type='boolean', string='Generate Lines of all employee', readonly=True),
    generate_lines_employee = fields.Boolean(related = 'name.generate_lines_employee',  string='Generate Lines of all employee')
    ref = fields.Char('Ref',size=256,readonly=True)
    employee_id = fields.Many2one('hr.employee', 'Empleado',readonly=True)
    #partner_id = fields.Many2one('partner_id', related = 'employee_id', relation="res.partner", string="Partner Employee", store=True)
    partner_id = fields.Many2one("res.partner", string="Partner Employee", store=True)
    contract_id = fields.Many2one('hr.contract', 'Contrato',readonly=True, domain="[('employee_id', '=', employee_id)]")
    period_id = fields.Integer('Force Period', help="Keep empty to use the period of the validation date.")
    journal_id = fields.Many2one('account.journal', 'Expense Journal')
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True)
    user_id = fields.Many2one('res.users', 'User',default=lambda self: self.env.user.id)
    company_id =  fields.Many2one('res.company', 'Company',default = lambda self: self.env['res.company']._company_default_get('hr.discount'))
    collection_form = fields.Selection([('middle_month','Middle of the month'),('end_month','End of the month'),('middle_end_month','Middle and End of the month'),], 'Forma de Cobro/Pago',default = 'end_month')
    date = fields.Date('Date register')
    date_from = fields.Date('Date From')
    amount = fields.Float('Monto')
    interest = fields.Float('% Interes')
    number_of_quotas = fields.Integer('Numero de cuotas',readonly=True,default=1)
    lines_ids = fields.One2many('th.discount.lines', 'discount_id', 'Pays', required=False)
    amount_to_paid = fields.Float(string='Monto a Pagar')
    value_quota = fields.Float(string='Valor/Cuota')
    amount_paid = fields.Float(string='Monto Pagado')
    amount_remain = fields.Float(string='Monto Restante')
    quotas_paid = fields.Integer(string='Cuotas Pagadas')
    quotas_remain = fields.Integer(string='Cuotas Restantes')
    transferencia = fields.Boolean('Es transferencia',default = True)
    
    
    paid = fields.Boolean(string='Paid?')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)#,default = _get_currency)
    state = fields.Selection([("draft","Draft"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True, default='draft',)
    
    advance_run_id = fields.Many2one('th.discount.run', 'Descuentos', readonly=True, ondelete="cascade")
    observacion = fields.Text('Observacion')
    #para descuentos
    articulo_id = fields.Many2one('th.reglamento.interno', string='Articulo Reglamento')
    codigo_art = fields.Char(related='articulo_id.cod_articulo',store = True)
    descripcion_art = fields.Text(related='articulo_id.descripcion',store = True)
    tipo = fields.Selection([("valor","Valor"),("porcentaje","Porcentaje")],"Tipo Descuento", default='valor')
    porcentaje = fields.Float('% Descuento', digits=(16,2))
    jefe = fields.Char('Jefe')
    identificacion_jefe = fields.Char('Identificacion Jefe')
    
    pagos_ids = fields.Many2many('account.payment', string="PagosPrestamos")
    has_pagos = fields.Boolean(help="Technical field used for usability purposes")

    def button_approve(self, discount_id):
        hr_admin_group = self.env.ref('hr.group_hr_manager')
        account_admin_group = self.env.ref('account.group_account_manager')
        
        if not (hr_admin_group in self.env.user.groups_id or account_admin_group in self.env.user.groups_id):
            raise UserError(_('Solo los administradores de Recursos Humanos o Administradores Contables pueden aprobar.'))

        
        move_pool = self.env['account.move']
        
        if not self:
            self = self.browse(discount_id)
        
        for discount in self:
            if discount.name.type_expense != 'discount':
                if not discount.journal_id:
                    raise ValidationError(_('Debe definir un diario para el descuento del empleado.'))
                
                if not discount.generate_lines_employee:
                    self.create_lines_discount(discount)
                    if not discount.employee_id.partner_id:
                        raise ValidationError(_('El empleado %s no tiene un socio creado.') % discount.employee_id.name)

                if not (discount.name.credit_account_id and discount.name.debit_account_id):
                    raise ValidationError(_('Debe seleccionar una cuenta de débito y crédito en el tipo de descuento.'))
                
                sequence = discount.journal_id.sequence_id
                name = sequence.with_context(ir_sequence_date=discount.date).next_by_id()
                ref = f"{discount.name.name} - {discount.ref}"
                
                move_id = move_pool.create({
                    'name': name,
                    'journal_id': discount.journal_id.id,
                    'date': discount.date,
                    'ref': ref,
                    'company_id': discount.company_id.id,
                })
                
                if not discount.generate_lines_employee:
                    self.create_move_line(discount, discount.employee_id.partner_id.id, discount.name.debit_account_id.id, discount.amount_to_paid, 0, move_id.id, 1, ref)
                    self.generate_move_line_credit(discount, discount.employee_id.partner_id.id, move_id.id, 1, ref)
                else:
                    for line in discount.lines_ids:
                        self.create_move_line(discount, line.employee_id.partner_id.id, discount.name.debit_account_id.id, line.amount, 0, move_id.id, 1, ref)
                    self.generate_move_line_credit(discount, discount.company_id.partner_id.id, move_id.id, 1, ref)
                
                move_id.post()
                discount.write({'state': 'approve', 'move_id': move_id.id, 'period_id': 1})
            else:
                discount.write({'state': 'approve', 'period_id': 1})
        
        self.finalize_discount()
        return True

    def button_approve_total(self, discount_id):
        move_pool = self.env['account.move']
        
        if not self:
            self = self.browse(discount_id)
        
        acum_dscto = 0
        
        for discount in self:
            if not discount.journal_id:
                raise ValidationError(_('Debe definir un diario para el descuento del empleado.'))
            
            if not discount.generate_lines_employee:
                self.create_lines_discount(discount)
                if not discount.employee_id.partner_id:
                    raise ValidationError(_('El empleado %s no tiene un socio creado.') % discount.employee_id.name)

            if not (discount.name.credit_account_id and discount.name.debit_account_id):
                raise ValidationError(_('Debe seleccionar una cuenta de débito y crédito en el tipo de descuento.'))
            
            discount.write({'state': 'approve', 'period_id': 1})
            acum_dscto += discount.amount_to_paid
        
        return {'descuento': acum_dscto, 'journal': discount.journal_id.id}
    


class ThDiscountLine(models.Model):
    
    _name = 'th.discount.lines' 

    name = fields.Char('Name', size=256,  readonly=False)
    payslip_id = fields.Many2one('hr.payslip', 'Payslip')
    bonificacion_id = fields.Many2one('hr.bonificacion', 'Bonificacion')
    vac_line_id = fields.Many2one('hr.vacations.historic.line', 'Vacacion')
    bonus_id = fields.Many2one('th.employee.bonus', 'Abono')
    decimo_tercer_id = fields.Many2one('hr.decimos.run.dter.lines','Decimo Tercero')
    employee_id = fields.Many2one('hr.employee', 'Employee',readonly=False)
    date = fields.Date('Date')
    date_paid = fields.Date()#'date_to',related = 'payslip_id',relation='hr.payslip')
    amount = fields.Float('Amount', digits=(16,2), readonly=False)
    discount_id = fields.Many2one('th.discount','Discount')
    move_line_id = fields.Many2one('account.move.line', 'Accounting Entry Line', readonly=True)
    number_quota = fields.Integer('Number Quota')
    state = fields.Selection([("draft","Draft"),("approve","Approve"),("paid","Paid"),("cancel","Cancel")],"State",readonly=True)
    
class ThReglamentoInterno(models.Model):
    _name = 'th.reglamento.interno'
    
    name = fields.Char('Name', size=256)
    cod_articulo = fields.Char('Articulo', size=20)
    descripcion = fields.Text('Descripcion')
    state = fields.Selection([("activo","Activo"),("inactivo","Inactivo")],"State",default='activo')
    
    