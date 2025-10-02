# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import html

class AccountConfigurationPayment(models.Model):
    _name = 'account.configuration.payment'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Configuraciones de Pagos"

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company
    )
    day_id=fields.Many2one("calendar.day","Dia de Pago",required=True,tracking=True)

    bank_conf_ids=fields.One2many('account.configuration.payment.bank','conf_payment_id','Configuraciones del Banco')
    journal_ids=fields.Many2many('account.journal','account_conf_payment_all_journal_rel','conf_payment_id','journal_id','Diarios',tracking=True)
    active=fields.Boolean("Activo",default=True,tracking=True)

    local_prepayment_account_id=fields.Many2one('account.account','Cuenta de Anticipos Locales',tracking=True)
    exterior_prepayment_account_id = fields.Many2one('account.account', 'Cuenta de Anticipos Exterior',tracking=True)

    validate_with_base_amount=fields.Boolean("Validar con Base Imponible",default=True,tracking=True)
    lock_payment_with_base_amount=fields.Boolean("Bloquear pago con excedente",default=True,tracking=True)

    first_bond_issuance_acct_id=fields.Many2one("account.account","Cuenta Primera Obligacion")
    second_bond_issuance_acct_id = fields.Many2one("account.account", "Cuenta Segunda Obligacion")
    third_bond_issuance_acct_id = fields.Many2one("account.account", "Cuenta Tercera Obligacion")

    int_first_bond_issuance_acct_id = fields.Many2one("account.account", "Cuenta Interés Primera Obligacion")
    int_second_bond_issuance_acct_id = fields.Many2one("account.account", "Cuenta Interés Segunda Obligacion")
    int_third_bond_issuance_acct_id = fields.Many2one("account.account", "Cuenta Interés Tercera Obligacion")

    payment_overdue_interest_acct_id = fields.Many2one("account.account", "Cuenta Interés Mora")
    payment_other_acct_id =  fields.Many2one("account.account", "Cuenta Otros Gastos")

    prestamo_capital_acct_id = fields.Many2one("account.account", "Cuenta Capital Prestamos")
    prestamo_interes_acct_id = fields.Many2one("account.account", "Cuenta Interes Prestamos")
    prestamo_interes_mora_acct_id = fields.Many2one("account.account", "Cuenta Interes Mora")
    prestamo_otros_acct_id = fields.Many2one("account.account", "Cuenta otros Prestamos")

    liquidation_account_id=fields.Many2one("account.account", "Cuenta Liquidacion de Haberes")

    group_by_employee_payment=fields.Boolean('Agrupar Pagos',default=True)

    user_info_report_ids=fields.Many2many('res.users','res_users_info_report_rel','conf_id','user_id','Usuarios Notificados',tracking=True)
    hour_start = fields.Integer('Hora de Inicio', default=8,tracking=True)
    periodicity=fields.Integer('Periocidad',default=6,tracking=True)

    due_days=fields.Integer('Dias de Vencimiento',default=5,tracking=True)

    _rec_name="company_id"

    _check_company_auto = True

    @api.model
    def cron_send_payment_notifications(self,scheduled_hours=[]):
        OBJ_MAIL = self.env["bank.mail.message"]

        now_utc = fields.Datetime.now()  # hora UTC
        now_local = fields.Datetime.context_timestamp(self, now_utc)  # hora local del usuario

        print("UTC:", now_utc)  # ejemplo: 2025-09-08 13:00:00
        print("Local:", now_local)  # ejemplo: 2025-09-08 08:00:00  (si tu zona es UTC-5)

        current_hour = now_local.hour
        today = now_local.date()

        print("Hour:", current_hour)  # 8
        print("Date:", today)  # 2025-09-08

        configs = self.search([('active', '=', True), ('user_info_report_ids', '!=', False)])
        users = configs.mapped('user_info_report_ids')  # traemos todos los usuarios relacionados

        # Calcular intervalos
        #interval = 24 // conf.periodicity
        if not scheduled_hours:
            scheduled_hours = range(0,23)

        if current_hour in scheduled_hours:
            # Verificar si ya existe un mail para este conf en este día y hora

            today_str = today.strftime('%Y-%m-%d')

            for user in users:
                # Crear el name único
                mail_name = "%s,%s,%s::%s" % ('res.users',user.id, today_str, current_hour)

                exists = OBJ_MAIL.search([
                        ('internal_type', '=', 'batch'),
                        ('type', '=', 'res.users'),
                        ('name','=',mail_name),
                        ('internal_id', '=',user.id),
                        #('company_id', '=', user.company_id.id),
                        ('create_date', '>=', fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))),
                        ('create_date', '<=', fields.Datetime.to_string(datetime.combine(today, datetime.max.time()))),
                        ('scheduled_hour', '=', current_hour),  # si agregas este campo técnico
                    ], limit=1)

                if exists:
                    continue  # ya está creado para este intervalo
                configs=configs.filtered(lambda x: user in x.user_info_report_ids)
                if not configs:
                    continue
                company_id=configs.mapped('company_id')
                company_names=company_id.mapped('name')
                emails = [user.email]
                # Quitar duplicados
                unique_emails = list(set(emails))
                if not unique_emails:
                    continue
                # Opcional: convertir en string separado por coma
                emails_string = ','.join(unique_emails)
                # Crear el mensaje
                brw_mail = OBJ_MAIL.create({
                        "internal_type": "batch",
                        "type": self._name,
                        "name":mail_name,
                        "internal_id": user.id,
                        "model_name": "res.users",
                        "description": "PAGOS PROGRAMADOS PARA %s" % ( ",".join(company_names),),
                        "email":emails_string,
                        "partner_id": user.partner_id.id,
                        "company_id": company_id[0].id,
                        "state": "draft",
                        "template_id": self.env.ref('gps_bancos.mail_template_alarma_por_pagar').id,
                        "report_name_ref": None,
                        "scheduled_hour": current_hour,  # campo técnico
                    })

    def _get_query(self,type):
        query_final="select * from resumen order by date_maturity asc"
        if type=='resumen':
            query_final = "select company_name,tipo,sum(amount_residual) as amount_residual from resumen group by company_name,tipo "
        QUERY=f""";WITH VARIABLES AS (
            SELECT %s::DATE + %s::INT AS due_days,
                   %s::INT AS action_move_id,
                   %s::INT AS menu_move_id,
                   %s::INT AS action_order_id,
                   %s::INT AS menu_order_id
        ),resumen as (
        SELECT rc.name as company_name,
               'account.move'::varchar as model_name,    
               am.id,
               aml.id AS move_line_id,
               aml.name AS move_line_dscr,
               COALESCE(aml.date_maturity, am.date) AS date_maturity,
               aml.debit,
               aml.credit,
               am.date AS move_date,
               am.partner_id,
               rp.name AS partner_name,
               rp.vat AS partner_vat,
               am.name AS name,
               am.ref AS ref,
               COALESCE(ABS(aml.amount_residual),0.00) AS amount_residual,
               VARIABLES.action_move_id AS action_id,
               VARIABLES.menu_move_id AS menu_id,
               'DOC. CONTABLE'::varchar as tipo
        FROM account_move am
        INNER JOIN account_move_line aml ON aml.move_id = am.id
        INNER JOIN account_account aa ON aa.id = aml.account_id
                                       AND aa.account_type = 'liability_payable'
        INNER JOIN VARIABLES ON TRUE
        INNER JOIN res_partner rp ON rp.id = COALESCE(aml.partner_id, am.partner_id)
        INNER JOIN res_company rc ON rc.id = am.company_id
        WHERE am.state = 'posted'
          AND am.company_id = ANY(%s)
          AND COALESCE(aml.date_maturity, am.date) <= VARIABLES.due_days
          AND ROUND(aml.amount_residual,2) != 0.00

        UNION
        SELECT rc.name as company_name,
               'purchase.order'::varchar as model_name,
               po.id,
               por.id AS move_line_id,
               por.name AS move_line_dscr,
               por.date_maturity AS date_maturity,
               0.00 as debit,
               por.amount as credit,
               po.date_order::date AS move_date,
               po.partner_id,
               rp.name AS partner_name,

               rp.vat AS partner_vat,
               po.name AS name,
               po.partner_ref AS ref,
               COALESCE(por.pending,0.00) AS amount_residual,
               VARIABLES.action_order_id AS action_id,
               VARIABLES.menu_order_id AS menu_id,
               'ORDEN DE COMPRA'::varchar AS tipo
        FROM purchase_order po
        INNER JOIN VARIABLES ON TRUE
        INNER JOIN account_payment_request por ON por.order_id = po.id
        INNER JOIN res_company rc ON rc.id = po.company_id
        INNER JOIN res_partner rp ON rp.id = po.partner_id
        WHERE por.state IN ('confirmed','done','locked')
          AND po.state in ('purchase','done')
          AND po.company_id = ANY(%s)
          AND COALESCE(por.pending,0.00) != 0.00
              AND COALESCE(por.date_maturity, po.date_order) <= VARIABLES.due_days
          
          )
          
        {query_final}
        """
        return QUERY

    def get_cxp_payments(self,partner_id):
        user=self.env["res.users"].sudo().search([('partner_id','=',partner_id)])
        configs = self.search([('active', '=', True), ('user_info_report_ids', '!=', False), ('user_info_report_ids', 'in', user.ids)])
        all_result=[]
        all_totals=[]
        for config in configs:
            self._cr.execute(self._get_query('all'), (
                fields.Date.context_today(self), config.due_days,
                self.get_ref_id('account.menu_action_move_in_invoice_type'),
                self.get_ref_id('account.action_move_in_invoice_type'),
                self.get_ref_id('purchase.menu_purchase_rfq'),
                self.get_ref_id('purchase.purchase_rfq'),
                [config.company_id.id],  # para account_move
                [config.company_id.id]  # para purchase_order
            ))
            result = self._cr.dictfetchall()
            ############################################################3

            self._cr.execute(self._get_query('resumen'), (
                fields.Date.context_today(self), config.due_days,
                self.get_ref_id('account.menu_action_move_in_invoice_type'),
                self.get_ref_id('account.action_move_in_invoice_type'),
                self.get_ref_id('purchase.menu_purchase_rfq'),
                self.get_ref_id('purchase.purchase_rfq'),
                [config.company_id.id],  # para account_move
                [config.company_id.id]  # para purchase_order
            ))
            #print(self._cr.query)
            result_total = self._cr.dictfetchall()
            #print(result_total)
            all_result+=result
            all_totals += result_total
        print("--------0",{
            "result": all_result,
            "totals": all_totals
        })
        return {
            "result": all_result,
            "totals": all_totals
        }

    def _build_payments_table(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('param.download.bancos.url')
        lines = self.get_cxp_payments()  # tu método que devuelve la lista/dict

        html = """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th>ID</th>
                    <th>Nombre</th>
                    <th>Partner</th>
                    <th>Fecha</th>
                    <th>Vencimiento</th>
                    <th>Crédito</th>
                    <th>Saldo Pendiente</th>
                </tr>
            </thead>
            <tbody>
        """

        for line in lines:
            html += f"""
                <tr>
                    <td>
                        <a href="{base_url}/web#id={line['id']}&model=account.move&view_type=form" target="_blank">
                            {line['id']}
                        </a>
                    </td>
                    <td>{line['name']}</td>
                    <td>{line['partner_name']}</td>
                    <td>{line['move_date']}</td>
                    <td>{line['date_maturity']}</td>
                    <td style="text-align:right;">{line['credit']}</td>
                    <td style="text-align:right;">{line['amount_residual']}</td>
                </tr>
            """

        html += "</tbody></table>"
        return html

    def create_link_amv(self,mv_id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('param.download.bancos.url')
        menu_id = self.env.ref('account.menu_action_move_in_invoice_type').id
        action_id = self.env.ref('account.action_move_in_invoice_type').id
        download_url = f"/web?#id={mv_id}&view_type=form&model=account.move&menu_id={menu_id}&action={action_id}"
        full_url= f"{base_url}{download_url}"
        return full_url

    def get_ref_id(self,ref_name):
        v=self.env.ref(ref_name)
        return v and v.id or 0



    def limpiar_texto(self,valor):
        """Limpia caracteres problemáticos para QWeb/HTML"""
        if not valor:
            return ""
        if not isinstance(valor, str):
            valor = str(valor).replace('/','').replace('>','').replace('<','').replace('&','')
        return html.escape(valor, quote=True)