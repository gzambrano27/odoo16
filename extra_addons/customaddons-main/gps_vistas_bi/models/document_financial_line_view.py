from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo import tools

class DocumentFinancialLineView(models.Model):
    _name = 'document.financial.line.view'
    _description = 'Vista de Operaciones financieras'
    _auto = False

    id = fields.Integer(string="ID", readonly=True)

    type = fields.Char(string="Tipo", readonly=True)

    company_id = fields.Many2one("res.company", string="Compañía", readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=False, readonly=True)
    company_name = fields.Char(string="Nombre Compañía", readonly=True)

    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    partner_name = fields.Char(string="Nombre Partner", readonly=True)

    document_id = fields.Many2one("document.financial", string="Documento", readonly=True)
    document_name = fields.Char(string="Nombre Documento", readonly=True)

    date_process = fields.Date(string="Fecha Proceso", readonly=True)
    date_maturity = fields.Date(string="Fecha Vencimiento", readonly=True)

    type_emission = fields.Char(string="Tipo Emisión", readonly=True)
    type_class = fields.Char(string="Clase", readonly=True)

    cuota = fields.Integer(string="Cuota", readonly=True)

    periods = fields.Integer(string="Periodos", readonly=True)
    years = fields.Integer(string="Años", readonly=True)

    global_total = fields.Monetary(string="Total Global", readonly=True)
    global_total_to_paid = fields.Monetary(string="Total Global por Pagar", readonly=True)
    global_total_paid = fields.Monetary(string="Total Global Pagado", readonly=True)

    capital = fields.Monetary(string="Capital", readonly=True)
    interes = fields.Monetary(string="Interés", readonly=True)
    otros = fields.Monetary(string="Otros", readonly=True)

    total = fields.Monetary(string="Total Línea", readonly=True)
    por_pagar = fields.Monetary(string="Por Pagar", readonly=True)
    pagado = fields.Monetary(string="Pagado", readonly=True)

    monto_financiado = fields.Monetary(string="Monto Financiado", readonly=True)
    interes_nominal_anual = fields.Float(string="Interés Nominal Anual (%)", readonly=True)
    tipo_tasa_interes = fields.Selection(
        [("fija", "Fija"), ("variable", "Variable")],
        string="Tipo de Tasa de Interés",
        readonly=True
    )
    porc_comision = fields.Float(string="Porcentaje Comisión", readonly=True)
    seguro_desgravamen = fields.Float(string="Seguro Desgravamen (%)", readonly=True)

    valor_comision = fields.Monetary(string="Valor Comisión", readonly=True)
    valor_interes = fields.Monetary(string="Valor Interés", readonly=True)
    total_seguro_desgravamen = fields.Monetary(string="Total Seguro Desgravamen", readonly=True)
    valor_primera_cuota = fields.Monetary(string="Valor Primera Cuota", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'purchase_order_view')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW document_financial_line_view AS (
                            SELECT
        dbkl.id,
        dbk.type::varchar as type,
        rc.id as company_id,
        rc.name as company_name,

        rp.id as partner_id,
        rp.name as partner_name,

        dbk.id as document_id,
        dbk.name as document_name,	


        dbk.date_process as date_process,
        dbkl.date_process as date_maturity,
        case when (dbk.type='emision') then dbk.type_emission else null end as type_emission,
        case when (dbk.type='emision') then dbk.type_class  else null end as type_class,
        dbkl.quota as cuota,

        dbk.periods,
        dbk.years ,

        dbk.total as global_total,
        dbk.total_to_paid as global_total_to_paid,
        dbk.total_paid as global_total_paid,

        dbkl.payment_Capital  as capital,
        dbkl.payment_interest as interes,
        dbkl.payment_other as otros,

        dbkl.total as total,
        dbkl.total_to_paid as por_pagar,
        dbkl.total_paid as pagado,

        coalesce(dbk.amount,0.00) as monto_financiado,
        coalesce(dbk.percentage_interest,0.00) as interes_nominal_anual,
        dbk.interest_rate_type as tipo_tasa_interes,
        coalesce(dbk.percentage_amortize,0.00) as porc_comision,
        coalesce(dbk.insurance_rate,0.00) as seguro_desgravamen,
        coalesce(dbk.commission_value,0.00) as valor_comision ,
        coalesce(dbk.interest_value,0.00) as valor_interes,
        coalesce(dbk.insurance_value,0.00) as total_seguro_desgravamen,
        coalesce(dbk.first_quota_value,0.00) as valor_primera_cuota

        FROM document_financial dbk
        INNER JOIN document_financial_line dbkl ON dbkl.document_id = dbk.id
        inner join res_company rc on rc.id=dbk.company_id
        inner join res_partner rp on rp.id=dbk.partner_id
        WHERE dbk.state = 'posted' and dbk.internal_type ='out' 

              )              """)