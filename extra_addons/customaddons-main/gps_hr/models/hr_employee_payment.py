# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
import re
import unicodedata
import base64
import io
import csv
from datetime import datetime
from collections import defaultdict

class HrEmployeePayment(models.Model):
    _name = "hr.employee.payment"
    _description = "Pagos a Empleados"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_default_company_id(self):
        if self._context.get("allowed_company_ids", []):
            return self._context.get("allowed_company_ids", [])[0]
        return False

    name = fields.Char("Descripción", size=255, required=True,tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,tracking=True
    )

    currency_id = fields.Many2one("res.currency", "Moneda", compute="compute_company_values", store=True)
    partner_id = fields.Many2one("res.partner", "Contacto", compute="compute_company_values", store=True)

    date_process = fields.Date("Fecha del Proceso", default=fields.Date.today(), required=True,tracking=True)

    month_id = fields.Many2one("calendar.month", "Mes", compute="_compute_date_info", store=True, required=False)
    year = fields.Integer("Año", compute="_compute_date_info", store=True, required=False)

    comments = fields.Text("Comentarios",tracking=True)

    total = fields.Monetary("Total", digits=(16, 2), default=0.00, compute="_compute_total", store=True, required=False,tracking=True)
    state = fields.Selection([('draft', 'Preliminar'),
                              ('sended', 'Enviado'),
                              ('approved', 'Realizado'),
                              ('cancelled', 'Anulado') ], default="draft", required=True, string="Estado",tracking=True)

    payment_bank_account_id=fields.Many2one("res.partner.bank","# Cuenta Bancaria",required=False)
    payment_journal_id = fields.Many2one("account.journal", "Diario", required=False,tracking=True)

    movement_ids = fields.Many2many("hr.employee.movement", "payment_movement_rel","payment_id","movement_id","Lote de Movimientos")
    payslip_ids = fields.Many2many("hr.payslip.run", "payment_payslip_run_rel", "payment_id", "payslip_run_id","Lote de Roles")

    movement_line_ids = fields.Many2many("hr.employee.movement.line", "payment_movement_line_rel", "payment_id", "movement_id",
                                    "Movimientos",tracking=True)
    payslip_line_ids = fields.Many2many("hr.payslip", "payment_payslip_rel", "payment_id", "payslip_run_id", "Roles",tracking=True)

    paid_movement_line_ids = fields.Many2many("hr.employee.movement.line", "paid_payment_movement_line_rel", "payment_id",
                                         "movement_id",
                                         "Movimientos", tracking=True,compute="_compute_paid_movement_line_ids")

    line_ids=fields.One2many("hr.employee.payment.line","process_id","Detalle de Pagos",tracking=True)
    move_ids=fields.One2many("hr.employee.payment.move","process_id","Asiento Contable",tracking=True)

    move_id = fields.Many2one("account.move", string="# Asiento")
    payment_id = fields.Many2one("account.payment", string="# Pago")


    csv_export_file =fields.Binary(string="Archivo Reporte")
    csv_export_filename = fields.Char(stirng="Nombre Archivo")

    attachment_id=fields.Many2one("ir.attachment","Informe Adjunto")
    ref=fields.Char("Referencia",tracking=True)

    bank_reference = fields.Char("Referencia Bancaria", tracking=True)

    pay_with_transfer = fields.Boolean("Pagar con Transferencia", default=True,tracking=True)
    account_id = fields.Many2one('account.account', 'Cuenta', required=False)

    filter_iess = fields.Boolean(string="Solo Afiliados",compute="_compute_filter_iess", default=False, tracking=True)

    @api.depends('payslip_ids','movement_ids')
    def _compute_filter_iess(self):
        for brw_each in self:
            filter_iess=False
            if brw_each.payslip_ids:
                filter_iess=brw_each.payslip_ids.mapped('type_struct_id.legal_iess')[0]
            if brw_each.movement_ids:
                filter_iess = brw_each.movement_ids.mapped('filter_iess')[0]
            brw_each.filter_iess=filter_iess

    def action_create_payment_document(self):

        return True

    @api.onchange('payment_journal_id')
    def onchange_payment_journal_id(self):
        if not self.payment_journal_id:
            self.account_id = False
        else:
            self.account_id = self.payment_journal_id.default_account_id and self.payment_journal_id.default_account_id.id or False


    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []

        if name:
            domain = ['|', '|',
                      ('ref', operator, name),
                      ('name', operator, name),
                      ('id', '=', name if name.isdigit() else 0)]

        records = self.search(domain + args, limit=limit)
        return records.name_get()

    _rec_name = "name"#
    _order = "id desc"

    _check_company_auto = True

    @api.depends('company_id')
    def compute_company_values(self):
        for brw_each in self:
            brw_each.currency_id = brw_each.company_id and brw_each.company_id.currency_id.id or False
            brw_each.partner_id = brw_each.company_id and brw_each.company_id.partner_id.id or False

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.compute_company_values()
        self.payment_bank_account_id=False
        self.payment_journal_id=False
        self.movement_ids=[(6,0,[])]
        self.payslip_ids = [(6, 0, [])]
        self.line_ids = [(5,)]
        self.move_ids = [(5,)]

    @api.depends('line_ids')
    @api.onchange('line_ids')
    def _compute_total(self):
        DEC=2
        for brw_each in self:
            total=0.00
            for brw_line in brw_each.line_ids:
                total+=brw_line.total
            brw_each.total=round(total,DEC)

    def update_accounts_info(self):
        for brw_each in self:
            line_ids = [(5,)]#,'movement_line_ids','payslip_line_ids'
            movement_line_ids = brw_each.movement_line_ids.ids + [-1, -1]
            payslip_line_ids = brw_each.payslip_line_ids.ids + [-1, -1]
            self._cr.execute("""select x.employee_id,
he.bank_id as bank_id,
he.account_number as bank_acc_number,
case when(he.bank_type='checking') then 'Corriente' else 'Ahorro' end as bank_tipo_cuenta,
he.tercero,
he.l10n_latam_identification_tercero_id,
he.identificacion_tercero,
he.nombre_tercero,
sum(x.total) as total 
from 
(
	select heml.employee_id,
	heml.total
	from hr_employee_movement hem
	inner join hr_employee_movement_line heml on heml.process_id=hem.id 
	inner join hr_salary_rule hsr on hsr.id=hem.rule_id 
	where hsr.payment=true and heml.id in %s and hem.state='approved'  
	union all 
	select ps.employee_id,
	ps.total_payslip as total
	from hr_payslip_run psr
	inner join hr_payslip ps on ps.payslip_run_id=psr.id 
	where ps.id in %s and psr.state='close' 
) x 
inner join hr_employee he on he.id=x.employee_id 
group by 
x.employee_id,
he.bank_id,
he.account_number,
he.bank_type,he.tercero,
he.l10n_latam_identification_tercero_id,
he.identificacion_tercero,
he.nombre_tercero  """, (tuple(movement_line_ids),  tuple(payslip_line_ids) ))
            result = self._cr.dictfetchall()
            if result:
                for each_result in result:
                    each_result["name"] = brw_each.name
                    line_ids.append((0, 0, each_result))
            brw_each.line_ids = line_ids

    @api.onchange('movement_ids', 'payslip_ids', 'pay_with_transfer')
    @api.depends('movement_ids', 'payslip_ids', 'pay_with_transfer')
    def _compute_paid_movement_line_ids(self):
        for brw_each in self:
            paid_movement_line_ids = brw_each.movement_ids.line_ids._origin.filtered(
                lambda x: x.pay_with_transfer == brw_each.pay_with_transfer and x.state == 'approved' and (
                    x.for_payment_ids.filtered(lambda y: y != brw_each and y.state not in ('cancelled',))))
            brw_each.paid_movement_line_ids = paid_movement_line_ids

    @api.onchange('movement_ids', 'payslip_ids', 'pay_with_transfer')
    def onchange_batchs(self):
        for brw_each in self:
            brw_movement_line=brw_each.movement_ids and brw_each.movement_ids.line_ids.filtered(lambda x: x.pay_with_transfer==brw_each.pay_with_transfer and not x.has_payment and x.state=='approved' and not (x.for_payment_ids.filtered(lambda y:y!=brw_each and  y.state not in ('cancelled',)) ) )
            movement_line_ids=brw_movement_line and brw_movement_line.ids or []
            payslip_line_ids = brw_each.payslip_ids and brw_each.payslip_ids.slip_ids.filtered(
                lambda x: x.pay_with_transfer==brw_each.pay_with_transfer and not x.has_payments and x.state=='done').ids or []
            brw_each.movement_line_ids = [(6,0,movement_line_ids)]
            brw_each.payslip_line_ids= [(6,0,payslip_line_ids)]
            brw_each.onchange_lines()

    @api.onchange('movement_line_ids','payslip_line_ids','payment_journal_id','pay_with_transfer','name')
    @api.depends('movement_line_ids','payslip_line_ids','payment_journal_id','pay_with_transfer','name')
    def onchange_lines(self):
        for brw_each in self:
            brw_each.update_accounts_info()
            move_ids=[(5,)]
            total=0.00
            #grouped_lines = defaultdict(float)

            for brw_document in brw_each.movement_ids:
                if brw_document.legal_iess and  brw_document.move_id:
                    brw_movement_lines=brw_document.line_ids.filtered(lambda x: x in brw_each.movement_line_ids)._origin
                    brw_account_move_line=brw_document.move_id.line_ids.filtered(lambda x:x.credit>0)#debe ser 1
                    for brw_line in brw_movement_lines:
                        #key = (brw_account_move_line.account_id.id, brw_line.employee_id.partner_id.id)
                        if brw_line.total>0.00:
                            #grouped_lines[key] += brw_line.total
                            move_ids += [(0, 0, {
                                    "account_id": brw_account_move_line.account_id.id,
                                    "move_id": brw_document.move_id.id,
                                    "debit": brw_line.total,
                                    "credit": 0,
                                    "move_line_id":brw_account_move_line.id,
                                    "partner_id":brw_line.employee_id.partner_id.id,
                                    'movement_line_id':brw_line.id
                            })]
                            total+=brw_line.total
                if not brw_document.legal_iess and brw_document._origin.move_id:
                    brw_movement_lines = brw_document.line_ids.filtered(
                            lambda x: x in brw_each.movement_line_ids)._origin
                    brw_account_move_line = brw_document.move_id.line_ids.filtered(
                            lambda x: x.credit > 0)  # debe ser 1
                    for brw_line in brw_movement_lines:
                        # key = (brw_account_move_line.account_id.id, brw_line.employee_id.partner_id.id)
                        if brw_line.total > 0.00:
                            account_partner = brw_line.contract_id.get_contact_account()
                            if not account_partner:
                                raise ValidationError(
                                    _("No hay contacto para la contabilizacion para %s") % (brw_line.employee_id.name,))

                            move_ids += [(0, 0, {
                                        "account_id": brw_account_move_line.account_id.id,
                                        "move_id": brw_document.move_id.id,
                                        "debit": brw_line.total,
                                        "credit": 0,
                                        "move_line_id": brw_account_move_line.id,
                                        "partner_id": account_partner.id,#brw_line.employee_id.partner_id.id,
                                        'movement_line_id': brw_line.id
                                })]
                            total += brw_line.total

                    # if not brw_document.legal_iess and  brw_document.move_id:
                    #     brw_account_move_line = brw_document.move_id.line_ids.filtered(lambda x: x.credit > 0)  # debe ser 1
                    #
                    #     for brw_line in brw_document.move_id.line_ids:
                    #         if brw_line.credit > 0:  ##valores a pagar
                    #             move_ids += [(0, 0, {
                    #                 "account_id": brw_line.account_id.id,
                    #                     "move_id": brw_document.move_id.id,
                    #                     "debit": brw_line.credit,
                    #                     "credit": 0,
                    #                     "move_line_id":brw_line.id,
                    #                     "partner_id":brw_document.company_id.partner_id.id
                    #             })]
                    #             total+=brw_line.credit
            ######################
            brw_company=brw_each.company_id
            ACCOUNT=self.env.ref('gps_hr.rule_SALARIO').rule_account_ids.filtered(lambda x:
                                                                                  x.type=='payslip' and  x.account_type=='credit' and  x.company_id==brw_company).mapped('account_id')
            for brw_document in brw_each.payslip_ids:
                if brw_document.legal_iess and brw_document.move_id:
                    brw_payslip_lines = brw_document.slip_ids.filtered( lambda x: x in brw_each.payslip_line_ids)._origin
                    brw_account_move_line = brw_document.move_id.line_ids.filtered(lambda x: x.credit > 0 and x.account_id==ACCOUNT)   # debe ser 1
                    for brw_line in brw_payslip_lines:
                        if brw_line.total_payslip > 0.00:
                            #if brw_line.credit > 0 :  ##valores a pagar
                            move_ids += [(0, 0, {
                                "account_id": brw_account_move_line.account_id.id,
                                "move_id": brw_document.move_id.id,
                                "debit": brw_line.total_payslip,
                                "credit": 0,
                                "move_line_id":brw_account_move_line.id,
                                "partner_id":brw_line.employee_id.partner_id.id,
                                'payslip_id':brw_line.id,
                            })]
                            total+=brw_line.total_payslip
                if not brw_document.legal_iess :#and brw_document.move_id
                    brw_payslip_lines = brw_document.slip_ids.filtered(lambda x: x in brw_each.payslip_line_ids)._origin
                    for brw_line in brw_payslip_lines:
                        total_payslip=brw_line.total_payslip
                        if total_payslip > 0.00:
                            account_partner = brw_line.contract_id.get_contact_account()
                            if not account_partner:
                                raise ValidationError(
                                    _("No hay contacto para la contabilizacion para %s") % (brw_line.employee_id.name,))
                            move_ids += [(0, 0, {
                               "account_id": self._get_account_noiess_id(account_partner),
                               "move_id": False,
                               "debit": total_payslip,
                               "credit": 0,
                               "move_line_id": False,
                               "partner_id": account_partner.id,
                                'payslip_id': brw_line.id,
                            })]
                            total += total_payslip
            acc_id = brw_each.payment_journal_id.default_account_id.id
            if total>0.00:
                move_ids += [(0, 0, {
                    "account_id": acc_id,
                    "move_id": False,
                    "debit": 0,
                    "credit": total,
                    "partner_id": brw_each.company_id.partner_id.id
                })]
            #print(move_ids)
            brw_each.move_ids = move_ids

    def _get_account_noiess_id(self,account_partner):
        self.ensure_one()
        return account_partner.property_account_payable_id.id

    def quitar_tildes(texto):
        # Normalizar el texto a su forma descompuesta
        texto_normalizado = unicodedata.normalize('NFD', texto)
        # Eliminar los caracteres diacríticos (tildes, ñ, etc.)
        texto_sin_tildes = ''.join(
            char for char in texto_normalizado if unicodedata.category(char) != 'Mn'
        )
        return texto_sin_tildes
    
    def genera_archivo(self):
        if self.state!='approved':
            self.update_accounts_info()
        print('genera archivo')
        company = self.company_id.name
        if company == 'IMPORT GREEN POWER TECHNOLOGY, EQUIPMENT & MACHINERY ITEM S.A':
            codbanco = '11074'  # Verificar!
        if company == 'GREEN ENERGY CONSTRUCTIONS & INTEGRATION C&I SA':
            codbanco = '11100'  # Verificar!
        csvfile = io.StringIO()
        writer = csv.writer(csvfile, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='')
        fechahoy = datetime.now()
        i = 1
        file_name =False
        if not self.payment_journal_id:
            raise ValidationError(_("Debes definir un diario de bancos"))
        journal_name=self.payment_journal_id.name.lower()
        if 'bolivariano' in journal_name:
            file_name='pago_bolivariano_nomina.biz'
        if 'internacional' in journal_name:
            file_name='pago_internacional_nomina.txt'
        if 'produbanco' in journal_name:
            file_name='pago_produbanco_nomina.txt'
        for x in self.line_ids:
            identificacion = x.employee_id.identification_id
            tipo_identificacion = (x.employee_id.l10n_latam_identification_type_id == self.env.ref(
                "l10n_ec.ec_dni")) and 'C' or 'P'
            nombre_persona_pago = x.employee_id.name
            if x.total>0.00:
                if x.employee_id.tercero:
                    identificacion = x.employee_id.identificacion_tercero
                    tipo_identificacion = (x.employee_id.l10n_latam_identification_tercero_id == self.env.ref(
                        "l10n_ec.ec_dni")) and 'C' or 'P'
                    if (x.employee_id.l10n_latam_identification_tercero_id == self.env.ref(
                        "l10n_ec.ec_ruc")):
                        tipo_identificacion='R'
                    nombre_persona_pago = x.employee_id.nombre_tercero or nombre_persona_pago
                if 'bolivariano' in journal_name:
                    codigos_bancos = self.env.ref("l10n_ec.bank_12").get_all_codes()
                    if not codigos_bancos:
                        raise ValidationError(_("No hay codigos de bancos recuperados para BOLIVARIANO"))
                    bic=codigos_bancos.get(x.employee_id.bank_id.id,False)
                    if not bic:
                        raise ValidationError(_("No hay codigo encontrado para BOLIVARIANO para %s") % (x.employee_id.bank_id.name,))
                    tipo_cta = '03' if x.employee_id.bank_type == 'checking' else '04'
                    #forma_pago = 'CUE' if str(x.employee_id.bank_id.bic)== '37' else 'COB'
                    #code_bank = '34' if str(x.employee_id.bank_id.bic) == '37' else str(x.employee_id.bank_id.bic)
                    #if code_bank=='213':##juventud ecuatoriana progresista
                    #    code_bank='06'
                    code_bank=bic
                    forma_pago = 'CUE' if str(bic) == '34' else 'COB'#ya no es 37 es 34

                    #if code_bank=='429':##daquilema
                    #    code_bank='4102'
                    # pname = re.sub(r'[^0-9]', '', row_data['payment_name'].replace('.', ''))
                    idpago = self.id
                    fila = (
                            'BZDET' + str(i).zfill(6) +  # 001-011
                            identificacion.ljust(18) +  # 012-029
                            tipo_identificacion+#x.employee_id.partner_id.l10n_latam_identification_type_id.name[:1].upper()+# if x.employee_id.partner_id.l10n_latam_identification_type_id else '' +  # 030-030
                            identificacion.ljust(14) +  # 031-044
                            nombre_persona_pago[:60].ljust(60).replace("Ñ", "N").replace("ñ", "n") +  # 045-104
                            forma_pago[:3] +  # 105-107
                            '001' +  # Código de país (001) 108-110
                            #code_bank[:2].ljust(2) +  # 111-112
                            ' ' * 2+ # 111-112
                            tipo_cta +  # 113-114
                            x.employee_id.account_number[:20].ljust(20) +  # 115-134
                            '1' +  # Código de moneda (1) 135-135
                            str("{:.2f}".format(x.total)).replace('.', '').zfill(15) +  # 136-150
                            x.name[:60].ljust(60) +  # 151-210
                            #(row_data['payment_name']).zfill(14) +  # 211-225
                            str(idpago).zfill(15) +  # 211-225
                            '0' * 15 +  # Número de comprobante de retención 226-240
                            '0' * 15 +  # Número de comprobante de IVA 241-255
                            '0' * 20 +  # Número de factura - SRI 256-275
                            ' ' * 9 +  # Código de grupo 276-285
                            ' ' * 50 +  # Descripción del grupo 286-335
                            ('NO TIENE').ljust(50) + #x.employee_id.partner_id.street[:50].ljust(50)  if x.employee_id.partner_id.street else 'NO TIENE'+  # Dirección del beneficiario 336-385
                            ' ' * 21 +  # Teléfono 386-405
                            'RPA' +  # Código del servicio 406-408
                            ' ' * 10 * 3 +  # Cédula 1, 2, 3 para retiro 409-438
                            ' ' +  # Seña de control de horario 439-439
                            codbanco +  # Código empresa asignado 440-444
                            '0' +  # Código de sub-empresa 445-450
                            codbanco +  # Código de sub-empresa 445-450
                            'RPA' + #code_bank[:2].ljust(2) +  # Sub-motivo de pago/cobro 451-453
                            ' ' * 10 +
                            code_bank[:2].ljust(2)
                            )
                    print(fila)
                    writer.writerow([fila])
                    i = i + 1
                if 'internacional' in journal_name:
                    codigos_bancos=self.env.ref("l10n_ec.bank_8").get_all_codes()
                    if not codigos_bancos:
                        raise ValidationError(_("No hay codigos de bancos recuperados para INTERNACIONAL"))
                    tipo_cta = 'CTE' if x.employee_id.bank_type == 'checking' else 'AHO'
                    # code_bank = 'CUE001'.ljust(8) if row_data['bank_code'] == '37' else 'COB001'.ljust(8)
                    #forma_pago = 'CUE' if str(x.employee_id.bank_id.bic) == '37' else 'COB'
                    #code_bank = str(x.employee_id.bank_id.bic)
                    bic = codigos_bancos.get(x.employee_id.bank_id.id, False)
                    if not bic:
                        raise ValidationError(
                            _("No hay codigo encontrado para INTERNACIONAL para %s") % (x.employee_id.bank_id.name,))

                    forma_pago = 'CUE' if bic == '37' else 'COB'
                    code_bank = bic
                    payment_name=x.name[:60].ljust(60)
                    pname = re.sub(r'[^0-9]', '',payment_name.replace('.', ''))
                    codpago = re.sub(r'[^0-9]', '', pname)
                    fila = [
                        'PA',
                        identificacion,
                        'USD',
                        str("{:.2f}".format(x.total)).replace('.', ''),
                        'CTA',
                        tipo_cta,
                        x.employee_id.account_number,
                        payment_name,
                        tipo_identificacion,
                        identificacion,
                        nombre_persona_pago,
                        code_bank
                    ]
                    writer.writerow(fila)
                if 'produbanco' in journal_name:
                    codigos_bancos = self.env.ref("l10n_ec.bank_11").get_all_codes()
                    if not codigos_bancos:
                        raise ValidationError(_("No hay codigos de bancos recuperados para PRODUBANCO"))
                    tipo_cta = 'CTE' if x.employee_id.bank_type == 'checking' else 'AHO'
                    # code_bank = 'CUE001'.ljust(8) if row_data['bank_code'] == '37' else 'COB001'.ljust(8)
                    # forma_pago = 'CUE' if str(x.employee_id.bank_id.bic) == '37' else 'COB'
                    # code_bank = str(x.employee_id.bank_id.bic)
                    bic = codigos_bancos.get(x.employee_id.bank_id.id, False)
                    if not bic:
                        raise ValidationError(
                            _("No hay codigo encontrado para PRODUBANCO para %s") % (x.employee_id.bank_id.name,))

                    code_bank = bic
                    payment_name = x.name[:60].ljust(60)
                    pname = re.sub(r'[^0-9]', '', payment_name.replace('.', ''))
                    # 045-104
                    fila = [
                        'PA',  # Código Orientación
                        self.payment_journal_id.bank_account_id.acc_number.zfill(11),  ##Cuenta Empresa
                        str(i).zfill(7),  # Secuencial Pago
                        str(x.id),  # Comprobante de Pago
                        identificacion,  # Contrapartida
                        'USD',  # mONEDA
                        str("{:.2f}".format(x.total)).replace('.', '').zfill(11),  # Valor
                        'CTA',  # Forma de Pago
                        code_bank.zfill(4),  # Código de Institución Financiera
                        tipo_cta,  # Tipo de Cuenta
                        x.employee_id.account_number.zfill(11),  # Número d Cuenta
                        tipo_identificacion,  # Tipo ID Cliente
                        identificacion,  # Número ID Cliente Beneficiario
                        nombre_persona_pago[:60].ljust(60).replace("Ñ", "N").replace("ñ", "n"),  # Nombre del Cliente
                        '',  # Dirección Beneficiario
                        '',  # Ciudad Beneficiario
                        '',  # Teléfono Beneficiario
                        'GUAYAQUIL',  # Localidad de pago
                        payment_name,  # Referencia
                        'PAGO NOMINA'
                        # Referencia Adicional
                    ]
                    writer.writerow(fila)
        file_content = csvfile.getvalue()
        if not file_name:
            raise ValidationError(_("No hay nombre definido para el archivo"))
        if not file_content.strip():
            raise UserError(_("El archivo generado está vacío. Por favor, revise los datos de entrada."))
        file_content_base64 = base64.b64encode(file_content.encode())
        self.csv_export_file = file_content_base64
        self.csv_export_filename = file_name#
        base_url = self.env['ir.config_parameter'].get_param('param.download.bancos.url')
        attachment_obj = self.env['ir.attachment']
        attachment_id = attachment_obj.create({'name': f"{file_name}",
                                            'type': "binary",
                                            'datas': file_content_base64,
                                            'mimetype': 'text/csv',
                                            'store_fname': file_name})
        self.attachment_id = attachment_id.id
        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }

    @api.onchange('date_process')
    def onchange_account_date_process(self):
        self.update_date_info()

    @api.depends('date_process')
    def _compute_date_info(self):
        for brw_each in self:
            brw_each.update_date_info()

    def update_date_info(self):
        for brw_each in self:
            month_id = False
            year = False
            if brw_each.date_process:
                month_srch = self.env["calendar.month"].sudo().search([('value', '=', brw_each.date_process.month)])
                year = brw_each.date_process.year
                month_id = month_srch and month_srch[0].id or False
            brw_each.month_id = month_id
            brw_each.year = year

    def unlink(self):
        for brw_each in self:
            if self._context.get("validate_unlink", True):
                if brw_each.state != 'draft':
                    raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        return super(HrEmployeePayment, self).unlink()

    def action_cancel_request(self):
        for brw_each in self:
            pass
        return True

    def action_cancel_reverse_payment(self):
        for brw_each in self:
            pass
        return True

    def action_sended(self):
        for brw_each in self:
            brw_each.write({ "state":"sended" })
        return True

    def action_draft(self):
        for brw_each in self:
            brw_each.write({ "state":"draft" })
            brw_each.action_cancel_request()
        return True

    def action_approved(self):
        OBJ_PAYMENT = self.env["account.payment"]
        for brw_each in self:
            if not brw_each.payment_journal_id:
                raise ValidationError(_("Debes definir un diario para realizar el Pago"))
            if not brw_each.move_ids:
                raise ValidationError(_("No existen detalle para generar los pagos"))

            OBJ_PERIOD_LINE = self.env["account.fiscal.year.line"].sudo()
            payment_date =  brw_each.date_process
            brw_period, brw_period_line = OBJ_PERIOD_LINE.get_periods(payment_date, brw_each.company_id,
                                                                      for_account_payment=True)

            template_payments =  {
                'payment_type': 'outbound',
                'partner_id': None,
                'partner_type': 'supplier',
                'journal_id': brw_each.payment_journal_id.id,
                'company_id':  brw_each.company_id.id,
                'currency_id':  brw_each.company_id.currency_id.id,
                'date': payment_date,
                'amount': 0.00,
                'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
                'ref': set(),
                'is_prepayment': False,
                'prepayment_account_id': None,
                'period_id': brw_period.id,
                'period_line_id': brw_period_line.id,
                'change_payment': True,
                #'brw_movement_line': self.env["hr.employee.movement.line"],
                #'brw_payslip': self.env["hr.payslip"],
                'payment_purchase_line_ids': [(5,)],
                #'map_amounts': {},
                #'map_accounts': {}
            }

            grouped_payments = defaultdict(list)

            # Recorremos las líneas contables y agrupamos las que no coincidan con la cuenta destino
            for brw_line in brw_each.move_ids:
                if brw_line.account_id != brw_each.account_id and brw_line.partner_id:
                    grouped_payments[brw_line.partner_id.id].append(brw_line)
            payment_refs=[]
            # Creamos un pago por cada partner_id
            for partner_id, lines in grouped_payments.items():
                payment_line_ids = [(5,)]
                total_amount = 0.0
                movement_lines=self.env["hr.employee.movement.line"]
                payslip_lines = self.env["hr.payslip"]
                for line in lines:
                    rec_name_for_payment=None
                    if line.movement_line_id:
                        rec_name_for_payment=line.movement_line_id.process_id.name
                    if line.payslip_id:
                        rec_name_for_payment=line.payslip_id.payslip_run_id.name
                    payment_line_ids.append((0, 0, {
                        "account_id": line.account_id.id,
                        "partner_id":  partner_id,#line.movement_line_id.process_id.company_id.partner_id.id,
                        "name": rec_name_for_payment,
                        "credit": 0.00,
                        "debit": line.debit
                    }))
                    total_amount += line.debit
                    movement_lines+=line.movement_line_id
                    payslip_lines += line.payslip_id
                    if rec_name_for_payment not in payment_refs:
                        payment_refs.append(rec_name_for_payment)
                payments = template_payments.copy()
                payments.update({
                    "amount": total_amount,
                    "ref": ",".join(payment_refs),
                    "change_payment": True,
                    "partner_id": partner_id,
                    "payment_line_ids": payment_line_ids,
                })

                brw_payment = OBJ_PAYMENT.create(payments)
                brw_payment.action_post()


                if brw_payment.state != "posted":
                    raise ValidationError(
                        _("Asiento contable %s, id %s no fue publicado!") % (brw_payment.name, brw_payment.id)
                    )
                if movement_lines:
                    movement_lines.write({"payment_id": brw_payment.id})
                if payslip_lines:
                    payslip_lines.write({"payment_id": brw_payment.id})
                brw_invoice_lines = self.env["account.move.line"]
                for x in brw_payment.move_id.line_ids:
                    if x.debit > 0 and x.amount_residual != 0.00:
                        brw_invoice_lines+=x
                        for brw_movement in brw_each.movement_ids:
                            for y in brw_movement.move_id.line_ids:
                                if y.credit > 0 and y.partner_id == x.partner_id and y.account_id == x.account_id and y.amount_residual != 0.00:
                                    brw_invoice_lines += y
                        for brw_payslip in brw_each.payslip_ids:
                            for y in brw_payslip.move_id.line_ids:
                                if y.credit > 0 and y.partner_id == x.partner_id and y.account_id == x.account_id and y.amount_residual != 0.00:
                                    brw_invoice_lines += y
                        # if len(brw_invoice_lines) <= 1:
                        #     raise ValidationError(_("No hay nada que reconciliar para documento %s") % (brw_each.name,))
                        # if len(brw_invoice_lines)>1:
                        #     brw_invoice_lines.reconcile()
            # for brw_document_line in brw_each.movement_line_ids:
            #     pass#brw_document_line.action_paid()
            for brw_document in brw_each.payslip_line_ids:
                brw_document.write({"state":'paid'})
            payslip_runs = brw_each.payslip_line_ids.mapped('payslip_run_id')
            if payslip_runs:
                payslip_runs.test_paid()
            brw_each.write({ "state":"approved" })#"move_id":brw_move.id,
        return True

    def __action_approved(self):
        OBJ_MOVE = self.env["account.move"]
        for brw_each in self:
            if not brw_each.payment_journal_id:
                raise ValidationError(_("Debes definir un diario para realizar el Pago"))
            if not brw_each.move_ids:
                raise ValidationError(_("No existen detalle para generar los pagos"))
            vals = {
                    "move_type": "entry",
                    "name": "/",
                    'narration': brw_each.name,
                    'date': brw_each.date_process,
                    'ref': "PAGO DE NOMINA # %s" % (brw_each.id,),
                    'company_id': brw_each.company_id.id,
                    'journal_id': brw_each.payment_journal_id.id,
            }
            line_ids=[(5,)]
            for brw_line in brw_each.move_ids:
                line_ids += [(0, 0, {
                        "name": brw_each.name,
                        'credit': brw_line.credit,
                        'debit': brw_line.debit,
                        'ref': brw_each.name,
                        'account_id': brw_line.account_id.id,
                        'partner_id': brw_line.partner_id and brw_line.partner_id.id or False,
                        'date': brw_each.date_process,
                        "movement_payment_id":brw_line.id
                    })]
            vals["line_ids"] = line_ids
            brw_move = OBJ_MOVE.create(vals)
            brw_move.action_post()
            if brw_move.state != "posted":
                raise ValidationError(
                        _("Asiento contable %s,id %s no fue publicado!") % (brw_move.name, brw_move.id))
            brw_invoice_lines = self.env["account.move.line"]
            for x in brw_move.line_ids:
                if x.debit > 0 and x.amount_residual != 0.00:
                    brw_invoice_lines+=x
                    for brw_movement in brw_each.movement_ids:
                        for y in brw_movement.move_id.line_ids:
                            if y.credit > 0 and y.partner_id == x.partner_id and y.account_id == x.account_id and y.amount_residual != 0.00:
                                brw_invoice_lines += y
                    #####
                    for brw_payslip in brw_each.payslip_ids:
                        for y in brw_payslip.move_id.line_ids:
                            if y.credit > 0 and y.partner_id == x.partner_id and y.account_id == x.account_id and y.amount_residual != 0.00:
                                brw_invoice_lines += y
                    #if len(brw_invoice_lines) <= 1:
                    #    raise ValidationError(_("No hay nada que reconciliar para documento %s") % (brw_each.name,))
                    if len(brw_invoice_lines)>1:
                        brw_invoice_lines.reconcile()
            for brw_document in brw_each.movement_ids:
                brw_document.action_paid()
            for brw_document in brw_each.payslip_ids:
                brw_document.write({"state":'paid'})
            brw_each.write({"move_id":brw_move.id, "state":"approved" })
        return True

    def action_open_payments(self):
        self.ensure_one()
        payments = self.get_full_payments()
        payments_ids = payments.ids + [-1, -1]
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_account_payments_payable"
        )
        action["domain"] = [('id', 'in', payments_ids)]
        return action

    def update_lines_ref(self):
        for brw_each in self:
            payments1=brw_each.movement_line_ids.mapped('payment_id')
            payments2 = brw_each.payslip_line_ids.mapped('payment_id')
            payments=payments1+payments2
            if payments:
                i=1
                for brw_payment in payments:
                    if brw_payment.bank_reference is None or not brw_payment.bank_reference or brw_payment.bank_reference=="":
                        updated_ref="%s" % (brw_each.bank_reference,)
                        brw_payment.write({"bank_reference":updated_ref})
                    i+=1

    def write(self, vals):
        value= super(HrEmployeePayment,self).write(vals)
        if "bank_reference" in vals:
            self.update_lines_ref()
        return value

    def action_reversed_states(self):
        for brw_each in self:
            movement_line_ids = brw_each.movement_line_ids
            if movement_line_ids:
                for brw_movement_line in movement_line_ids:
                    if brw_movement_line.payment_id:
                        if brw_movement_line.payment_id.state!='posted' or brw_movement_line.payment_id.reversed_payment_id:
                            brw_movement_line.write({"state":"approved"})
            ######################################################
            payslip_line_ids = brw_each.payslip_line_ids
            if payslip_line_ids:
                for brw_payslip in payslip_line_ids:
                    if brw_payslip.payment_id:
                        if brw_payslip.payment_id.state != 'posted' or brw_payslip.payment_id.reversed_payment_id:
                            brw_payslip.write({"state": "done"})
            payslip_runs = brw_each.payslip_line_ids.mapped('payslip_run_id')
            if payslip_runs:
                payslip_runs.test_paid()
            brw_each.write({"state":"sended"})
            ##REVERSAR COTIZACION

        return True

    def get_full_payments(self):
        payments = self.movement_line_ids.mapped('payment_id')
        payments += payments.mapped('reversed_payment_id')

        payments2 = self.payslip_line_ids.mapped('payment_id')
        payments += payments2.mapped('reversed_payment_id')
        return payments

    def get_type_documents(self):
        movements=self.mapped('movement_ids.type')
        lst=movements
        if self.payslip_ids:
            lst.append('payslip')
        return lst
