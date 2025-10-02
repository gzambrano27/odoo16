# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

class AccountPaymentBankMacroSummary(models.Model):
    _name = 'account.payment.bank.macro.summary'
    _description = "Resumen de Pagos con Macros Bancarias"

    def _get_compute_dscr(self):
        for brw_each in self:
            brw_each.name=str(brw_each._origin.id)

    name=fields.Char("#",compute="_get_compute_dscr")
    bank_macro_id=fields.Many2one("account.payment.bank.macro","Macro",ondelete="cascade")
    type_module=fields.Selection(related="bank_macro_id.type_module",store=False,readonly=True)


    partner_id = fields.Many2one("res.partner","Proveedor",required=True)
    amount = fields.Monetary("Monto", required=True, digits=(16, 2))

    company_id = fields.Many2one("res.company", string="Compañia", related="bank_macro_id.company_id", store=True,
                                 readonly=True)
    currency_id = fields.Many2one("res.currency", "Moneda", related="company_id.currency_id", store=False,
                                  readonly=True)

    bank_account_id = fields.Many2one("res.partner.bank", "Cuenta de Banco", required=False)

    bank_id = fields.Many2one("res.bank", "Banco", required=False)
    bank_acc_number = fields.Char("# Cuenta", required=False)
    bank_tipo_cuenta = fields.Selection([('Corriente', 'Corriente'),
                                         ('Ahorro', 'Ahorro'),
                                         ('Tarjeta', 'Tarjeta'),
                                         ('Virtual', 'Virtual')
                                         ], string="Tipo de Cuenta", required=False)

    tercero = fields.Boolean("Tercero", default=False)
    identificacion_tercero = fields.Char("# Identificacion Tercero")
    nombre_tercero = fields.Char("Nombre de Cuenta Tercero")
    l10n_latam_identification_tercero_id = fields.Many2one("l10n_latam.identification.type",
                                                           "Tipo de Identificacion Tercero")

    line_ids=fields.Many2many("account.payment.bank.macro.line","bank_macro_line_rel","summary_id","line_id","Detalle")
    ref = fields.Char("# Referencia")
    comments = fields.Text("Glosa")

    number_mail_requests=fields.Integer('# Envios',default=0)

    #####
    reversed_motive_id = fields.Many2one('account.payment.request.type', 'Motivo de Reverso',
                                domain=[('type', '=', 'anulacion')])
    reversed_comments = fields.Text("Comentarios  de Reverso")
    reversed_date = fields.Date('Fecha de Reverso')
    reversed_ref = fields.Char('Referencia de Reverso')
    reversed=fields.Boolean('Fue reversado')


    is_intercompany=fields.Boolean("Es Multicompañia",compute="compute_is_intercompany",default=False,store=True,readonly=True)
    accredited_other_company = fields.Boolean(string="Acreditado en Compañia",default=False)
    intercompany_payment_id=fields.Many2one('account.payment','Pago Multicompañia')
    intercompany_payment_ref = fields.Char('Ref. Pago Multicompañia')

    default_mode_payment = fields.Selection(related="bank_macro_id.default_mode_payment", store=False, readonly=True)

    bank_intermediary_id = fields.Many2one(
        "res.bank",
        string="Banco Intermediario",
        domain=lambda self: self._domain_bank_intermediary_id(),
    )

    def _domain_bank_intermediary_id(self):
        """Excluye bancos de Ecuador (base.ec)"""
        ec_country = self.env.ref("base.ec", raise_if_not_found=False)
        if ec_country:
            return [("country", "!=", ec_country.id)]
        return [('id','=',-1)]  # Si no encuentra Ecuador, no aplica filtro

    @api.depends('company_id','partner_id')
    def compute_is_intercompany(self):
        for brw_each in self:
            partner = brw_each.partner_id.sudo()
            company_from_id = brw_each.company_id.sudo().id
            # SQL: obtener company_id del partner si es compañía
            self._cr.execute("""
                                                SELECT id
                                                FROM res_company
                                                WHERE partner_id = %s  
                                                LIMIT 1
                                            """, (partner.id,))
            result = self._cr.fetchone()
            company_to_id = result[0] if result else None
            is_intercompany=False
            if (
                    partner and partner.is_company
                    and company_to_id
                    and company_from_id != company_to_id
            ):
                is_intercompany=True
            brw_each.is_intercompany=is_intercompany

    _order="partner_id,bank_account_id asc"

    def write(self, vals):
        value= super(AccountPaymentBankMacroSummary,self).write(vals)
        for brw_each in self:
            if brw_each.bank_macro_id.state in ('done','confirmed'):
                for brw_line in brw_each.line_ids:
                    if brw_line.request_id.payment_employee_id:
                        brw_line.request_id.payment_employee_id._write({"bank_reference": brw_each.ref})
                    brw_line.write({"ref":brw_each.ref})
                    if brw_line.payment_id:
                        brw_line.payment_id.write({"bank_reference":brw_each.ref})

        return value

    def send_mail(self):
        OBJ_MAIL = self.env["bank.mail.message"]
        for brw_each in self:
            if brw_each.bank_macro_id.state in ("done", ):
                internal_type = self._context.get("internal_type", "process")
                brw_mail = OBJ_MAIL.create({
                    "internal_type": internal_type,
                    "type": "payment_bank",
                    "name": "%s,%s" % (brw_each._name, brw_each.id),
                    "internal_id": brw_each.id,
                    "model_name": brw_each._name,
                    "description": "PAGO %s" % (brw_each.company_id.name,),
                    "email": brw_each.bank_account_id.partner_email and brw_each.bank_account_id.partner_email.replace(';',',') or '',
                    "partner_id": brw_each.partner_id.id,
                    "company_id": brw_each.company_id.id,
                    "state": "draft",
                    "template_id": self.env.ref('gps_bancos.mail_template_pago_banco').id,
                    "report_name_ref": None#"hr_payroll.action_report_payslip"
                })
                brw_each.number_mail_requests=brw_each.number_mail_requests+1
                if internal_type == "process":
                    brw_mail.send_mail()
        return True

    def get_hidden_bank_acc_number(self):
        number = self.ensure_one()
        acc_number = number.bank_acc_number  # Asumiendo que el número está en un campo llamado bank_acc_number

        if not acc_number or len(acc_number) < 4:
            return acc_number  # No se oculta si es demasiado corto

        first = acc_number[0]
        last_two = acc_number[-2:]
        hidden = '*' * (len(acc_number) - 3)  # Restamos 3 (1 + 2)

        return f'{first}{hidden}{last_two}'

    def get_payment_details(self):
        brw_each =self
        invoices_values={}
        for brw_macro_line in brw_each.line_ids:
            invoice=brw_macro_line.mapped('request_id').mapped('invoice_id')#deberia ser 1
            if invoice:
                if not invoices_values.get(invoice,False):
                    invoices_values[invoice]={
                        "total":0.00,
                        "doc":invoice,
                        "withholds":invoice.get_withholds()
                    }
                invoices_values[invoice]["total"]=invoices_values[invoice]["total"]+brw_macro_line.amount
        #print(invoices_values)
        return invoices_values

    date_payment = fields.Date(
        string="Fecha de Pago",
        compute="_compute_date_payment",
        store=True
    )

    @api.depends('bank_macro_id.date_payment')
    def _compute_date_payment(self):
        for record in self:
            record.date_payment = record.bank_macro_id.date_payment if record.bank_macro_id else False

    detalle_pago_html = fields.Html(string="Detalle del Pago", compute="_compute_detalle_pago_html",store=False,readonly=True)

    invoices_ids=fields.Many2many("account.move",compute="_compute_info",store=False,readonly=True,string="Facturas")
    order_ids = fields.Many2many("purchase.order", compute="_compute_info", store=False, readonly=True,string= "Ordenes de Compra")
    payment_ids = fields.Many2many("account.payment", compute="_compute_info", store=False, readonly=True,
                                 string="Pagos")

    contratista = fields.Boolean(
        string="Contratista",
        compute="_compute_contratista",
        store=True,default=False
    )

    @api.depends('partner_id','partner_id.category_id')
    def _compute_contratista(self):
        for brw_each in self:
            contratista=False
            if brw_each.partner_id.category_id:
                if self.env.ref("gps_bancos.rp_contratista") in brw_each.partner_id.category_id:
                    contratista = True
            brw_each.contratista=contratista

    @api.depends('line_ids')
    def _compute_info(self):
        for brw_each in self:
            brw_each.invoices_ids= brw_each.line_ids.mapped('request_id.invoice_id')
            brw_each.order_ids = brw_each.line_ids.mapped('request_id.order_id')
            brw_each.payment_ids = brw_each.line_ids.mapped('payment_id')

    @api.depends('bank_macro_id.date_payment','bank_macro_id')
    def _compute_detalle_pago_html(self):
        DEC=2
        for brw_each in self:
            detalle_pago_html=""
            if brw_each.bank_macro_id.state=='done':
                facturas_detalles=""
                oc_detalles = ""
                otros_detalles = f""""""
                payment_ids=brw_each.payment_ids
                for invoice in brw_each.invoices_ids:
                    withhold_amount=0.00
                    withholds=invoice.get_withholds()
                    if withholds:
                        withhold_amount=sum(withholds.mapped('amount_total_signed'))
                    #################################################################
                    facturas_pagos_detalles = ""
                    conciliaciones = invoice.line_ids.mapped('matched_debit_ids')

                    if conciliaciones:
                        facturas_pagos_detalles += """
                        <tr><td colspan="2" align='right'>
                            <table style="width:95%; font-size: 12px; margin-top:10px; background-color:#f9f9f9; border:1px solid #ddd;">
                                <tr>
                                    <th style="text-align:left;">Fecha</th>
                                    <th style="text-align:left;">Descripción</th>
                                    <th style="text-align:right;">Monto aplicado</th>
                                </tr>
                        """
                        for reconc in conciliaciones:
                            line = reconc.debit_move_id#if reconc.debit_move_id.move_id != invoice else reconc.credit_move_id
                            move = line.move_id
                            if move in withholds:
                                continue
                            fecha = move.date.strftime('%Y-%m-%d')
                            payment,descripcion = line.move_id.get_payment_dscr_summary()
                            monto = reconc.amount
                            style=(payment and (payment in payment_ids)) and """ style="color: red;" """ or ""
                            facturas_pagos_detalles += f"""
                                <tr {style}>
                                    <td>{fecha}</td>
                                    <td>{descripcion}</td>
                                    <td align="right">$ {monto:,.2f}</td>
                                </tr>
                            """
                        facturas_pagos_detalles += "</table></td></tr>"
                    ################################################################
                    retenciones_names=','.join(name.replace('Ret', '') for name in withholds.mapped('name'))
                    facturas_detalles += f"""
                      <tr><td>  <div style="border:1px solid #ccc; padding:10px; margin-bottom:15px; border-radius:6px;">
                            <p style="font-weight:bold;">Factura: {invoice.l10n_latam_document_number if invoice.l10n_latam_document_number else invoice.name}</p>
                            <table style="width:100%; font-size: 13px;">
                                <tr><td>Base imponible</td><td align='right'>$ {invoice.amount_untaxed:,.2f}</td></tr>
                                <tr><td>IVA 15%</td><td align='right'>$ {invoice.amount_tax:,.2f}</td></tr>
                                <tr><td colspan="2"><hr style="border: none; border-top: 1px solid #aaa;"/></td></tr>
                                <tr><td><strong>Total</strong></td><td align='right'><strong>$ {invoice.amount_total:,.2f}</strong></td></tr>
                                <tr><td>Retenciones {retenciones_names}</td><td align='right'>- $ {withhold_amount:,.2f}</td></tr>
                                <tr><td colspan="2"><hr style="border: none; border-top: 1px solid #aaa;"/></td></tr>
                                <tr><td><strong></strong></td><td align='right'><strong>$ {round(invoice.amount_total - withhold_amount, DEC):,.2f}</strong></td></tr>
                                {facturas_pagos_detalles}
                            </table>
                        </div></td> </tr>"""
                for order in brw_each.order_ids:
                    oc_pagos_detalles=""
                    if order.purchase_payment_line_ids:
                        oc_pagos_detalles += """
                                                <tr><td colspan="2" align='right'>
                                                    <table style="width:95%; font-size: 12px; margin-top:10px; background-color:#f9f9f9; border:1px solid #ddd;">
                                                        <tr>
                                                            <th style="text-align:left;">Fecha</th>
                                                            <th style="text-align:left;">Descripción</th>
                                                            <th style="text-align:right;">Monto aplicado</th>
                                                        </tr>
                                                """
                        for payment_line_order in order.purchase_payment_line_ids:
                            fecha = payment_line_order.payment_id.date.strftime('%Y-%m-%d')
                            payment,descripcion = payment_line_order.payment_id.move_id.get_payment_dscr_summary()
                            monto = payment_line_order.amount
                            style = (payment and (payment in payment_ids)) and """ style="color: red;" """ or ""

                            oc_pagos_detalles += f"""
                                                            <tr {style}>
                                                                <td>{fecha}</td>
                                                                <td>{descripcion}</td>
                                                                <td align="right">$ {monto:,.2f}</td>
                                                            </tr>
                                                        """
                    oc_detalles += f"""
                                                              <tr><td>  <div style="border:1px solid #ccc; padding:10px; margin-bottom:15px; border-radius:6px;">
                                                                    <p style="font-weight:bold;">OC: {order.name if order.name else order.name}</p>
                                                                    <table style="width:100%; font-size: 13px;">
                                                                        <tr><td>Base imponible</td><td align='right'>$ {order.amount_untaxed:,.2f}</td></tr>
                                                                        <tr><td>IVA 15%</td><td align='right'>$ {order.amount_tax:,.2f}</td></tr>
                                                                        <tr><td colspan="2"><hr style="border: none; border-top: 1px solid #aaa;"/></td></tr>
                                                                        <tr><td><strong>Total</strong></td><td align='right'><strong>$ {order.amount_total:,.2f}</strong></td></tr>
                                                                        {oc_pagos_detalles}
                                                                    </table>
                                                                </div></td> </tr>"""
                if not brw_each.invoices_ids and not brw_each.order_ids:
                    otros_detalles+=f"""<tr><td colspan="2" align='right'>{brw_each.comments or ''} </td></tr>"""

                detalle_pago_html= f"""
                <table class="table table-sm" >
                    <tr><td>  <div style="border:1px solid #ccc; padding:10px; margin-bottom:15px; border-radius:6px;">
                            <p style="font-weight:bold;">Fecha Pago: {brw_each.date_payment.strftime('%Y-%m-%d') if brw_each.date_payment else ""}</p>
                            <p style="font-weight:bold;">Total Pago: $ {brw_each.amount:,.2f}</p>
                            
                        </td> </tr>   
                    {facturas_detalles}   
                    {oc_detalles}    
                    {otros_detalles}           
                </table>
                """
            brw_each.detalle_pago_html=detalle_pago_html

    def _create_payment_multicompany(self,brw_account,brw_analytic):
        for brw_each in self:
            if not brw_each.is_intercompany:
                raise ValidationError(_("Solo se puede acreditar en compañía para registros multicompañía."))

            if brw_each.accredited_other_company:
                raise ValidationError(_("Ya ha sido acreditado en la otra compañía."))

            # Buscar la compañía destino (por el partner_id)
            company_to = self.env['res.company'].sudo().search([('partner_id', '=', brw_each.partner_id.id)], limit=1)
            if not company_to:
                raise ValidationError(_("No se encontró la compañía asociada al proveedor."))

            if brw_account.company_id!=company_to:
                raise ValidationError(_("La cuenta seleccionada no pertenece a la multicompañía destino!!"))

            journal_ids=self.env['account.journal'].sudo().with_company(company_to).search([
                    ('type', '=', 'bank'),
                    ('company_id', '=', company_to.id),
                    ('bank_account_id','=',brw_each.bank_account_id.id)
                ], limit=1)
            if not journal_ids:
                raise ValidationError(_("No hay diario en %s encontrado para cuenta destino %s") % (company_to.name,brw_each.bank_account_id.full_name,))
            if len(journal_ids)>1:
                raise ValidationError(_("No hay diario en %s encontrado para cuenta destino %s") % (company_to.name, brw_each.bank_account_id.full_name,))

            # Crear el pago en la otra compañía

            OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
            payment_date = brw_each.date_payment
            brw_period, brw_period_line = OBJ_PERIOD_LINE.get_periods(payment_date, company_to,
                                                                      for_account_payment=True)
            ref=f"ACREDITACION {brw_each.bank_macro_id.name} , {brw_each.ref or ''}"
            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': brw_each.company_id.partner_id.id,
                'amount': brw_each.amount,
                'company_id': company_to.id,
                'currency_id': brw_each.currency_id.id,
                'date': brw_each.date_payment,
                'ref': ref,
                'bank_reference': brw_each.ref or '',
                'journal_id': journal_ids[0].id,
                'period_id': brw_period.id,
                'period_line_id': brw_period_line.id,
                'change_payment':True,
                'payment_line_ids':[(5,),
                                    (0, 0, {
                                        "account_id": brw_account.id,
                                        "partner_id": brw_each.company_id.partner_id.id,
                                        "name": ref,
                                        "credit": brw_each.amount ,
                                        "debit": 0.00,
                                        'analytic_id':brw_analytic and brw_analytic.id or False
                                    })
                                    ]
            }
            obj_payment= self.env['account.payment'].with_context(allowed_company_ids=[company_to]) .with_user(self._uid).sudo().with_company(company_to)
            payment =obj_payment.create(payment_vals)
            payment.action_post()
            # Marcar como acreditado y guardar referencia
            brw_each.write({
                'accredited_other_company': True,
                'intercompany_payment_id': payment.id,
                'intercompany_payment_ref': payment.name,
            })

        return True

    def create_payment_multicompany(self):
        self.ensure_one()
        partner = self.partner_id
        company = self.env['res.company'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not company:
            raise ValidationError(f"No se encontró una compañía vinculada al partner: {partner.name}")
        allowed_company_ids=self._context.get('allowed_company_ids', [])
        # ⚠️ Activar temporalmente la compañía si no está activa para el usuario
        if company.id not in allowed_company_ids:
            allowed_company_ids = allowed_company_ids + [company.id]
            self = self.with_context(allowed_company_ids=allowed_company_ids)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Pago por Compañía',
            'res_model': 'account.payment.multicompany',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.payment.bank.macro.summary',
                'active_ids': [self.id],
                'active_id': self.id,
                'allowed_company_ids':allowed_company_ids
            }
        }

    search_move_doc = fields.Char(
        string="Factura / Asiento",
        compute="_compute_search_move_doc",
        store=False,
        search="_search_search_move_doc"
    )

    # Campo de búsqueda para OC relacionadas
    search_po_doc = fields.Char(
        string="Orden de Compra",
        compute="_compute_search_po_doc",
        store=False,
        search="_search_search_po_doc"
    )

    # ---------------------------------------------------
    # COMPUTADOS
    # ---------------------------------------------------
    def _compute_search_move_doc(self):
        for rec in self:
            line_ids=rec.line_ids.filtered(lambda l:l.request_id.type == 'account.move' and l.request_id)
            search_move_doc=False
            if line_ids:
                search_move_doc=",".join(line_ids.mapped('request_id.invoice_id.name'))
            rec.search_move_doc = search_move_doc

    def _compute_search_po_doc(self):
        for rec in self:
            line_ids = rec.line_ids.filtered(lambda l: l.request_id.type == 'purchase.order' and l.request_id)
            search_po_doc = False
            if line_ids:
                search_po_doc = ",".join(line_ids.mapped('request_id.order_id.name'))
            else:
                line_ids = rec.line_ids.filtered(lambda l: l.request_id.type == 'account.move' and l.request_id)
                if line_ids:
                    search_po_doc=",".join(line_ids.mapped('invoice_id.invoice_line_ids.purchase_line_id.order_id.name')  )
            rec.search_po_doc = search_po_doc

    @api.model
    def _search_search_move_doc(self, operator, value):
        """Busca en line_ids los documentos account.move (por invoice_id.name o ref)."""
        # Buscar moves por nombre de factura/asiento o ref
        moves = self.env['account.move'].search([
            '|',
            ('name', operator, value),
            ('ref', operator, value)
        ])
        if not moves:
            return [('id', '=', 0)]

        # Buscar summaries que tengan line_ids con esos moves
        summaries = self.search([
            ('line_ids.request_id.invoice_id', 'in', moves.ids)
        ])
        return [('id', 'in', summaries.ids)]

    @api.model
    def _search_search_po_doc(self, operator, value):
        """Busca OCs directas en line_ids o ligadas a facturas account.move."""
        domain = []

        # 1) OCs directas
        pos = self.env['purchase.order'].search([('name', operator, value)])
        if pos:
            summaries = self.search([
                ('line_ids.request_id.order_id', 'in', pos.ids)
            ])
            if summaries:
                domain.append(('id', 'in', summaries.ids))

        # 2) OCs desde facturas (account.move -> invoice_line_ids -> purchase.order)
        moves = self.env['account.move'].search([
            ('invoice_line_ids.purchase_line_id.order_id.name', operator, value)
        ])
        if moves:
            summaries = self.search([
                ('line_ids.request_id.invoice_id', 'in', moves.ids)
            ])
            if summaries:
                domain.append(('id', 'in', summaries.ids))

        if not domain:
            return [('id', '=', 0)]
        if len(domain) == 1:
            return domain
        return ['|'] + domain