# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

fileO = FileManager()
dateO = DateManager()
calendarO = CalendarManager()
from datetime import datetime, timedelta
import pytz


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    warning_date_advance_payment_message = fields.Text(store=True, readonly=True, tracking=True,
                                                       string="Advertencia Primer Pago",
                                                       compute="_get_warning_date_advance_payment")
    warning_date_advance_payment = fields.Boolean(store=True, readonly=True, tracking=True,
                                                  string="Tiene Advertencia Primer Pago?",
                                                  compute="_get_warning_date_advance_payment")
    payment_request_ids = fields.One2many("account.payment.request", "order_id", "Solicitud de Pago")

    overdue_days = fields.Integer(
        string="Vence en",
        compute="_compute_overdue_days",
        store=False
    )

    purchase_payment_line_ids = fields.One2many('purchase.order.payment.line', 'order_id', 'Pago')
    total_payments_advances = fields.Monetary(compute="_compute_total_payments_advances", store=True, readonly=True,
                                              string="Total Pagado por Anticipos")
    total_dif_payments_advances = fields.Monetary(compute="_compute_total_payments_advances", store=True, readonly=True,
                                                  string="Total por Pagar")

    validate_with_base_amount = fields.Boolean(string="Validar con Base Imponible", default=False,
                                               compute="_get_validata_with_base_imponible")

    total_request_payments = fields.Monetary(compute="_compute_total_request_payments", store=True, readonly=True,
                                             string="Total por Solicitudes")
    total_dif_request_payments = fields.Monetary(compute="_compute_total_request_payments", store=True, readonly=True,
                                                 string="Total Dif. por Solicitudes")

    @api.depends('payment_request_ids', 'payment_request_ids.state', 'payment_request_ids.amount',
                 'payment_request_ids.paid', 'amount_total')
    def _compute_total_request_payments(self):
        DEC = 2
        for brw_each in self:
            total_request_payments = 0.00
            total_dif_request_payments = 0.00
            if brw_each.amount_total > 0.00:
                for brw_request in brw_each.payment_request_ids:
                    if brw_request.state != 'cancelled':
                        if brw_request.state == 'locked':
                            total_request_payments += brw_request.paid
                        else:
                            total_request_payments += brw_request.amount
                total_dif_request_payments = brw_each.amount_total - total_request_payments
            brw_each.total_request_payments = round(total_request_payments, DEC)
            brw_each.total_dif_request_payments = round(total_dif_request_payments, DEC)

    @api.depends('state', 'company_id')
    def _get_validata_with_base_imponible(self):
        for brw_each in self:
            brw_conf = brw_each.company_id.get_payment_conf()
            validate_with_base_amount = brw_conf.validate_with_base_amount
            if validate_with_base_amount:  # es decir calcula a partir de la base imponible
                validate_with_base_amount = (validate_with_base_amount and
                                             brw_each.payment_term_id.validate_with_base_amount)  ##por defecto en verdadero
            brw_each.validate_with_base_amount = validate_with_base_amount  # brw_conf.validate_with_base_amount

    @api.depends('purchase_payment_line_ids',
                 'purchase_payment_line_ids.payment_id.reversed_payment_id',
                 'purchase_payment_line_ids.payment_id.amount',
                 'purchase_payment_line_ids.payment_id.state',
                 'state', 'amount_total', 'amount_untaxed', 'validate_with_base_amount')
    def _compute_total_payments_advances(self):
        DEC = 2
        for brw_each in self:
            total_payments_advances = 0.00
            if brw_each.state in ('purchase', 'done'):
                for brw_order_payment in brw_each.purchase_payment_line_ids:
                    if brw_order_payment.payment_id.state == 'posted' and not brw_order_payment.payment_id.reversed_payment_id:
                        total_payments_advances += brw_order_payment.amount
            # brw_conf = brw_each.company_id.get_payment_conf()
            total = brw_each.amount_total  # brw_each.validate_with_base_amount and brw_each.amount_untaxed or se calculara siempre sobre el total para no exceder el valor
            total_dif_payments_advances = round(total - total_payments_advances, DEC)
            brw_each.total_payments_advances = total_payments_advances
            brw_each.total_dif_payments_advances = round(total_dif_payments_advances, DEC)

    @api.constrains('total_request_payments', 'total_dif_request_payments', 'state')
    def validate_total_request_payments(self):
        for brw_each in self:
            if brw_each.total_dif_request_payments < 0.00 and brw_each.partner_id.ref != 'REL':
                raise ValidationError(
                    _("No puedes solicitar un valor mayor al total de la OC.Solicitado %s contra %s permitido") % (
                        brw_each.total_request_payments, brw_each.amount_total))
        return True

    @api.constrains('total_payments_advances', 'total_dif_payments_advances', 'state')
    def validate_total_payments_advances(self):
        for brw_each in self:
            brw_conf = brw_each.company_id.get_payment_conf()
            if brw_conf.lock_payment_with_base_amount:
                if brw_each.total_dif_payments_advances < 0.00:
                    raise ValidationError(
                        _("No puedes pagar anticipadamente de la OC %s un valor mayor a su total") % (brw_each.name,))
        return True

    @api.model
    def get_date_with_tz(self, current_datetime):
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)

        # Obtener la fecha y hora actual en UTC y convertirla a la zona horaria local
        current_datetime_local = pytz.utc.localize(current_datetime).astimezone(local_tz)
        return current_datetime_local

    @api.depends('date_advance_payment')
    def _compute_overdue_days(self):
        date_cut = fields.Date.context_today(self)
        for record in self:
            overdue_days = 0
            if record.required_advance_payment:
                if record.state in ('done', 'purchase'):
                    date_cut = self.get_date_with_tz(record.date_approve).date()
                date_advance_payment = record.date_advance_payment
                if record.date_advance_first_payment:
                    date_advance_payment = record.date_advance_first_payment
                if date_advance_payment:
                    overdue_days = (date_advance_payment - date_cut).days
            record.overdue_days = overdue_days

    # def obtener_fecha_proximo_dia_sgte(self, fecha_actual, dia_semana,fecha_corte):
    #     while True:
    #         # Agregar el número de días que corresponde
    #
    #         if calendarO.dow(fecha_actual) == dia_semana and fecha_actual==fecha_corte:
    #             return fecha_actual
    #         fecha_final = fecha_actual + timedelta(days=1)
    #         fecha_actual = fecha_final

    def obtener_fecha_proximo_dia(self, fecha_actual, dia_semana):
        while True:
            # Agregar el número de días que corresponde

            if calendarO.dow(fecha_actual) == dia_semana:
                return fecha_actual
            fecha_final = fecha_actual + timedelta(days=1)
            fecha_actual = fecha_final

    def obtener_fecha_dia_anterior(self, fecha_actual, dia_semana):
        while True:
            # Retroceder un día
            if calendarO.dow(fecha_actual) == dia_semana:
                return fecha_actual
            fecha_actual -= timedelta(days=1)

    @api.onchange('company_id', 'date_advance_payment', 'required_advance_payment', 'payment_term_id')
    @api.depends('company_id', 'date_advance_payment', 'required_advance_payment', 'payment_term_id')
    def _get_warning_date_advance_payment(self):
        OBJ_CONFIG = self.env["account.configuration.payment"].sudo()
        OBJ_LEGAL = self.env["calendar.legal.holiday"].sudo()
        for brw_each in self:
            brw_conf = OBJ_CONFIG.search([
                ('company_id', '=', brw_each.company_id.id)
            ])

            # company_name = brw_each.company_id.name
            # raise ValidationError(
            #     _("Por favor, configura las políticas de pago para la compañía '%s' antes de continuar.") % company_name)
            warning_date_advance_payment_message = None
            warning_date_advance_payment = False
            if brw_conf:
                if brw_each.required_advance_payment:
                    if brw_each.date_advance_payment:
                        warning_date_advance_payment_message = "POR POLITICA LOS PAGOS SE REALIZAN LOS %s." % (
                            brw_conf.day_id.name.upper(),)
                        x = CalendarManager()
                        v = x.dow(brw_each.date_advance_payment)
                        if brw_conf.day_id.value == v:
                            nueva_fecha = brw_each.date_advance_payment
                        else:
                            nueva_fecha = self.obtener_fecha_proximo_dia(brw_each.date_advance_payment,
                                                                         brw_conf.day_id.value)
                            warning_date_advance_payment_message += "LA FECHA DE PAGO DEBERIA SER %s." % (nueva_fecha,)
                            warning_date_advance_payment = True
                        dct_holidays = OBJ_LEGAL.get_holiday(nueva_fecha, nueva_fecha)
                        if dct_holidays:
                            brw_holiday = self.env["calendar.holiday"].sudo().browse(dct_holidays["holiday_id"])
                            warning_date_advance_payment_message += "CONSIDERA QUE LA FECHA DE PAGO ES FERIADO(%s)." % (
                                brw_holiday.name.upper(),)
                else:
                    warning_date_advance_payment_message = "POR POLITICA LOS PAGOS SE REALIZAN LOS %s." % (
                        brw_conf.day_id.name.upper(),)

            brw_each.warning_date_advance_payment_message = warning_date_advance_payment_message
            brw_each.warning_date_advance_payment = warning_date_advance_payment

    def validate_request_default_payments(self):
        for order in self:
            if order.warning_date_advance_payment:
                raise ValidationError(
                    _("La orden de compra %s requiere un anticipo, pero la fecha seleccionada no coincide con el día de pago establecido para la compañía %s.") % (
                        order.name, order.company_id.name))
        return True

    def button_control_presupuesto(self):
        """Set the state to 'control_presupuesto'."""
        for order in self:
            if order.state == 'draft':
                order.validate_request_default_payments()
        return super(PurchaseOrder, self).button_control_presupuesto()

    def button_approve(self):
        for order in self:
            order.update_new_date()
        values = super(PurchaseOrder, self).button_approve()
        for order in self:
            if order.state in ('purchase', 'done', 'to_approve'):  ##
                if order.required_advance_payment:
                    if order.date_advance_payment:
                        date_approve = self.get_date_with_tz(order.date_approve).date()
                        if order.date_advance_payment <= date_approve:
                            raise ValidationError(
                                _("No es posible aprobar la orden de compra %s el mismo día del pago de la compañía %s ,si requiere que el pago sea anticipado o inmediato." % (
                                    order.company_id.name, order.name,)))
                order.create_payment_request()
                order.validate_request_default_payments()
        return values

    def button_cancel(self):
        self.validate_cancel_payments()
        values = super(PurchaseOrder, self).button_cancel()
        self.cancel_payments()
        return values

    def validate_cancel_payments(self):
        for brw_each in self:
            if brw_each.total_payments_advances != 0.00:
                raise ValidationError(
                    _("No puedes anular la %s si tiene aplicado al menos un anticipo") % (brw_each.name,))
        return True

    def cancel_payments(self):
        for brw_each in self:
            lines = self.env["account.payment.request"].sudo().search([('order_id', '=', brw_each.id)])
            noupdates = lines.filtered(lambda x: x.state in ('locked', 'done'))
            if noupdates:
                raise ValidationError(_("No puedes anular %s si tiene solicitudes ya procesadas") % (brw_each.name,))
            lines.action_cancelled()
            # if brw_each.total_payments_advances>0.00:
            #    raise ValidationError(_("No puedes anular una OC que tiene pagos ya publicados"))
        return True

    def liberate_requests_payments(self):
        for brw_each in self:
            lines = self.env["account.payment.request"].sudo().search([('order_id', '=', brw_each.id)])
            ####
            lines_locked = lines.filtered(lambda x: x.state in ('confirmed',) and x.paid > 0.00)
            if lines_locked:
                lines_locked.action_locked()

            lines_process = lines.filtered(lambda x: x.state not in ('locked', 'done'))
            if lines_process:
                lines_confirmed = lines_process.filtered(lambda x: x.state in ('confirmed',))  ##confirmed
                if lines_confirmed:  # si esta en alguna documento de pago
                    srch_ids = self.env["account.payment.bank.macro.line"].sudo().search(
                        [('request_id', 'in', lines_confirmed.ids), ('bank_macro_id.state', 'not in', ('cancelled',))])
                    if srch_ids:
                        nocancel_ids = srch_ids.mapped('request_id').ids
                        lines_process = lines_process.filtered(lambda x: x.id not in nocancel_ids)
                if lines_process:
                    lines_process.action_cancelled()

        return True

    def update_new_date(self):
        OBJ_CONFIG = self.env["account.configuration.payment"].sudo()
        DATE_APPROVE = fields.Date.context_today(self)  # order.date_approve.date()
        for order in self:
            if order.required_advance_payment:
                if order.date_advance_payment:
                    if order.date_advance_payment <= DATE_APPROVE:
                        order.date_advance_first_payment = order.date_advance_payment
                        order.message_post(
                            body=_(
                                _("No es posible aprobar la orden de compra %s el mismo día del pago de la compañía %s ,si requiere que el pago sea anticipado o inmediato.Se actualizará a la fecha de pago más cercana." % (
                                    order.name, order.company_id.name,))),
                            message_type="comment",
                            # Usar "comment" para notas o "notification" para notificaciones
                            subtype_xmlid="mail.mt_note"  # "mail.mt_note" indica que es una nota
                        )
                        ###actualiza con fecha a futuro
                        new_date_advance_payment = order.date_advance_first_payment
                        brw_conf = OBJ_CONFIG.search([
                            ('company_id', '=', order.company_id.id)
                        ])
                        nueva_fecha = self.calcular_nueva_fecha(new_date_advance_payment, brw_conf, DATE_APPROVE)
                        requiere_aprobacion = order.requiere_aprobacion
                        order.date_advance_payment = nueva_fecha
                        order.requiere_aprobacion = requiere_aprobacion

    def calcular_nueva_fecha(self, new_date_advance_payment, brw_conf, to_date):
        while new_date_advance_payment <= to_date:
            new_date_advance_payment = new_date_advance_payment + timedelta(days=1)
            new_date_advance_payment = self.obtener_fecha_proximo_dia(new_date_advance_payment,
                                                                      brw_conf.day_id.value)
        return new_date_advance_payment

    def button_confirm(self):
        TODAY = fields.Date.context_today(self)
        for order in self:
            if order.state == 'control_presupuesto':
                order.update_new_date()
            order.validate_request_default_payments()
            if order.required_advance_payment:
                if order.date_advance_payment:
                    if order.date_advance_payment <= TODAY:
                        # print("button_confirm",1)
                        raise ValidationError(
                            _("No es posible aprobar la orden de compra %s el mismo día del pago de la compañía %s o con una fecha inferior a la actual,si requiere que el pago sea anticipado o inmediato." % (
                                order.company_id.name, order.name,)))
        values = super(PurchaseOrder, self).button_confirm()
        for order in self:
            if order.required_advance_payment:
                if order.state in ('purchase', 'done'):
                    if order.date_advance_payment:
                        DATE_APPROVE = self.get_date_with_tz(order.date_approve).date()
                        if order.date_advance_payment <= DATE_APPROVE:
                            # print("button_confirm", 2,DATE_APPROVE,order.date_advance_payment)
                            raise ValidationError(
                                _("No es posible aprobar la orden de compra %s el mismo día del pago de la compañía %s ,si requiere que el pago sea anticipado o inmediato." % (
                                    order.company_id.name, order.name,)))
        self.create_payment_request()
        for order in self:
            if order.state in ('purchase', 'done'):
                order.send_mail_not_partner_bank()
        return values

    def reconcile_automatics(self, invoices):
        OBJ_MACRO = self.env["account.payment.bank.macro"]
        for brw_each in self:
            for brw_purchase_payment_line in brw_each.purchase_payment_line_ids:
                x = brw_purchase_payment_line
                if x.payment_id.state == 'posted' and x.amount_residual != 0.00 and not x.reconciled and x.order_id == brw_each:
                    brw_payment = x.payment_id
                    reconciled = OBJ_MACRO.reconcile_payment_with_invoice_anticipo(brw_payment, invoices)
                    if reconciled:
                        brw_purchase_payment_line.write({
                            "reconciled": True,
                            "reconciled_date": fields.Datetime.now(),
                            "reconciled_user_id": self.env.user.id
                        })

    def __create_payment_request_old(self):
        OBJ_CONFIG = self.env["account.configuration.payment"].sudo()
        for brw_each in self:
            if brw_each.amount_total > 0.00:
                brw_conf = OBJ_CONFIG.search([
                    ('company_id', '=', brw_each.company_id.id)
                ])
                if brw_conf:
                    company_name = brw_each.company_id.name
                    #         _("Por favor, configura las políticas de pago para la compañía '%s' antes de continuar.") % company_name)
                    order_id = brw_each.id
                    if brw_each.state in ('done', 'purchase'):
                        date = fields.Date.context_today(self).strftime('%Y-%m-%d')
                        # print(1,date)
                        self._cr.execute(f"""select po.id as order_id,
                                                case when(ptm.index=1 and {brw_each.required_advance_payment}) then  coalesce(po.date_advance_payment ,'{date}'::date)::date 
                    else (coalesce(po.date_approve,'{date}'::date)::date + PTM.interval_time)::date end as date_maturity,
                                                round(po.to_invoice *ptm.final_amount/100.00,2) AS amount_residual,
                                                ptm.final_amount AS percentage 
                                                from (                                
                                                    select po.id as id ,
                                                            po.date_advance_payment ::DATE as date_advance_payment,
                                                 coalesce(po.date_approve ,'{date}'::date)      ::DATE as date_approve,
                                                            po.payment_Term_id,
                                                      case when({brw_each.validate_with_base_amount}) then sum( 
                                                        (case when(pol.product_qty>0) then 
                                                            pol.price_subtotal /pol.product_qty else 0.00 end) * 
                                                        (pol.product_qty) 

                                                        ) else po.amount_total  end as to_invoice  
                                                    from purchase_order po	
                                                    inner join purchase_order_line pol on po.id=pol.order_id

                                                     where   po.id={order_id}
                                                    group by 
                                                    po.id  ,
                                                            po.date_advance_payment,
                                                            po.date_approve::DATE ,
                                                            po.payment_Term_id,po.amount_total 

                                                ) po 	
                                                inner join (
                                                    SELECT 
                                                    ROW_NUMBER() OVER (PARTITION BY APT.ID ORDER BY CASE 
                                                        WHEN (COALESCE(APTL.DAYS, 0) > 0) THEN (COALESCE(APTL.DAYS, 0) || ' days') 
                                                        WHEN (COALESCE(APTL.MONTHS, 0) > 0) THEN (COALESCE(APTL.MONTHS, 0) || ' months') 
                                                        ELSE '0 days'
                                                    END::INTERVAL ) as index  ,
                                                    APT.ID,
                                                    COALESCE(APTL.MONTHS, 0) AS MONTHS,
                                                    COALESCE(APTL.DAYS, 0) AS DAYS,
                                                    APTL.VALUE,
                                                    case when (APTL.VALUE='balance') then 0 else APTL.VALUE_AMOUNT end as VALUE_AMOUNT ,
                                                    CASE 
                                                        WHEN (COALESCE(APTL.DAYS, 0) > 0) THEN (COALESCE(APTL.DAYS, 0) || ' days') 
                                                        WHEN (COALESCE(APTL.MONTHS, 0) > 0) THEN (COALESCE(APTL.MONTHS, 0) || ' months') 
                                                        ELSE '0 days'
                                                    END::INTERVAL AS interval_time   ,
                                                    round((case when (APTL.VALUE='balance' and (APTL.DAYS==0 or APTL.MONTHS==0 )) then 100.00- (
                                                        SUM(case when (APTL.VALUE='balance') then 0 else APTL.VALUE_AMOUNT end ) OVER (PARTITION BY APT.ID ORDER BY CASE 
                                                        WHEN (COALESCE(APTL.DAYS, 0) > 0) THEN (COALESCE(APTL.DAYS, 0) || ' days') 
                                                        WHEN (COALESCE(APTL.MONTHS, 0) > 0) THEN (COALESCE(APTL.MONTHS, 0) || ' months') 
                                                        ELSE '0 days'
                                                        END::INTERVAL)-(case when (APTL.VALUE='balance') then 0 else APTL.VALUE_AMOUNT end)
                                                    ) else APTL.VALUE_AMOUNT end),2)	 as final_amount
                                                    FROM 
                                                        ACCOUNT_PAYMENT_TERM APT
                                                    INNER JOIN 
                                                        ACCOUNT_PAYMENT_TERM_LINE APTL 
                                                        ON APTL.PAYMENT_ID = APT.ID 
                                                ) ptm on ptm.id=po.payment_Term_id 
 where round(po.to_invoice *ptm.final_amount/100.00,2)!=0.00 """)
                        result = self._cr.dictfetchall()
                        quota = 1
                        payment_request_ids = [(5,)]
                        if brw_each.payment_request_ids:
                            brw_payment_request_ids = brw_each.payment_request_ids.with_context(validate_unlink=False)
                            brw_payment_request_ids.unlink()

                        for each_result in result:
                            srch = self.env["account.payment.request"].search(
                                [('company_id', '=', brw_each.company_id.id),
                                 ('type', '=', 'purchase.order'),
                                 ('type_document', '=', 'quota'),
                                 ('quota', '=', quota),
                                 ('order_id', '=', brw_each.id),
                                 ])
                            if not srch:
                                vals = {
                                    "company_id": brw_each.company_id.id,
                                    "order_id": brw_each.id,
                                    "payment_term_id": brw_each.payment_term_id.id,
                                    "quota": quota,
                                    "date_maturity": each_result["date_maturity"],
                                    "partner_id": brw_each.partner_id.id,
                                    "amount": each_result["amount_residual"],
                                    'amount_original': each_result["amount_residual"],
                                    "state": "draft",
                                    "type": "purchase.order",
                                    'manual_type': "purchase.order",
                                    "description_motive": "CUOTA %s DE %s" % (quota, brw_each.name),
                                    'request_type_id': self.env.ref('gps_bancos.req_type_anticipo_oc').id,
                                    "percentage": (each_result["percentage"] > 100.00) and 100.00 or each_result[
                                        "percentage"],
                                    'document_ref': brw_each.notes or brw_each.ref,
                                }
                                date = self.obtener_fecha_dia_anterior(each_result["date_maturity"],
                                                                       brw_conf.day_id.value)
                                vals["date"] = date
                                vals["is_prepayment"] = (quota == 1 and brw_each.required_advance_payment)
                                payment_request_ids.append((0, 0, vals))
                                quota += 1
                        brw_each.write({"payment_request_ids": payment_request_ids})  # se graban solicitudes
                        brw_request = brw_each.payment_request_ids.filtered(
                            lambda x: x.is_prepayment)  # se busca solo prepagos
                        if brw_request.is_prepayment:
                            brw_request.action_confirmed()  # se autoriza
        return True

    def create_payment_request(self):
        DEC = 2
        OBJ_CONFIG = self.env["account.configuration.payment"].sudo()
        TODAY = fields.Date.context_today(self)
        for brw_each in self:
            if brw_each.amount_total > 0.00:
                brw_conf = OBJ_CONFIG.search([
                    ('company_id', '=', brw_each.company_id.id)
                ])
                if brw_conf:
                    company_name = brw_each.company_id.name
                    #         _("Por favor, configura las políticas de pago para la compañía '%s' antes de continuar.") % company_name)
                    order_id = brw_each.id
                    if brw_each.state in ('done', 'purchase'):
                        date = brw_each.date_advance_payment or fields.Date.context_today(self)  # .strftime('%Y-%m-%d')

                        quota = 1
                        payment_request_ids = [(5,)]
                        if brw_each.payment_request_ids:
                            brw_payment_request_ids = brw_each.payment_request_ids.with_context(validate_unlink=False)
                            brw_payment_request_ids.unlink()

                        currency = brw_each.company_id.currency_id
                        example_amount = brw_each.validate_with_base_amount and brw_each.amount_untaxed or brw_each.amount_total
                        terms = brw_each.payment_term_id._compute_terms(
                            date_ref=date,
                            currency=currency,
                            company=self.env.company,
                            tax_amount=0,
                            tax_amount_currency=0,
                            untaxed_amount=example_amount,
                            untaxed_amount_currency=example_amount,
                            sign=1)
                        for i, info_by_dates in enumerate(
                                brw_each.payment_term_id._get_amount_by_date(terms, currency).values()):
                            date_str = info_by_dates['date']
                            date_maturity = datetime.strptime(date_str, "%d/%m/%Y")
                            # for each_result in result:
                            srch = self.env["account.payment.request"].search(
                                [('company_id', '=', brw_each.company_id.id),
                                 ('type', '=', 'purchase.order'),
                                 ('type_document', '=', 'quota'),
                                 ('quota', '=', quota),
                                 ('order_id', '=', brw_each.id),
                                 ])
                            percentage = round((info_by_dates['amount'] / example_amount) * 100.00, DEC)
                            percentage = percentage >= 100.00 and 100.00 or percentage
                            if not srch:
                                vals = {
                                    "company_id": brw_each.company_id.id,
                                    "order_id": brw_each.id,
                                    "payment_term_id": brw_each.payment_term_id.id,
                                    "quota": quota,
                                    "date_maturity": date_maturity,
                                    "partner_id": brw_each.partner_id.id,
                                    "amount": info_by_dates['amount'],
                                    'amount_original': info_by_dates['amount'],
                                    "state": "draft",
                                    "type": "purchase.order",
                                    'manual_type': "purchase.order",
                                    "description_motive": "CUOTA %s DE %s" % (quota, brw_each.name),
                                    'request_type_id': self.env.ref('gps_bancos.req_type_anticipo_oc').id,
                                    "percentage": percentage,
                                    'document_ref': brw_each.notes or brw_each.partner_ref,
                                }
                                date = date_maturity.date()
                                if date >= TODAY:  # mayor a la fecha actual
                                    date = self.obtener_fecha_dia_anterior(date_maturity,
                                                                           brw_conf.day_id.value)
                                else:
                                    date = self.obtener_fecha_proximo_dia(TODAY,
                                                                          brw_conf.day_id.value)
                                vals["date"] = date
                                vals["is_prepayment"] = (quota == 1 and brw_each.required_advance_payment)
                                payment_request_ids.append((0, 0, vals))
                                quota += 1
                        brw_each.write({"payment_request_ids": payment_request_ids})  # se graban solicitudes
                        brw_request = brw_each.payment_request_ids.filtered(
                            lambda x: x.is_prepayment)  # se busca solo prepagos
                        if brw_request.is_prepayment:
                            brw_request.action_confirmed()  # se autoriza
        return True

    def write(self, vals):
        def test_fields(vals, field_list):
            for each_ky in field_list:
                if each_ky in vals:
                    return True
            return False

        if test_fields(vals, ['payment_term_id', 'date_maturity', ]):
            for brw_each in self:
                l = brw_each.payment_request_ids.filtered(lambda x: x.paid != 0.00)
                if len(l) > 0:
                    raise ValidationError(
                        _("No es posible modificar una Orden de Compra si tiene una solicitud de pago ya procesada."))
        return super(PurchaseOrder, self).write(vals)

    def send_mail_not_partner_bank(self):
        template = self.env.ref('gps_bancos.email_template_partner_no_oc_bank', raise_if_not_found=False)
        for brw_each in self:
            bank_accounts = brw_each.partner_id.bank_ids.filtered(lambda x: x.active)
            if not bank_accounts and template:
                template.send_mail(brw_each.id, force_send=True)
        return True

    def get_mail_bank_alert_not(self):
        self.ensure_one()
        return self.company_id.get_mail_bank_alert_not()