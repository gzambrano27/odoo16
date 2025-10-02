# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models,api,_
from odoo.exceptions import ValidationError
from datetime import datetime
from bs4 import BeautifulSoup

from . import DEFAULT_MODE_PAYMENTS

class AccountPaymentRequestPurchase(models.Model):
    _name = 'account.payment.request'
    _description="Solicitud de Pagos"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_default_date_maturity(self):
        return fields.Date.context_today(self)

    @api.model
    def _get_default_date(self):
        return fields.Date.context_today(self)


    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,readonly=False
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)

    origin=fields.Selection([('automatic','Automatica'),
                           ('manual','Manual')
                           ],string="Origen",default="automatic",tracking=True)

    type=fields.Selection([('purchase.order','Orden de Compra'),
                           ('account.move','Factura/Asiento'),
                           ('request','Solicitud'),
                           ('hr.employee.payment', 'Rol de Pagos/Prestamos'),
                           ('hr.employee.liquidation', 'Liquidación')
                           ],string="Tipo",default="request",tracking=True)

    manual_type = fields.Selection([
                                    ('purchase.order', 'Orden de Compra'),
                                     ('request', 'Solicitud')
                             ], string="Tipo Manual", default=None, tracking=True)

    type_document=fields.Selection([('quota','Cuota'),
                                     ('document','Documento'),
                                     ('work_acceptance', 'Aceptación de Trabajo')
                           ],string="Tipo de Documento",default="document",tracking=True)

    picking_id = fields.Many2one("stock.picking", string="Recepción Relacionada")
    work_acceptance_id = fields.Many2one("work.acceptance", string="Aceptación Relacionada")

    type_module=fields.Selection([('financial','Financiero'),
                           ('payslip','Nómina')],string="Tipo de Módulo",default="financial")

    payment_employee_id = fields.Many2one("hr.employee.payment", "Nómina", required=False, tracking=True)
    liquidation_employee_id = fields.Many2one("hr.employee.liquidation", "Liquidación", required=False, tracking=True)

    order_id=fields.Many2one("purchase.order","Orden de Compra",required=False,tracking=True)
    invoice_id = fields.Many2one("account.move", "Factura/Asiento", required=False,tracking=True)

    invoice_line_id = fields.Many2one("account.move.line", "Cuota de Factura/Asiento", required=False,tracking=True)
    invoice_line_ids = fields.Many2many("account.move.line","acct_payment_request_wizard_inv_lines_rel","wizard_id","invoice_id", "Cuota de Factura/Asiento", required=False, tracking=True)

    payment_term_id=fields.Many2one("account.payment.term","Terminos de Pago",required=False,tracking=True)
    quota=fields.Integer("Cuota",required=True)
    date=fields.Date("Fecha de Solicitud",required=True,tracking=True,default=_get_default_date)

    date_maturity = fields.Date("Fecha de Vencimiento", required=True,tracking=True,default=_get_default_date_maturity)
    date_payment = fields.Date("Ult. Fecha de Pago", required=False, compute="_compute_total",store=True,readonly=True)
    partner_id=fields.Many2one("res.partner","Proveedor",required=True,tracking=True)
    vat=fields.Char(related="partner_id.vat",store=False,readonly=True,string="# Identificacion")

    amount_original=fields.Monetary("Valor Original",required=True,tracking=True,default=0.01)
    amount=fields.Monetary("Valor",required=True,tracking=True,default=0.01)
    paid = fields.Monetary("Pagado", compute="_compute_total",store=True,readonly=True,tracking=True)
    pending = fields.Monetary("Pendiente", compute="_compute_total",store=True,readonly=True,tracking=True)

    comments=fields.Text("Comentarios",tracking=True)

    description_motive = fields.Char("Motivo", tracking=True,size=255)

    state=fields.Selection([('draft','Preliminar'),
                            ('confirmed','Confirmado'),
                            ('done','Realizado'),
                            ('cancelled', 'Anulado'),
                           ('locked', 'Bloqueado'),
                            ],string="Estado",default="draft",tracking=True)

    name=fields.Char(compute="_compute_full_name",store=True,readony=True,string="Descripcion")
    adjust = fields.Boolean(compute="_compute_adjust", store=True, readony=True, string="Ajuste de Fecha")
    is_prepayment = fields.Boolean("Es prepago?", default=False)
    payment_ids=fields.One2many("account.payment","payment_request_id","Pagos")

    consolidated_payment_ids = fields.Many2many(
        "account.payment",
        "request_consolidated_payment_rel",
        "request_id",
        "payment_id",
        string="Pagos consolidados",
        compute="_compute_consolidated_payment_ids",
    )

    @api.depends('payment_ids','payment_employee_id','liquidation_employee_id')
    def _compute_consolidated_payment_ids(self):
        for rec in self:
            consolidated_payment_ids= self.env["account.payment"].sudo()
            if rec.payment_employee_id:
                consolidated_payment_ids+=rec.sudo().payment_employee_id.get_full_payments()
            if rec.payment_ids:
                consolidated_payment_ids+= rec.sudo().payment_ids
            rec.consolidated_payment_ids = consolidated_payment_ids

    macro_line_ids = fields.One2many("account.payment.bank.macro.line",'request_id', "Detalle de Macro")

    temporary=fields.Boolean("Temporal",default=False)

    enable_payment_bank_ids = fields.Many2many(
        'res.bank',
        compute='_compute_enable_payment_bank_ids',
        string='Registrados en el Banco',
        search='_search_enable_payment_bank_ids'
    )

    amount_residual=fields.Monetary(compute="_get_compute_amount_residual",string="Saldo Act. del Documento",required=False,tracking=True,default=0.00)
    amount_request_residual = fields.Monetary(compute="_get_compute_amount_request_residual", string="Disponible en Sol.",
                                      required=False, tracking=True, default=0.00)

    checked=fields.Boolean("Verificado",default=False,tracking=True)

    request_wizard_id = fields.Many2one('account.payment.analysis.request.wizard', 'Lote de Sol. de Generacion')
    request_wizard_comments=fields.Char(related="request_wizard_id.comments",store=False,readonly=True)
    request_type_id = fields.Many2one('account.payment.request.type', "Motivo de Solicitud", required=True )

    percentage=fields.Float("% Aplicado",default=0.00,digits=(16,2))

    document_ref=fields.Html('Referencia de Documento')

    document_ref_clean = fields.Char("Referencia Limpia", compute="_compute_document_ref_clean", store=True)

    payment_line_ids=fields.One2many('account.payment.request.lines','request_id', string="Cuentas")

    @api.model
    def _get_mode_payments(self):
        return [mode for mode in DEFAULT_MODE_PAYMENTS if mode[0] != 'credit_card']

    @api.depends('document_ref')
    def _compute_document_ref_clean(self):
        for record in self:
            if record.document_ref:
                # Usamos BeautifulSoup para quitar las etiquetas HTML
                soup = BeautifulSoup(record.document_ref, "html.parser")
                clean_text = soup.get_text(separator=" ", strip=True)
                # Opcional: limitar longitud si es campo Char
                record.document_ref_clean = clean_text[:255]
            else:
                record.document_ref_clean = False


    enable_other_account=fields.Boolean("Cuentas de Contrapartida",default=False)

    other_account_id = fields.Many2one("account.account", "Otra Cuenta Contable", required=False,
                                            domain=[])
    analytic_id = fields.Many2one("account.analytic.account", "Cuenta Analitica")

    bank_codes = fields.Char( compute='_compute_bank_codes', string="Códigos de Banco", search='_search_bank_codes')

    reembolso_id=fields.Many2one('hr.registro.reembolsos',"Reembolso",store=True,readonly=True,required=False,compute="_compute_documento_liquidacion")
    caja_chica_id = fields.Many2one('hr.registro.caja.chica', "Caja Chica",store=True,readonly=True,required=False,compute="_compute_documento_liquidacion")

    default_mode_payment = fields.Selection(DEFAULT_MODE_PAYMENTS, string="Forma de Pago", default="bank",tracking=True)
    default_mode_nomina_payment = fields.Selection(selection=_get_mode_payments, string="Forma de Pago Nomina", default="bank",
                                            tracking=True)


    macro_paid = fields.Monetary(
        string="Monto Macro Aplicado",
        compute="_compute_macro_total",
        store=True,
        readonly=True,
        tracking=True
    )

    macro_pending = fields.Monetary(
        string="Monto Macro Pendiente",
        compute="_compute_macro_total",
        store=True,
        readonly=True,
        tracking=True
    )

    tipo_partner_pago = fields.Selection(
        selection=[('local', 'Local'), ('exterior', 'Exterior')],
        string="Tipo de Pago a Proveedor",
        compute="_compute_tipo_partner_pago",
        store=True
    )

    @api.depends('partner_id','partner_id.country_id')
    @api.onchange('partner_id','partner_id.country_id')
    def _compute_tipo_partner_pago(self):
        for record in self:
            tipo_partner_pago = 'local'
            if record.type_module!='payslip':
                tipo_partner_pago = 'exterior'
                if record.partner_id.country_id.code == 'EC':
                    tipo_partner_pago = 'local'
                else:
                    employee_srch=self.env["hr.employee"].sudo().search([('partner_id','=',record.partner_id.id)])
                    if employee_srch:
                        tipo_partner_pago = 'local'
                    if not employee_srch:
                        if record.invoice_id.l10n_latam_document_type_id:
                            if record.invoice_id.l10n_latam_document_type_id.code=='03':
                                tipo_partner_pago ="local"
            record.tipo_partner_pago = tipo_partner_pago

    @api.onchange('default_mode_nomina_payment')
    def _onchange_default_mode_nomina_payment(self):
        if self.default_mode_nomina_payment:
            self.default_mode_payment = self.default_mode_nomina_payment

    @api.depends('macro_line_ids.amount','macro_line_ids.reversed','macro_line_ids.apply','macro_line_ids.bank_macro_id.state', 'amount')
    def _compute_macro_total(self):
        DEC=2
        for rec in self:
            total_pagado = 0.00
            for each_macro in rec.macro_line_ids:
                if ((each_macro.apply and each_macro.bank_macro_id.state!='cancelled')
                        and not each_macro.reversed):
                    total_pagado+=each_macro.amount
            rec.macro_paid = round(total_pagado,DEC)
            rec.macro_pending = round(rec.amount - total_pagado,DEC)

    @api.depends('invoice_id')
    def _compute_documento_liquidacion(self):
        for rec in self:
            reembolso_id,caja_chica_id=False,False
            if rec.invoice_id:
                reembolso_id=self.env["hr.registro.reembolsos"].sudo().search([('liquidation_move_id','=',rec.invoice_id.id)])
                caja_chica_id = self.env["hr.registro.caja.chica"].sudo().search([('liquidation_move_id', '=', rec.invoice_id.id)])
            rec.reembolso_id=reembolso_id and reembolso_id.id or False
            rec.caja_chica_id = caja_chica_id and caja_chica_id.id or False

    @api.depends('partner_id','partner_id.bank_ids','partner_id.bank_ids.bank_id')
    def _compute_bank_codes(self):
        for rec in self:
            if rec.partner_id:
                bank_accounts = rec.partner_id.bank_ids.mapped('bank_id.bic')
                rec.bank_codes = ",".join(bank_accounts)
            else:
                rec.bank_codes = ""

    @api.model
    def _search_bank_codes(self, operator, value):
        """
        Permite buscar por los códigos de banco asociados al partner del request.
        """
        hide_nomina=self._context.get('hide_nomina',0)
        print(self._context)
        banks = self.env['res.bank'].sudo().search([('bic', operator, value)])
        print(type(hide_nomina),hide_nomina)
        if hide_nomina==1:

            self._cr.execute("""SELECT sub.partner_id,sub.partner_id  
    FROM (
        SELECT pb.partner_id, pb.id, pb.sequence, b.bic,pb.bank_id,
               ROW_NUMBER() OVER (PARTITION BY pb.partner_id ORDER BY pb.sequence, pb.id) AS rn
        FROM res_partner_bank pb
        JOIN res_bank b ON pb.bank_id = b.id and pb.active=true 
    ) sub
    WHERE sub.bank_id in %s 
    group by sub.partner_id """,(tuple(banks.ids),))
            partner_result = self._cr.fetchall()
            partner_ids = partner_result and [*dict(partner_result)] or []
            partner_ids += [-1, -1]
            return [('partner_id', 'in', tuple(partner_ids))]
        else:
            print(banks)#aqui me sale xq tiene una segunda cuenta
            self._cr.execute("""select apr.ID, apr.ID
                    FROM hr_employee he 
                    
					inner join res_partner_bank pb on pb.id=he.bank_account_id and pb.bank_id in %s 
					inner join account_payment_request apr on apr.partner_id=he.partner_id and apr.type='hr.employee.payment'
                    WHERE pb.active = TRUE group by apr.ID, apr.ID """, (tuple(banks.ids), ))
            document_result=self._cr.fetchall()
            document_ids=document_result and [*dict(document_result)] or []
            document_ids+=[-1,-1]
            return [('id', 'in', tuple(document_ids) )]

    @api.depends('state','order_id.state','order_id.total_dif_payments_advances','invoice_line_ids.amount_residual')
    def _get_compute_amount_residual(self):
        DEC=2
        for brw_each in self:
            amount_residual=0.00
            if brw_each.state not in  ('cancelled', ):
                if  brw_each.type=='account.move':
                    amount_residual=sum(brw_each.invoice_line_ids.mapped('amount_residual'))
                    amount_residual=amount_residual*-1##correccion de signo
                if brw_each.type == 'purchase.order':
                    amount_residual=brw_each.order_id.total_dif_payments_advances
            brw_each.amount_residual=round(amount_residual,DEC)

    @api.depends('state', 'order_id.state', 'order_id.total_dif_payments_advances', 'invoice_line_ids.amount_residual')
    def _get_compute_amount_request_residual(self):
        DEC = 2
        for brw_each in self:
            amount_request_residual = 0.00
            brw_each.amount_request_residual = round(amount_request_residual, DEC)

    @api.onchange('manual_type','origin')
    def onchange_manual_type(self):
        self.type=None
        if self.origin=='manual':
            self.type=self.manual_type
            self.order_id=False
            self.enable_other_account=False
            self.other_account_id=False
            self.analytic_id=False



    @api.depends('partner_id')
    def _compute_enable_payment_bank_ids(self):
        for record in self:
            record.enable_payment_bank_ids = record.partner_id.enable_payment_bank_ids

    def _search_enable_payment_bank_ids(self, operator, value):
        # Buscamos todos los partners que tengan bancos coincidentes con el criterio
        partners = self.env['res.partner'].search([
            ('enable_payment_bank_ids', operator, value)
        ])
        return [('partner_id', 'in', partners.ids)]

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise ValidationError(_("No puedes duplicar este documento"))

    @api.onchange('date_maturity','company_id')
    def onchange_date_maturity(self):
        OBJ_CONFIG = self.env["account.configuration.payment"].sudo()
        OBJ_ORDER = self.env["purchase.order"].sudo()
        brw_conf = OBJ_CONFIG.search([
            ('company_id', '=', self.company_id.id)
        ])
        if not brw_conf:
            raise ValidationError(_("No hay configuracion de pagos para la empresa %s") % (self.company_id.name,))
        TODAY=fields.Date.context_today(self)
        if self.date_maturity:
            if self.date_maturity<TODAY:
                self.date_maturity=None
                self.date=None
                return {
                    "warning":{"title":_("Advertencia"),
                               'message':_("No puedes seleccionar una fecha de vencimiento menor o igual a la actual")
                               }
                }
            date = OBJ_ORDER.obtener_fecha_proximo_dia(TODAY, brw_conf.day_id.value)
            self.date=date
            return
        self.date=None


    _rec_name = "name"
    _check_company_auto = True

    @api.onchange('amount','macro_line_ids', 'macro_line_ids.reversed', 'macro_line_ids.amount', 'macro_line_ids.payment_id.state', 'macro_line_ids.payment_id', 'macro_line_ids.payment_id.reversed_payment_id')
    @api.depends('amount','macro_line_ids', 'macro_line_ids.reversed',  'macro_line_ids.amount', 'macro_line_ids.payment_id.state', 'macro_line_ids.payment_id', 'macro_line_ids.payment_id.reversed_payment_id')
    def _compute_total(self):
        DEC=2
        for brw_each in self:
            paid,posted_dates= 0.00, []
            if brw_each.state in ('confirmed','locked','done'):
                for brw_line in brw_each.macro_line_ids:
                    if brw_line.payment_id.state=='posted':
                        if not brw_line.reversed and not brw_line.payment_id.reversed_payment_id:
                            paid += brw_line.amount
                            posted_dates.append(brw_line.payment_id.date)
            date_payment = posted_dates and max(posted_dates) or None
            brw_each.paid =round( paid,DEC)
            brw_each.pending =round( brw_each.amount- paid,DEC)
            brw_each.date_payment=date_payment
            brw_each.test_states()

    def test_states(self):
        DEC=2
        for brw_each in self:
            if brw_each.state in ('confirmed','done'):
                if round(brw_each.pending,DEC)!=0.00:
                    brw_each.state='confirmed'
                else:
                    brw_each.state = 'done'

    def unlink(self):
        for brw_each in self:
            if self._context.get("validate_unlink", True):
                if brw_each.state != 'draft':
                    raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
                if brw_each.type!='request':
                    raise ValidationError(_("Este tipo de registros no puede ser eliminado solo anulado"))
        return super(AccountPaymentRequestPurchase, self).unlink()


    @api.depends('type_document','type','order_id','quota','amount','invoice_id','invoice_line_id','payment_employee_id','liquidation_employee_id')
    @api.onchange('type_document','type','order_id','quota','amount','invoice_id','invoice_line_id','payment_employee_id','liquidation_employee_id')
    def _compute_full_name(self):
        DEC=2
        for brw_each in self:
            name=None
            if brw_each.type=='purchase.order':
                name="%s cuota %s por %s" % (brw_each.order_id.name,brw_each.quota,f"{round(brw_each.amount,DEC):.2f}" )
                if brw_each.type_document=="document":
                    name = "%s por %s" % (
                    brw_each.order_id.name, f"{round(brw_each.amount, DEC):.2f}")
            if brw_each.type == 'account.move':
                name = "%s cuota del %s por %s" % (
                brw_each.invoice_id.name, brw_each.invoice_line_id.date_maturity, f"{round(brw_each.invoice_line_id.credit, DEC):.2f}")
                if brw_each.type_document=="document":
                    name = "%s por %s" % (
                    brw_each.invoice_id.name, f"{round(brw_each.amount, DEC):.2f}")
            if brw_each.type == 'request':
                name= brw_each.description_motive
            if brw_each.type == 'hr.employee.payment':
                if brw_each.payment_employee_id:
                    name= brw_each.payment_employee_id.name
            if brw_each.type == 'hr.employee.liquidation':
                if brw_each.liquidation_employee_id:
                    name= brw_each.liquidation_employee_id.name
            brw_each.name=name

    @api.onchange('description_motive','type','enable_other_account')
    def onchange_description_motive(self):
        if self.type=='request':
            self.document_ref=self.description_motive

    @api.depends('date', 'date_maturity')
    @api.onchange('date', 'date_maturity')
    def _compute_adjust(self):
        for brw_each in self:
            brw_each.adjust = (brw_each.date!=brw_each.date_maturity)

    @api.onchange('amount')
    def _onchange_amount(self):
        if self.amount <= 0:
            return {
                'warning': {
                    'title': "Monto inválido",
                    'message': "El monto debe ser mayor a 0.",
                }
            }

    @api.constrains('amount')
    def _check_amount_positive(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError("El monto debe ser mayor a 0.")

    def action_draft(self):
        for brw_each in self:
            brw_each.validate_payment_banks()
            brw_each.write({"state":"draft"})
        return True

    def action_locked(self):
        for brw_each in self:
            #   brw_each.validate_payment_banks()
            if brw_each.state!='confirmed' or brw_each.paid<=0.00 :
                raise ValidationError(_("Solo puedes confirmar un documento en estado confirmado y con valores pagados mayor a 0.00.Verificar %s - %s") % (brw_each.id,brw_each.name,))
            brw_each.write({"state":"locked"})
        return True

    def action_confirmed(self):
        DEC=2
        for brw_each in self:
            brw_each.validate_payment_banks()
            # if brw_each.type!='purchase.order':#account_move
            #     user=self.env.user
            #     if not (user.has_group("gps_bancos.group_confimar_sol_pagos") or user.has_group("gps_bancos.group_pagar_sol_pagos") or user.has_group("gps_bancos.group_admin_sol_pagos")):
            #         raise ValidationError(_("No tienes acceso para confirmar un solicitud que no pertenezca a una orden de compra"))
            if brw_each.state!='draft':
                raise ValidationError(_("Solo puedes confirmar un documento en estado preliminar.Verificar %s - %s") % (brw_each.id,brw_each.name,))
            #if brw_each.origin=="manual":
            if brw_each.amount<=0.00:
                raise ValidationError(_("El valor de la solicitud debe ser mayor a 0.00"))
            ###########
            if brw_each.type == 'account.move':
                lines=brw_each.invoice_line_ids
                invoices=".".join(lines.mapped('move_id.name'))
                total = round(abs(sum(lines.mapped('amount_residual'))),DEC)
                if round(brw_each.amount,DEC) > round(total,DEC):
                    raise ValidationError(
                        _("El valor de la solicitud de las Facturas %s NO debe ser mayor al valor pendiente %s de %s ") % (invoices,brw_each.amount,total))

            if brw_each.type == 'purchase.order':
                if brw_each.company_id != brw_each.order_id.company_id:
                    raise ValidationError(
                        _("Solo puedes confirmar un documento si la orden de compra es de la misma empresa seleccionada.Verificar %s - %s") % (
                        brw_each.id, brw_each.name,))
                if round(brw_each.amount,DEC) > round(brw_each.order_id.total_dif_payments_advances,DEC):
                    raise ValidationError(
                        _("El valor de la solicitud de la OC %s NO debe ser mayor al valor pendiente %s de %s") % (brw_each.order_id.name,brw_each.amount,brw_each.order_id.total_dif_payments_advances) )
            ###########################################
            vals={"state":"confirmed"}
            if brw_each.origin=="manual":
                vals["checked"]=True
                if brw_each.enable_other_account:
                    if not brw_each.payment_line_ids:
                        raise ValidationError(_("Debes definir al menos una cuenta "))
                    if round(brw_each.other_amount_diference,DEC)!=0.00:
                        raise ValidationError(_("Los totales de Debe, Haber y Pago no coinciden. Ajusta las líneas hasta que sean iguales."))
            brw_each.write(vals)
            brw_each.send_mail_not_partner_bank()
        return True

    def action_lock(self):
        for brw_each in self:
            if brw_each.state != 'confirmed':
                raise ValidationError(_("Solo puedes bloquear un documento en estado confirmado.Verificar %s - %s") % (
                brw_each.id, brw_each.name,))
            brw_each.write({"state":"locked"})
        return True

    def action_done(self):
        for brw_each in self:
            if brw_each.state != 'confirmed':
                raise ValidationError(_("Solo puedes procesar un documento en estado confirmado.Verificar %s - %s") % (
                brw_each.id, brw_each.name,))
            if not brw_each.checked:
                raise ValidationError(
                    _("No puedes pagar solicitudes no verificadas .ver solicitud # %s") % (brw_each.id,))
            brw_each.write({"state":"done"})
        return True

    def action_cancelled(self):
        for brw_each in self:
            if brw_each.state=='cancelled':
                continue
            brw_each.validate_payment_banks()
            if brw_each.state not in ('confirmed','draft'):
                raise ValidationError(_("Solo puedes anular un documento en estado confirmado o preliminar.Verificar %s - %s") % (
                brw_each.id, brw_each.name,))
            brw_each.write({"state":"cancelled"})
        return True

    def validate_payment_banks(self):
        for brw_each in self:
            srch=self.env["account.payment.bank.macro.line"].sudo().search([('request_id','=',brw_each.id),
                                                                            ('bank_macro_id.state','!=','cancelled')
                                                                            ])
            if srch:
                dscr_names=",".join([str(id) for id in srch.mapped('request_id').mapped('id')])
                dscr_payments = ",".join(srch.mapped('bank_macro_id').mapped('name'))
                raise ValidationError(_("Las solicitudes %s estan siendo utilizadas en los siguientes pagos a proveedores %s") % (dscr_names,dscr_payments))
        return True

    def confirm_multi_payments(self):
        for brw_each in self:
            if brw_each.state not in ('draft',):
                raise ValidationError(_("No puedes seleccionar solicitudes que no esten en preliminar.Revisar %s") % (brw_each.name,))
            brw_each.action_confirmed()
        return True

    def cancel_multi_payments(self):
        for brw_each in self:
            if brw_each.state not in ('draft','confirmed'):
                raise ValidationError(_("No puedes seleccionar solicitudes que no esten en preliminar o confirmado.Revisar %s") % (brw_each.name,))
            brw_each.action_cancelled()
        return True

    def get_multi_payments(self):
        OBJ_MODEL_DATA = self.env["ir.model.data"].sudo()
        form_id = OBJ_MODEL_DATA.resolve_view_ref("gps_bancos", "account_payment_request_wizard_view_form")
        lst_ids=[]
        last_company=self.env["res.company"]
        last_payslip_type=None
        all_payslip_types=[]
        last_default_mode_payment=None
        last_tipo_partner_pago=None
        for brw_each in self:
            if brw_each.state not in ('confirmed',):
                raise ValidationError(_("No puedes seleccionar solicitudes no confirmadas.Revisar %s") % (brw_each.name,))
            macro_pending=brw_each.macro_pending
            bank_macro_ids=brw_each.macro_line_ids.filtered(lambda x: (x.apply and x.bank_macro_id.state!='cancelled') and not x.reversed).mapped('bank_macro_id')
            bank_macro_ref = [f"({rec.id}) {rec.name}" for rec in bank_macro_ids]
            bank_macro_ref_str = ', '.join(bank_macro_ref)
            if macro_pending<=0.00:
                raise ValidationError(
                    _("Las solicitudes ya no tienen valores por aplicar entre pagos a proveedores %s.Revisar %s") % (bank_macro_ref_str,brw_each.name,))
            if last_default_mode_payment:
                if last_default_mode_payment != brw_each.default_mode_payment:
                    raise ValidationError(_("Solo puedes procesar solicitudes de una misma forma de pago"))
            if brw_each.type_module != 'payslip':
                if last_tipo_partner_pago:
                    if last_tipo_partner_pago != brw_each.tipo_partner_pago:
                        raise ValidationError(_("Solo puedes procesar una único tipo de pago 'local' o 'exterior' "))
            if last_company:
                if last_company!=brw_each.company_id:
                    raise ValidationError(_("Solo puedes procesar solicitudes de una sola empresa"))
            if brw_each.type=='purchase.order':
                if not brw_each.order_id:
                    raise ValidationError(_("La solicitud %s de tipo orden de compra no tiene definido un documento") % (brw_each.id,))
                if brw_each.order_id.state not in ('done','purchase'):
                    raise ValidationError(
                        _("La solicitud %s con %s debe estar en estado Orden de Compra o Bloqueado") % (brw_each.id,brw_each.order_id.name))
            if brw_each.type == 'account.move':
                if not brw_each.invoice_id:
                    raise ValidationError(
                        _("La solicitud %s de tipo factura/asiento contable no tiene definido un documento") % (brw_each.id,))
                if brw_each.invoice_id.state not in ('posted',):
                    raise ValidationError(
                        _("La solicitud %s con %s debe estar en estado publicado") % (brw_each.id,brw_each.invoice_id.name))
            if not brw_each.checked:
                raise ValidationError(_("No puedes pagar solicitudes no verificadas .ver solicitud # %s") % (brw_each.id,) )
            if brw_each.partner_id:
                brw_each.partner_id.validate_partner_for_transaction(company_id=brw_each.company_id.id)
            if brw_each.type_module=='payslip':
                if brw_each.payment_employee_id:
                    if last_payslip_type is None:
                        last_payslip_type =brw_each.payment_employee_id.filter_iess
                    if brw_each.payment_employee_id.filter_iess!=last_payslip_type:
                        raise ValidationError(_("No puedes mezclar documentos de nomina de afiliados y no afiliados"))
                    all_payslip_types = list(set(all_payslip_types + brw_each.payment_employee_id.get_type_documents()))
                    last_payslip_type = brw_each.payment_employee_id.filter_iess
                if brw_each.liquidation_employee_id:
                    all_payslip_types = list(
                        set(all_payslip_types + ["liquidation"]))
            last_company = brw_each.company_id
            last_default_mode_payment= brw_each.default_mode_payment
            last_tipo_partner_pago=brw_each.tipo_partner_pago
            lst_ids.append(brw_each.id)
        if len(all_payslip_types)>1:
            dct_payslip={
                  "liquidation": "Liquidación de Haberes",
                    "payslip": "Rol de Pago",
                    "batch": "Lote",
                    "batch_automatic": "Lote Automático",
                    "discount": "Préstamo"
            }
            tipos = [dct_payslip.get(tp, tp) for tp in all_payslip_types]
            tipos_str = ", ".join(tipos)
            raise ValidationError(_(
                "No puedes mezclar diferentes tipos de documentos de nómina en un pago en lote: %s"
            ) % tipos_str)
        context = {"active_id":lst_ids[0],
                   "active_ids":lst_ids,
                   "active_model":self._name,
                   'hide_bank_account':last_default_mode_payment!='bank',
                   'default_tipo_partner_pago':last_tipo_partner_pago
                    }
        v= {
                'name': "GENERACION DE PAGOS MULTIPLES",
                'view_mode': 'form',
                'res_model': "account.payment.request.wizard",
                'views': [(form_id, 'form')],
                "context": context,
                'target':'new',
                'type': 'ir.actions.act_window'
        }
        return v

    def get_document_payments(self):
        OBJ_MODEL_DATA = self.env["ir.model.data"].sudo()
        lst_ids = []
        last_company = self.env["res.company"]
        last_type=None
        last_tipo_partner_pago=None
        for brw_each in self:
            if last_company:
                if last_company != brw_each.company_id:
                    raise ValidationError(_("Solo puedes procesar solicitudes de una sola empresa"))
            if last_tipo_partner_pago:
                if last_tipo_partner_pago != brw_each.tipo_partner_pago:
                    raise ValidationError(_("Solo puedes procesar una único tipo de pago 'local' o 'exterior' "))
            if last_type:
                if last_type != brw_each.type:
                    raise ValidationError(_("Solo puedes procesar tipos de una sola empresa"))
            if brw_each.type == 'purchase.order':
                if not brw_each.order_id:
                    raise ValidationError(
                        _("La solicitud %s de tipo orden de compra no tiene definido un documento") % (brw_each.id,))
                if brw_each.order_id.state not in ('done', 'purchase'):
                    raise ValidationError(
                        _("La solicitud %s con %s debe estar en estado Orden de Compra o Bloqueado") % (
                        brw_each.id, brw_each.order_id.name))
                lst_ids.append(brw_each.order_id.id)
            if brw_each.type == 'account.move':
                if not brw_each.invoice_id:
                    raise ValidationError(
                        _("La solicitud %s de tipo factura/asiento contable no tiene definido un documento") % (
                        brw_each.id,))
                if brw_each.invoice_id.state not in ('posted',):
                    raise ValidationError(
                        _("La solicitud %s con %s debe estar en estado publicado") % (
                        brw_each.id, brw_each.invoice_id.name))
                lst_ids.append(brw_each.invoice_id.id)
            last_company = brw_each.company_id
            last_type = brw_each.type
            last_tipo_partner_pago= brw_each.tipo_partner_pago
        context = {"active_id": lst_ids[0],
                   "active_ids": lst_ids,
                   "active_model": self._name
                   }
        lst_ids+=[-1,-1]
        if last_type=="purchase.order":
            tree_id=self.env.ref('purchase.purchase_order_view_tree').id
            form_id = self.env.ref('purchase.purchase_order_form').id
            v = {
                'name': "OC",
                'view_mode': 'tree',
                'res_model': "purchase.order",
                'views': [(tree_id, 'tree'),(form_id, 'form')],
                "context": context,
                'type': 'ir.actions.act_window',
                'domain':[('id','in',lst_ids)]
            }
            return v
        if last_type == "account.move":
            tree_id = self.env.ref('account.view_in_invoice_bill_tree').id
            form_id = self.env.ref('account.view_move_form').id
            v = {
                'name': "ASIENTOS DE FACTURAS",
                'view_mode': 'tree',
                'res_model': "account.move",
                'views': [(tree_id, 'tree'),(form_id, 'form')],
                "context": context,
                'type': 'ir.actions.act_window',
                'domain':[('id','in',lst_ids)]
            }
            return v
        return True

    @api.onchange('order_id', 'origin', 'type')
    def onchange_order_id(self):
        brw_each = self
        if brw_each.origin == 'manual':
            if brw_each.type == 'purchase.order':
                brw_each.partner_id = False
                brw_each.vat = None
                brw_each.payment_term_id = False
                brw_each.quota = 1
                brw_each.description_motive=""
                brw_each.amount_original=0.00
                if brw_each.order_id:
                    brw_each.partner_id = brw_each.order_id.partner_id
                    brw_each.vat = brw_each.order_id.partner_id.vat
                    brw_each.payment_term_id = brw_each.order_id.payment_term_id
                    brw_each.quota = 99999
                    brw_each.amount = brw_each.order_id.total_dif_payments_advances
                    brw_each.amount_original= brw_each.order_id.total_dif_payments_advances
                    brw_each.description_motive = "ANTICIPO DE %s" % (brw_each.name,)

    def get_mail_bank_alert_not(self):
        self.ensure_one()
        return self.company_id.get_mail_bank_alert_not()

    def send_mail_not_partner_bank(self):
        template = self.env.ref('gps_bancos.email_template_payment_request', raise_if_not_found=False)
        for brw_each in self:
            if brw_each.origin == 'manual':
                if brw_each.state in ('confirmed',):
                    if not (self.env.user.has_group('gps_bancos.group_pagar_sol_pagos') and not self.env.user.has_group('gps_bancos.group_admin_sol_pagos')):
                        template.send_mail(brw_each.id, force_send=True)
        return True

    def get_request_action_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_id=self.env.ref('gps_bancos.account_payment_request_view_action').id
        company_id=self.company_id.id
        menu_id=self.env.ref('gps_bancos.account_payment_request_view_menu').id
        active_id=self.id
        return f"{base_url}/web#id={active_id}&action={action_id}&model=account.payment.request&view_type=form&cids={company_id}&menu_id={menu_id}"

    def validate_checked(self,checked):
        for brw_each in self:
            msg_verificado=checked and "VERIFICADO" or "NO VERIFICADO"
            if brw_each.state not in ('confirmed',):
                raise ValidationError(_("Solo documentos confirmados pueden ser marcados como %s") % (msg_verificado,))
        return True

    other_debit_total = fields.Monetary("Debito", store=True, compute="get_payment_line_amount_real_onchange")
    other_credit_total = fields.Monetary("Crédito", store=True, compute="get_payment_line_amount_real_onchange")

    other_amount_total = fields.Monetary(string="Total", store=True, compute="get_payment_line_amount_real_onchange")
    other_amount_diference = fields.Monetary(string="Diferencia", store=True,
                                             compute="get_payment_line_amount_real_onchange")

    @api.depends('enable_other_account', 'payment_line_ids', 'amount',
                 'payment_line_ids.account_id', 'payment_line_ids.partner_id',
                 'payment_line_ids.debit', 'payment_line_ids.credit')
    def get_payment_line_amount_real_onchange(self):
        DEC = 2
        for record in self:
            if record.enable_other_account:
                amount_total = record.amount
                change_amount = 0.00
                other_debit_total = 0.00
                other_credit_total = 0.00
                for line in record.payment_line_ids:
                    amount_total += line.credit
                    change_amount += line.debit
                    other_debit_total += line.debit
                    other_credit_total += line.credit
                other_credit_total += record.amount
                record.other_debit_total = round(other_debit_total, DEC)
                record.other_credit_total = round(other_credit_total, DEC)
                record.other_amount_total = round(amount_total, DEC)
                record.other_amount_diference = round(amount_total - change_amount, DEC)
            else:
                record.other_amount_total = 0.00
                record.other_amount_diference = 0.00
                record.other_debit_total = 0.00
                record.other_credit_total = 0.00

    @api.onchange('enable_other_account', 'payment_line_ids', 'amount',
                 'payment_line_ids.account_id', 'payment_line_ids.partner_id', 'payment_line_ids.debit',
                 'payment_line_ids.credit')
    def onchange_payment_line_amount_real_onchange(self):
        DEC = 2
        record = self
        if record.enable_other_account:
            amount_total = record.amount
            change_amount = 0.00
            other_debit_total = 0.00
            other_credit_total = 0.00
            for line in record.payment_line_ids:
                amount_total += line.credit
                change_amount += line.debit
                other_debit_total += line.debit
                other_credit_total += line.credit
            other_credit_total += record.amount
            record.other_debit_total = round(other_debit_total, DEC)
            record.other_credit_total = round(other_credit_total, DEC)
            record.other_amount_total = round(amount_total, DEC)
            record.other_amount_diference = round(amount_total - change_amount, DEC)
        else:
            record.other_amount_total = 0.00
            record.other_amount_diference = 0.00
            record.other_debit_total = 0.00
            record.other_credit_total = 0.00
