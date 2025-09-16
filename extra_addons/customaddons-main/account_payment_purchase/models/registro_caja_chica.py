from datetime import date, datetime, timedelta
from odoo import api, fields, models, _
import json
from odoo.tools import float_is_zero
from odoo.exceptions import ValidationError, UserError
import re

class HrRegistroCajaChicaAnticiposLine(models.Model):
    _name = 'hr.registro.caja.chica.anticipos.line'

    caja_chica_id = fields.Many2one('hr.registro.caja.chica', 'Caja Chica', ondelete='cascade')
    payment_id = fields.Many2one('account.payment', 'Pagos', ondelete='cascade')
    fecha_pago = fields.Date('Fecha Pago')
    diario_pago = fields.Many2one('account.journal','Diario de Pago')
    monto_pago = fields.Float('Monto Pago')

    @api.onchange('payment_id')
    def _onchange_payment_id(self):
        """Load related fields when payment_id changes."""
        if self.payment_id:
            self.fecha_pago = self.payment_id.date
            self.diario_pago = self.payment_id.journal_id.id
            self.monto_pago = self.payment_id.amount
        else:
            self.fecha_pago = False
            self.diario_pago = False
            self.monto_pago = 0.0

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    caja_chica_id = fields.Many2one('hr.registro.caja.chica')

class HrRegistroCajaChica(models.Model):
    _name = 'hr.registro.caja.chica'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    def action_print_pdf(self):
        """Genera y devuelve el informe PDF."""
        return self.env.ref('account_payment_purchase.registro_cajachica_rep').report_action(self)

    def _get_journal(self):
        journal = self.env['account.journal'].search([('name', '=', 'Caja Chica')], limit=1)
        return journal and journal[0] or None

    @api.model
    def create(self, vals):        
        vals['name'] = self.env['ir.sequence'].next_by_code('CAJA_CHICA')
        result = super(HrRegistroCajaChica, self).create(vals)       
        return result
    
    name = fields.Char('Registro de Caja',default='')
    fecharegistro = fields.Date('Fecha', default=fields.Date.context_today)
    fechaingreso = fields.Date('Fecha Ingreso', default=fields.Date.context_today, tracking = True)
    es_empleado = fields.Boolean('Es empleado',default = True)
    partner_id = fields.Many2one("res.partner", string="Partner Employee", store=True)
    nombres = fields.Char('Nombres')
    employee_id = fields.Many2one('hr.employee', 'Empleado', default=lambda self: self._default_employee_id(), tracking = True)
    user_id = fields.Many2one('res.users', string='Usuario',  store=True, default=lambda self: self.env.uid, readonly=True)
    state = fields.Selection([("draft","Borrador"),("revision","En Revision"),("to_approve","Pendiente Aprobacion"),("approve","Aprobado"),("paid","Pagado"),("cancel","Anulado")],"Estado",readonly=True, default='draft',tracking = True)
    line_ids = fields.One2many('hr.registro.caja.chica.line', 'caja_chica_id', 'Caja Chica Lines')
    total = fields.Float('Total Caja Chica', store = True, compute='_compute_total')
    journal_id = fields.Many2one('account.journal', 'Income Journal',states={'draft': [('readonly', False)]}, readonly=True, default = _get_journal)
    move_id = fields.Many2one('account.move', 'Mov Contable Caja Chica', readonly=True)
    company_id =  fields.Many2one('res.company', 'Compañía', required=True, readonly=True, states={'draft':[('readonly',False)]},default = lambda self: self.env['res.company']._company_default_get('hr.registro.caja.chica'))
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, states={'draft':[('readonly',False)]},default=lambda self: self.env.ref('base.USD').id)
    pagos_ids = fields.Many2many('account.payment', string="PagosCajaChica", copy=False, readonly=True, compute='_set_pagos')
    #has_pagos = fields.Boolean(compute="_get_has_pagos", help="Technical field used for usability purposes")
    has_pagos = fields.Boolean(help="Technical field used for usability purposes")
    val_pagado = fields.Float('Valor Pagado', compute='_compute_residual')
    residual = fields.Float('Residual', compute='_compute_residual')
    payments_widget = fields.Text()#compute='_get_payment_info_JSON')
    outstanding_credits_debits_widget = fields.Text()#(compute='_get_outstanding_info_JSON')
    has_outstanding = fields.Boolean()#(compute='_get_outstanding_info_JSON')
    move_caja_chica_id = fields.Many2one('account.move', 'Mov Cruce Anticipo', readonly=True)
    tiene_combustible = fields.Boolean('Tiene Combustible')#, compute="_get_has_combustible")
    caja_id = fields.Many2one('account.account','Caja', domain=[('name', 'ilike', 'Caja Chica%')], default=lambda self: self._default_caja_id())
    liquidation_move_id = fields.Many2one('account.move', string='Liquidación de Compra', readonly=True, copy=False)

    job_id = fields.Many2one('hr.job', compute="_compute_job_id", store=True, readonly=True,string="Cargo")
    line_pagos_ids = fields.One2many('hr.registro.caja.chica.anticipos.line', 'caja_chica_id',
                                     'Caja Chica Anticipos Lines')
    total_pagos_ant = fields.Float('Total', compute="_calc_total")
    fecha_revisado = fields.Date('Fecha Revisado', tracking = True)

    @api.depends('line_pagos_ids.monto_pago')
    def _calc_total(self):
        for move in self:
            tot = 0
            for line in move.line_pagos_ids:
                tot = tot + line.monto_pago
            move.total_pagos_ant = tot

    @api.depends('es_empleado','employee_id')
    def _compute_job_id(self):
        for brw_each in self:
            job_id=False
            if brw_each.es_empleado and brw_each.employee_id:
                job_id=brw_each.employee_id.job_id and brw_each.employee_id.job_id.id or False
            brw_each.job_id=job_id

    def crear_liquidacion_compra(self):
        """Crea un movimiento contable y luego reemplaza la cuenta de contrapartida con la de Reembolso por Liquidar."""
        if not (self.env.user.has_group('account_payment_purchase.group_reembolso_manager') or
                self.env.user.has_group('account_payment_purchase.group_reembolso_contador')):
            raise UserError(_('Solo usuarios autorizados pueden generar liquidación de compra.'))

        move_model = self.env['account.move']
        journal = self.env['account.journal'].search([
            ('code', '=', 'LIQCO'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if not journal:
            raise UserError(_("No se encontró un Diario de Liquidación con el código 'LIQCO'."))

        for record in self:
            existe_mov = self.env['account.move.line'].search([('caja_chica_id', '=', record.id)])
            if existe_mov:
                raise UserError(_("Ya existe una liquidación para el registro de caja chica %s") % (existe_mov.move_id.name))

            record.journal_id = journal.id

            if not record.line_ids:
                raise UserError(_("La caja chica no tiene líneas registradas."))

            move_lines = []
            total_amount = 0

            for line in record.line_ids:
                if line.verificado:
                    product = line.tipo.product_id
                    tax = line.tipo.taxes_id

                    if not tax:
                        raise UserError(_("El rubro %s no tiene una cuenta de impuesto configurada.") % product.name)

                    line_vals = {
                        'account_id': product.property_account_expense_id.id,
                        'name': product.name,
                        'quantity': 1,
                        'debit': line.valor_aprobado,
                        'credit': 0.0,
                        'price_unit': line.valor_aprobado,
                        'analytic_distribution': {str(line.cuenta_analitica_id.id): 100} if line.cuenta_analitica_id else {},
                        'product_id': product.id,
                        'caja_chica_id': record.id,
                    }

                    if tax:
                        line_vals['tax_ids'] = [(6, 0, [tax.id])]

                    move_lines.append((0, 0, line_vals))
                    total_amount += line.valor_aprobado

            if not move_lines:
                raise UserError(_("No hay líneas verificadas para crear la liquidación de compra."))

            # Crear el movimiento contable
            move_vals = {
                'move_type': 'in_invoice',  # ← se crea con tipo factura para que Odoo genere la contrapartida
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'invoice_date': fields.Date.today(),
                'ref': record.name,
                'line_ids': move_lines,
                'partner_id': record.employee_id.partner_id.id,
                'payment_reference': record.name,
            }

            move = move_model.create(move_vals)

            # Buscar el partner Reembolso y su cuenta contable
            partner_reembolso = self.env['res.partner'].search([('name', '=', 'Caja Chica')], limit=1)
            if not partner_reembolso or not partner_reembolso.property_account_payable_id:
                raise UserError(_('El contacto "Caja Chica" no tiene configurada cuenta por pagar.'))

            # Buscar la línea contable de contrapartida generada automáticamente
            payable_line = move.line_ids.filtered(
                lambda l: l.account_id.account_type == 'liability_payable' and l.credit > 0
            )
            if not payable_line:
                raise UserError(_('No se encontró la línea contable de contrapartida (cuenta por pagar) para modificar.'))

            # Reemplazar cuenta contable por la de reembolsos por liquidar
            payable_line.account_id = partner_reembolso.property_account_payable_id
            payable_line.date_maturity = fields.Date.today()

            # Enlazar movimiento a registro
            record.write({'liquidation_move_id': move.id})

    def crear_liquidacion_compraOrigen(self):
        """Crea un movimiento contable de liquidación de compra con impuestos desde el tipo de rubro."""
        if not (self.env.user.has_group('account_payment_purchase.group_caja_chica_contador') or self.env.user.has_group('account_payment_purchase.group_caja_chica_manager')):
            raise UserError(_('Solo usuarios autorizados pueden generar una liquidación de compra.'))

        move_model = self.env['account.move']
        journal = self.env['account.journal'].search([('code','=','LIQCO'), ('company_id','=',self.company_id.id)], limit=1)

        if not journal:
            raise UserError(_("No se encontró un Diario de Liquidación con el código 'LIQCO'."))

        for record in self:
            existe_mov = self.env['account.move.line'].search([('caja_chica_id','=',record.id)])
            if existe_mov:
                raise UserError(_("Ya existe una liquidacion para el registro de caja chica %s")%(existe_mov.move_id.name))
            record.journal_id = journal.id
            if not record.line_ids:
                raise UserError(_("La caja chica no tiene líneas registradas."))

            move_lines = []
            total_amount = 0

            for line in record.line_ids:
                if line.verificado:
                    product = line.tipo.product_id
                    tax = line.tipo.taxes_id  # Obtener el impuesto desde el tipo de rubro

                    if not tax:
                        raise UserError(_("El rubro %s no tiene una cuenta de impuesto configurada.") % product.name)

                    line_vals = {
                        'account_id': product.property_account_expense_id.id,
                        'name': product.name,
                        'quantity': 1,
                        'debit': line.valor_aprobado,
                        'credit': 0.0,
                        'price_unit': line.valor_aprobado,
                        'analytic_distribution': {str(line.cuenta_analitica_id.id): 100} if line.cuenta_analitica_id else {},
                        'product_id': product.id,
                        'caja_chica_id':record.id
                    }

                    if tax:
                        line_vals['tax_ids'] = [(6, 0, [tax.id])]  # Asigna el impuesto

                    move_lines.append((0, 0, line_vals))
                    total_amount += line.valor_aprobado

            if not move_lines:
                raise UserError(_("No hay líneas verificadas para crear la liquidación de compra."))
            #busco el partner
            partner = self.env['res.partner'].search([('name','=','Caja Chica')])
            move_lines.append((0, 0, {
                'account_id': partner.property_account_payable_id.id,
                'name': 'Caja Chica - %s' % record.name,
                'quantity': 1,
                'debit': 0.0,
                'credit': total_amount,
                'caja_chica_id': record.id,
            }))
            move_vals = {
                'move_type': 'in_invoice',
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'invoice_date': fields.Date.today(),
                'ref': record.name,
                'line_ids': move_lines,
                'partner_id': record.employee_id.partner_id.id,#partner.id,#
            }

            move = move_model.create(move_vals)
            record.write({'liquidation_move_id': move.id})

    @api.model
    def _default_employee_id(self):
        """Devuelve el empleado relacionado con el usuario actual."""
        user = self.env.user
        if not self.env['hr.employee'].search([('partner_id', '=', user.partner_id.id)], limit=1):
            return  self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        else:
            return self.env['hr.employee'].search([('partner_id', '=', user.partner_id.id)], limit=1)
        
    @api.model
    def _default_caja_id(self):
        """Devuelve la caja del empleado relacionado con el usuario actual."""
        user = self.env.user
        if not self.env['hr.employee'].search([('partner_id', '=', user.partner_id.id)], limit=1):
            empleado =  self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        else:
            empleado =  self.env['hr.employee'].search([('partner_id', '=', user.partner_id.id)], limit=1)
        nombre_completo = (empleado.last_name or '') #+ ' ' + (empleado.mother_last_name or '')
        return self.env['account.account'].search([('name', 'ilike', nombre_completo.strip())], limit=1)
        
    def action_print_pdf(self):
        """Genera y devuelve el informe PDF con validaciones previas."""
        # Verificar si existe alguna línea con diferencias y el reembolso está aprobado
        for line in self.line_ids:
            if line.valor != line.valor_aprobado:
                # Si el reembolso está aprobado y hay diferencias sin motivo, levantar un error
                if line.caja_chica_id.state == 'approve' and not line.observacion:
                    raise UserError(_(
                        "No puedes imprimir el documento porque existen líneas con diferencias en el 'Valor' y 'Valor Aprobado' "
                        "sin un 'Motivo' especificado."
                    ))
        
        # Si todo está validado, generar el informe
        return self.env.ref('account_payment_purchase.registro_cajachica_rep').report_action(self)

    @api.constrains('fechaingreso', 'line_ids', 'line_ids.fecha')
    def check_fechasemana(self):
        if self.fechaingreso:
            fechaing = self.fechaingreso
        for line in self.line_ids:
            if line.fecha > fechaing:
                raise UserError(_('No puede ingresar caja chica con fecha %s mayor a la de ingreso.') % (line.fecha))

    @api.depends('total', 'val_pagado', 'total_pagos_ant')
    def _compute_residual(self):
        for record in self:
            val_pagado = sum(line.monto_pago for line in record.line_pagos_ids)
            record.val_pagado = val_pagado
            record.residual = record.total - record.val_pagado

    @api.depends('line_ids.valor','line_ids.valor_aprobado')
    def _compute_total(self):
        total = 0
        for record in self:
            if record.state == 'draft' or record.state == 'revision':
                total = sum(line.valor for line in record.line_ids)
            if record.state == 'to_approve' or record.state == 'approve':
                total = sum(line.valor_aprobado for line in record.line_ids)
            record.total = total

    @api.depends('pagos_ids')
    def _get_has_pagos(self):
        for record in self:
            record.has_pagos = bool(record.pagos_ids)

    @api.depends('line_ids')
    def _get_has_combustible(self):
        for record in self:
            record.tiene_combustible = any(line.tipo.name == 'Combustible' for line in record.line_ids)

    @api.depends('pagos_ids')
    def _get_payment_info_JSON(self):
        for record in self:
            payments_info = {'title': _('Less Payment'), 'outstanding': False, 'content': []}
            if record.pagos_ids:
                for payment in record.pagos_ids:
                    if payment.state == 'posted':
                        payments_info['content'].append({
                            'name': payment.name,
                            'journal_name': payment.journal_id.name,
                            'amount': payment.amount,
                            'currency': record.currency_id.symbol,
                            'date': payment.payment_date,
                            'payment_id': payment.id,
                            'move_id': payment.move_id.id,
                            'ref': payment.move_id.name,
                        })
            record.payments_widget = json.dumps(payments_info)

    def procesa_combustibles(self):
        lines = []
        for line in self.line_ids:
            if line.tipo.name == 'Combustible':
                vals = {
                    'vehicle_id': line.vehicle_id.id,
                    'amount': line.valor,
                    'purchaser_id': self.employee_id.partner_id.id if self.es_empleado else self.partner_id.id,
                    'date': line.fecha,
                    'notes': f"{line.beneficiario} {line.observacion}"
                }
                lines.append(vals)
                self.env['fleet.vehicle.log.fuel'].create(vals)

    def assign_outstanding_credit_reemb(self, credit_aml_id):
        self.ensure_one()
        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if not credit_aml.currency_id and self.currency_id != self.company_id.currency_id:
            credit_aml.with_context(allow_amount_currency=True).write({
                'amount_currency': self.company_id.currency_id.with_context(date=credit_aml.date).compute(credit_aml.balance, self.currency_id),
                'currency_id': self.currency_id.id
            })
        if credit_aml.payment_id:
            credit_aml.payment_id.write({'reembolso_ids': [(4, self.id, None)]})
        return self.register_payment(credit_aml)

    def register_payment(self, payment_line, writeoff_acc_id=False, writeoff_journal_id=False):
        line_to_reconcile = self.env['account.move.line']
        for inv in self:
            line_to_reconcile += inv.move_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
        return (line_to_reconcile + payment_line).reconcile(writeoff_acc_id, writeoff_journal_id)

    def button_payments_caja_chica(self):
        return {
            'name': _('Pago de Caja Chica'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', [x.id for x in self.pagos_ids])],
        }

    # @api.depends('name')
    # def _set_pagos(self):
    #     for record in self:
    #         pagos = self.env['account.payment.line'].search([('reembolso_id', '=', record.id)])
    #         payments = self.env['account.payment'].browse([x.payment_id.id for x in pagos])
    #         record.pagos_ids = payments.filtered(lambda p: p.state == 'posted')

    def test_state(self, discount_id):
        for discount in self.browse(discount_id):
            discount.write({'state': 'approve' if discount.paid else 'paid'})
        return True

    def create_move_line(self, discount, partner, account, debit, credit, move_id, reference):
        return self.env['account.move.line'].with_context(check_move_validity=False).create({
            'name': reference or '/',
            'debit': debit,
            'credit': credit,
            'reference': reference,
            'account_id': account,
            'move_id': move_id,
            'journal_id': discount.journal_id.id,
            'partner_id': partner,
            'date': discount.fechaingreso,
        })

    def generate_move_line_credit(self, discount, partner_id, move_id, tot, ref):
        self.create_move_line(discount, partner_id, self.env['res.partner'].browse(partner_id).property_account_payable_id.id, 0, tot, move_id, ref)
        return True

    def button_revision(self):
        if not self.env.user.has_group('account_payment_purchase.group_reembolso_contador'):
            raise UserError(_('Solo usuarios autorizados pueden enviar a revision los documentos de reembolso!!.'))
        for x in self:
            x.write({'state': 'revision','fecha_revisado':fields.Date.today()})
            #self._compute_total()
        return True
    
    def button_to_approve(self):
        if not self.env.user.has_group('account_payment_purchase.group_caja_chica_contador'):
            raise UserError(_('Solo usuarios autorizados pueden enviar a aprobar.'))
        for x in self.line_ids:
            if not x.verificado:
                raise UserError(_('No se ha verificado el valor aprobado!!.'))
            if x.valor != x.valor_aprobado and not x.observacion:
                raise UserError(_(
                        "No puedes aprobar el documento porque existen líneas con diferencias en el 'Valor' y 'Valor Aprobado' "
                        "sin un 'Motivo' especificado."
                    ))
        for x in self:
            x.write({'state': 'to_approve'})
        return True

    def button_approve(self):
        if not self.env.user.has_group('account_payment_purchase.group_caja_chica_manager'):
            raise UserError(_('Solo usuarios autorizados pueden aprobar.'))
        for cchica in self:
            cchica.write({'state': 'approve'})#, 'move_id': move_id.id})
            self._compute_total()
        return True

    def button_set_draft(self):
        self.write({'state': 'draft'})
        return True

    def button_canceled(self):
        move_pool = self.env['account.move']
        for reembolso in self:
            if reembolso.liquidation_move_id:
                reembolso.liquidation_move_id.unlink()
            if reembolso.move_id and reembolso.move_id.state == 'posted':
                reembolso.move_id.line_ids.remove_move_reconcile()
                reembolso.move_id.button_cancel()
                reembolso.move_id.unlink()
            elif reembolso.move_id:
                reembolso.move_id.unlink()

            # if reembolso.move_reembolso_id and reembolso.move_reembolso_id.state == 'posted':
            #     reembolso.move_reembolso_id.line_ids.remove_move_reconcile()
            #     reembolso.move_reembolso_id.button_cancel()
            #     reembolso.move_reembolso_id.unlink()
            # elif reembolso.move_reembolso_id:
            #     reembolso.move_reembolso_id.unlink()

            reembolso.write({'state': 'cancel'})
        return True



class HrRegistroCajaChicaLine(models.Model):
    _name = 'hr.registro.caja.chica.line'
    _order = 'fecha'

    caja_chica_id = fields.Many2one('hr.registro.caja.chica', 'CajaChica', ondelete='cascade')
    identification_id = fields.Char('Cedula/RUC')
    beneficiario = fields.Char('Pagado a')
    tipo = fields.Many2one('hr.rubros', 'Tipo', domain="[('otros', '=', True)]")
    name_tipo=fields.Selection(related='tipo.name')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehiculo')
    fecha = fields.Date('Fecha')
    tipo_documento = fields.Selection([('Factura', 'Factura'), ('Vale', 'Vale de Caja'), ('Soporte', 'Soporte')], 'Tipo Doc', default='Factura')
    nro_documento = fields.Char('Documento')
    observacion = fields.Char('Motivo')
    valor = fields.Float('Valor')
    valor_aprobado = fields.Float('Valor Aprobado')
    verificado = fields.Boolean('Verificado')
    #cuenta_analitica_id = fields.Many2one('account.analytic.account', 'Cuenta Analitica')
    company_id = fields.Many2one(
        'res.company', 
        string="Compañía", 
        related='caja_chica_id.company_id', 
        store=True, 
        readonly=True
    )
    cuenta_analitica_id = fields.Many2one(
    'account.analytic.account', 
    'Cuenta Analitica', 
    domain="[('company_id', '=', parent.company_id)]"
    )
    
    @api.onchange('valor_aprobado')
    def onchange_valor_aprobado(self):
        for x in self:
            if x.valor_aprobado:
                x.verificado = True
                
    @api.constrains('tipo_documento', 'observacion')
    def _check_observacion_for_vale(self):
        for record in self:
            # Validar que el campo observacion sea obligatorio si el tipo de documento es 'Vale'
            if record.tipo_documento == 'Vale' and not record.observacion:
                raise ValidationError(_("El campo 'Motivo' es obligatorio cuando el tipo de documento es 'Vale'."))
            
    @api.constrains('tipo_documento', 'nro_documento')
    def _check_nro_documento_format(self):
        for record in self:
            # Solo validar si el tipo de documento es 'Factura'
            if record.tipo_documento == 'Factura':
                # Definir el formato esperado del número de documento usando una expresión regular
                # Formato: 3 dígitos - 3 dígitos - 9 dígitos (Ej: 001-001-000000001)
                pattern = r'^\d{3}-\d{3}-\d{9}$'
                if not re.match(pattern, record.nro_documento):
                    raise ValidationError(_("El número de documento debe estar en el formato 001-001-000000001 (3 dígitos-3 dígitos-9 dígitos)."))
                
    @api.constrains('tipo_documento', 'nro_documento', 'identification_id')
    def _check_unique_invoice(self):
        for record in self:
            # Solo validar si el tipo de documento es 'Factura'
            if record.tipo_documento == 'Factura':
                existing_records = self.env['hr.registro.caja.chica.line'].search([
                    ('tipo_documento', '=', 'Factura'),
                    ('nro_documento', '=', record.nro_documento),
                    ('identification_id', '=', record.identification_id),
                    ('id', '!=', record.id)  # Excluir el registro actual
                ])
                if existing_records:
                    raise ValidationError(_("La combinación de Número de Documento y Cedula/RUC ya existe para una Factura. Por favor, verifique los datos."))

    def obtiene_nombre_tipo(self):
        return f"{self.tipo.name} {self.tipo.unidad_administrativa.name} {self.observacion or '/'} {self.nro_documento or '/'}"

    @api.constrains('fecha')
    def _check_date_within_period(self):
        for line in self:
            if line.caja_chica_id.fechaingreso and line.fecha:
                registro_period = line.caja_chica_id.fechaingreso.strftime('%Y-%m')  # Año y mes de la cabecera
                line_period = line.fecha.strftime('%Y-%m')  # Año y mes de la línea
                if registro_period != line_period:
                    raise ValidationError(f"La fecha no pertenece al periodo {line.fecha} debe estar dentro del mismo período que la fecha de registro {line.caja_chica_id.fechaingreso}.")