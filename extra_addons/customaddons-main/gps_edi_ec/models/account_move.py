# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

from odoo import _, api, fields, models
from datetime import datetime,timedelta
from odoo.exceptions import ValidationError

from ...l10n_ec_edi.models import account_tax

L10N_EC_TAXSUPPORTS=[('01','01 Crédito fiscal por declaración de IVA (servicios y bienes distintos a inventarios y activos fijos)'),
('02','02 Costo o gasto para la declaración de IR (servicios y bienes distintos a inventarios y activos fijos)'),
('03','03 Activo fijo - Crédito fiscal por declaración de IVA'),
('04','04 Activo fijo - Costo o gasto para la declaración de IR'),
('05','05 Liquidación de gastos de viaje, alojamiento y comida (gastos por IR en nombre de los empleados y no de la empresa)'),
('06','06 Inventario - Crédito fiscal por declaración de IVA'),
('07','07 Inventario - Costo o gasto para declaración de IR'),
('08','08 Monto pagado para solicitar reembolso de gastos (intermediarios)'),
('09','09 Reembolso de reclamaciones'),
('10','10 Distribución de dividendos, beneficios o ganancias'),
('15','15 Pagos realizados por consumo propio y de terceros de servicios digitales'),
('00','00 Casos especiales cuyo soporte no aplica a las opciones anteriores'),
]

account_tax.L10N_EC_TAXSUPPORTS=L10N_EC_TAXSUPPORTS

class AccountMove(models.Model):
    _inherit = 'account.move'

    authorization_type = fields.Selection([('fisica', 'Fisica'), ('electronica', 'Electronica')], default="electronica",
                                          string="Tipo de Aut.", required=True)

    l10n_ec_code_taxsupport = fields.Selection(
        selection=L10N_EC_TAXSUPPORTS,
        string="Sustento Tributario",
        help="Indicates if the purchase invoice supports tax credit or cost or expenses, conforming table 5 of ATS",
        default="00"
    )

    @api.onchange('tax_totals', 'invoice_line_ids')
    @api.depends('tax_totals', 'invoice_line_ids')
    def _compute_amount_tax(self):
        DEC = 2
        for move in self:
            amount_base_exe, amount_base0, amount_baseno0, amount_tax0, amount_taxno0, amount_without_discount, amount_discount = 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00
            if move.invoice_line_ids:
                for brw_line in move.invoice_line_ids:
                    amount_without_discount_line = ((brw_line.quantity or 1.00) * (brw_line.price_unit or 0.00))
                    amount_discount_line = brw_line.discount_amount_currency
                    amount_discount += amount_discount_line
                    amount_without_discount += amount_without_discount_line
            if move.move_type != "entry":
                tax_totals = move.tax_totals
                if tax_totals:
                    group_tax_parts = tax_totals.get("groups_by_subtotal", [])
                    for each_group_tax_ky in group_tax_parts.keys():
                        if each_group_tax_ky.upper() == "BASE IMPONIBLE":
                            each_group_tax_list = group_tax_parts[each_group_tax_ky]
                            if each_group_tax_list:
                                for each_group_tax in each_group_tax_list:
                                    if each_group_tax["tax_group_amount"] != 0.00:
                                        amount_baseno0 += each_group_tax["tax_group_base_amount"]
                                        amount_taxno0 += each_group_tax["tax_group_amount"]
                                    else:
                                        if each_group_tax["tax_group_name"].upper() == "EXENTO DE IVA":
                                            amount_base_exe += each_group_tax["tax_group_base_amount"]
                                        else:
                                            amount_base0 += each_group_tax["tax_group_base_amount"]
                                            amount_tax0 += each_group_tax["tax_group_amount"]
                else:
                    amount_base_exe = move.amount_untaxed
            amount_without_discount = round(amount_without_discount, DEC)
            amount_discount = round(amount_without_discount - (amount_base0 + amount_baseno0), DEC)
            move.amount_without_discount = amount_without_discount
            move.amount_discount = amount_discount
            move.amount_base0 = amount_base0
            move.amount_baseno0 = amount_baseno0
            move.amount_tax0 = amount_tax0
            move.amount_taxno0 = amount_taxno0
            move.amount_base_exe = amount_base_exe

    def get_required_origin_info(self):
        for brw_each in self:
            required_origin_info = False
            if brw_each.move_type in ("out_refund", "out_invoice", "in_refund"):
                required_origin_info = (
                            brw_each.manual_origin and (brw_each.l10n_latam_document_type_id.code in ('04', '05')))
            brw_each.required_origin_info = required_origin_info

    amount_without_discount = fields.Monetary(
        string='Base sin descuento',
        compute='_compute_amount_tax', store=True, readonly=True
    )
    amount_discount = fields.Monetary(
        string='Descuento',
        compute='_compute_amount_tax', store=True, readonly=True
    )

    amount_base0 = fields.Monetary(
        string='Base 0',
        compute='_compute_amount_tax', store=True, readonly=True
    )
    amount_baseno0 = fields.Monetary(
        string='Base diferente 0',
        compute='_compute_amount_tax', store=True, readonly=True
    )
    amount_base_exe = fields.Monetary(
        string='Base Exenta',
        compute='_compute_amount_tax', store=True, readonly=True
    )
    amount_tax0 = fields.Monetary(
        string='Impuesto 0',
        compute='_compute_amount_tax', store=True, readonly=True
    )
    amount_taxno0 = fields.Monetary(
        string='Impuesto diferente 0',
        compute='_compute_amount_tax', store=True, readonly=True
    )

    anulado_sri = fields.Boolean(string="Anulado por SRI", default=False)
    motivo_anulacion_sri = fields.Text(string="Motivo Anulacion en  SRI", default=False)

    manual_origin = fields.Boolean("Origen Manual", default=True)
    required_origin_info = fields.Boolean(compute="get_required_origin_info",
                                          string="Requiere Informacion de Documento Origen", default=False)
    manual_document_number = fields.Char("# Documento Origen", size=18)

    manual_date = fields.Date("Fecha Documento Origen")
    manual_origin_authorization = fields.Char("Aut. Documento Origen", size=49)

    manual_origin_docnum = fields.Char("# Documento Origen Calculado",store=False,readonly=True,compute="_compute_origin_related")
    manual_origin_docdate = fields.Char("Fecha Documento Origen Calculado", store=False, readonly=True,
                                       compute="_compute_origin_related")

    l10n_ec_withhold_names = fields.Char("# Retenciones", store=True, readonly=True,
                                        compute="_compute_l10n_ec_withhold_inv_store_fields")

    l10n_ec_withhold_invoices_ids= fields.One2many("account.move.line","l10n_ec_withhold_invoice_id","Rel. Facturas Retenciones")

    @api.depends('country_code', 'l10n_ec_withhold_invoices_ids','state','l10n_ec_withhold_invoices_ids.move_id.state','l10n_ec_withhold_invoices_ids.move_id.name')
    def _compute_l10n_ec_withhold_inv_store_fields(self):
        invoices_ec = self.filtered(lambda inv: inv.country_code == 'EC')
        for invoice in invoices_ec:
            l10n_ec_withhold_names = None
            if invoice.is_invoice():
                withhold_ids = invoice.l10n_ec_withhold_ids
                if withhold_ids:
                    l10n_ec_withhold_names=",".join(withhold_ids.filtered(lambda x: x.state=='posted').mapped('name'))
            invoice.l10n_ec_withhold_names= l10n_ec_withhold_names

    def _compute_origin_related(self):
        for brw_each in self:
            brw_each.manual_origin_docnum=brw_each.manual_document_number
            brw_each.manual_origin_date = brw_each.manual_origin_date

    @api.onchange('manual_origin', 'l10n_latam_document_type_id')
    def onchange_manual_origin_l10n_latam_document_type_id(self):
        self.get_required_origin_info()

    @api.onchange('manual_document_number')
    def onchange_manual_document_number(self):
        if self.manual_document_number:
            manual_document_numbers = self.manual_document_number.split('-')
            if len(manual_document_numbers) == 3:
                estab_part = "000%s" % (manual_document_numbers[0],)
                pto_part = "000%s" % (manual_document_numbers[1],)
                sequence_part = "000000000%s" % (manual_document_numbers[2],)
                estab_part = estab_part[-3:]
                pto_part = pto_part[-3:]
                sequence_part = sequence_part[-9:]
                manual_document_number = "%s-%s-%s" % (estab_part, pto_part, sequence_part)
                self.manual_document_number = manual_document_number

    def button_draft(self):
        """Restringe la reversión de un asiento contable si el usuario no pertenece al grupo 'Jefe Contable'"""
        if not self._context.get('pass_validation_reverse',False):
            if not self.env.user.has_group('gps_edi_ec.group_jefe_contable'):
                raise ValidationError(_("No tienes permisos para reversar un asiento contable publicado. Contacta al Jefe Contable."))

        return super(AccountMove, self).button_draft()

    def button_cancel(self):
        if not self._context.get('pass_validation_reverse',False):
            if not self.env.user.has_group('gps_edi_ec.group_jefe_contable'):
                raise ValidationError(_("No tienes permisos para anular un asiento contable publicado. Contacta al Jefe Contable."))

        for brw_each in self:
            brw_each.line_ids.remove_move_reconcile()
        values=super(AccountMove,self).button_cancel()
        for brw_each in self:
            if brw_each.state=="cancel":
                if brw_each.journal_id.l10n_ec_withhold_type=="in_withhold" or (brw_each.move_type in ("out_invoice","out_refund")):
                    if brw_each.edi_document_ids:
                        for brw_document in brw_each.edi_document_ids:
                            brw_each.anulado_sri=True
                if brw_each.journal_id.l10n_ec_withhold_type=="in_withhold" or (brw_each.move_type in ("out_invoice","out_refund")):
                    brw_each.edi_state="cancelled"
                    if brw_each.edi_document_ids:
                        brw_each.edi_document_ids.state = "cancelled"
        return values

    def action_post(self):
        for brw_each in self:
            #brw_each.validate_partners()
            if brw_each.move_type == 'entry' and not self.env.user.has_group('gps_edi_ec.group_jefe_contable') and not (brw_each.l10n_ec_withhold_type =='in_withhold' or brw_each.l10n_ec_withhold_type =='out_withhold') and not brw_each.prepayment_assignment:
                raise ValidationError(_("No tienes permiso para confirmar asientos manuales."))
            if brw_each.move_type!='entry':
                if brw_each.journal_id.l10n_latam_use_documents:
                    if brw_each.l10n_latam_manual_document_number:
                        if brw_each.l10n_latam_document_type_id.code!='00':
                            if brw_each.move_type in ("in_invoice","in_refund"):
                                if not brw_each.l10n_ec_code_taxsupport:
                                    raise ValidationError(_("Debes llenar el respectivo Sustento Tributario?"))
                                if not brw_each.l10n_ec_authorization_number:
                                    raise ValidationError(_("Debes llenar el # de Autorizacion"))
                                if brw_each.authorization_type == "fisica":
                                    if len(brw_each.l10n_ec_authorization_number) != 10:
                                        raise ValidationError(_("# Autorizacion debe tener longitud de 10"))
                                if brw_each.authorization_type == "electronica":
                                    if len(brw_each.l10n_ec_authorization_number) != 49:
                                        raise ValidationError(_("# Autorizacion debe tener longitud de 49"))
        values = super(AccountMove, self).action_post()
        return values

    def _l10n_ec_set_authorization_number(self):
        self.ensure_one()
        if self.move_type=='out_receipt':
            return
        return super(AccountMove,self)._l10n_ec_set_authorization_number()

    def write(self, vals):
        value = super(AccountMove, self).write(vals)
        self.complete_related_doc_data()
        return value

    @api.model
    def create(self, vals):
        brw_new = super(AccountMove, self).create(vals)
        brw_new.complete_related_doc_data()
        return brw_new

    def complete_related_doc_data(self):
        if self.l10n_latam_document_type_id and self.journal_id:
            if self.reversed_entry_id:
                vals = {"manual_date": self.reversed_entry_id.invoice_date,
                        "manual_document_number": self.reversed_entry_id.l10n_latam_document_number,
                        "manual_origin_authorization": self.reversed_entry_id.l10n_ec_authorization_number}
                self._write(vals)
            if self.debit_origin_id:
                vals = {
                    "manual_date": self.debit_origin_id.invoice_date,
                     "manual_document_number": self.debit_origin_id.l10n_latam_document_number,
                     "manual_origin_authorization":self.debit_origin_id.l10n_ec_authorization_number
                }
                self._write(vals)

    def validate_partners(self):
        # for brw_each in self:
        #     if brw_each.partner_id:
        #         if not brw_each.partner_id.company_id:
        #             raise ValidationError(_("El contacto %s  con id %s debe tener definido una empresa") % (brw_each.partner_id.name,brw_each.partner_id.id))
        #     if brw_each.line_ids:
        #         for brw_line in brw_each.line_ids:
        #             if brw_line.partner_id:
        #                 if not brw_line.partner_id.company_id:
        #                     raise ValidationError(
        #                         _("El contacto %s con id %s debe tener definido una empresa") % (brw_line.partner_id.name,brw_each.partner_id.id))
        return True

    def js_remove_outstanding_partial(self, partial_id):
        self=self.with_context(pass_validation_reverse=True)
        res = super(AccountMove,self).js_remove_outstanding_partial(partial_id)
        return res

    @api.depends('country_code', 'l10n_latam_document_type_id.code', 'l10n_ec_withhold_ids')
    def _compute_l10n_ec_show_add_withhold(self):
        # shows/hide "ADD WITHHOLD" button on invoices
        invoices_ec = self.filtered(lambda inv: inv.country_code == 'EC')
        (self - invoices_ec).l10n_ec_show_add_withhold = False
        for invoice in invoices_ec:
            codes_to_withhold = [
                '01',  # Factura compra
                '02',  # Nota de venta
                '03',  # Liquidacion compra
                '05',   #nota de debito ,se agrega
                '08',  # Entradas a espectaculos
                '09',  # Tiquetes
                '11',  # Pasajes
                '12',  # Inst FInancieras
                '20',  # Estado
                '21',  # Carta porte aereo
                '47',  # Nota de crédito de reembolso
                '48',  # Nota de débito de reembolso
                '41',  # Comprobante de venta emitido por reembolso
            ]
            add_withhold = invoice.country_code == 'EC' and invoice.l10n_latam_document_type_id.code in codes_to_withhold
            add_withhold = add_withhold and not invoice.l10n_ec_withhold_ids.filtered(lambda w: w.state == 'posted')
            invoice.l10n_ec_show_add_withhold = add_withhold