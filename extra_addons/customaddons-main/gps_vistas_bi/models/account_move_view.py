# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo import tools

class AccountMoveView(models.Model):
    _name = 'account.move.view'
    _description = 'Vista de Movimientos Contables'
    _auto = False

    id = fields.Integer(string="Move ID", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    move_type = fields.Char(string="Move Type", readonly=True)
    company_name = fields.Char(string="Company Name", readonly=True)
    journal_name = fields.Char(string="Journal Name", readonly=True)
    name = fields.Char(string="Nombre de asiento", readonly=True)
    ref = fields.Char(string="Ref", readonly=True)
    referencia_pago = fields.Char(string="Referencia Pago", readonly=True)
    fecha_asiento = fields.Date(string="Fecha Asiento", readonly=True)
    fecha_factura = fields.Date(string="Fecha Factura", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    partner_name = fields.Char(string="Partner Name", readonly=True)
    debit = fields.Monetary(string="Debit", readonly=True)
    credit = fields.Monetary(string="Credit", readonly=True)
    amount_residual = fields.Monetary(string="Residual Amount", readonly=True)
    narration = fields.Text(string="Narration", readonly=True)
    product_id = fields.Many2one("product.product", string="Product ID", readonly=True)
    producto_dscr = fields.Char(string="Producto Dscr", readonly=True)
    rfi = fields.Char(string="RFI", readonly=True)
    descripcion_linea = fields.Char(string="Descripcion Linea", readonly=True)
    payment_term_id = fields.Many2one("account.payment.term", string="Termino de Pago ID", readonly=True)
    termino_pago_dscr = fields.Char(string="Descripcion Term. Pago", readonly=True)
    tipo_documento_dscr = fields.Char(string="Tipo Documento Dscr", readonly=True)
    tipo_documento_codigo = fields.Char(string="Tipo Documento Cod", readonly=True)
    invoice_user_name = fields.Char(string="Invoice User Name", readonly=True)
    date_approved = fields.Date(string="Date Approved", readonly=True)
    account_analytic_id = fields.Many2one("account.analytic.account", string="Account Analytic ID", readonly=True)
    account_analytic_name = fields.Char(string="Account Analytic Name", readonly=True)
    quantity = fields.Float(string="Cantidad", readonly=True)
    uom_name = fields.Char(string="UOM Name", readonly=True)
    price_unit = fields.Monetary(string="Precio Unitario", readonly=True)
    tax_base_amount = fields.Monetary(string="Tax Base Amount", readonly=True)
    price_subtotal = fields.Monetary(string="Precio Subtotal", readonly=True)

    account_id = fields.Many2one("account.account", string="Account ID", readonly=True)
    account_name = fields.Char(string="Account Name", readonly=True)
    account_type = fields.Char(string="Account Type", readonly=True)
    

    currency_id = fields.Many2one(
        "res.currency", string="Currency",
        readonly=True, default=lambda self: self.env.company.currency_id.id
    )

    related_partner_id = fields.Many2one("res.partner", string="Partner Relacionado", readonly=True)
    related_partner_name = fields.Char(string="Partner Name Relacionado", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'account_move_view')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW account_move_view AS (
                SELECT am.id,
                    -- Fechas
                    am.date                     AS fecha_asiento,
                    am.invoice_date              AS fecha_factura,
                    am.date_approved,
                    
                    -- Compañía
                    rc.id                       AS company_id,
                    rc.name                     AS company_name,
                    
                    -- Partner
                    rp.id                       AS partner_id,
                    rp.name                     AS partner_name,
                    
                    --Datos generales de asiento
                    am.move_type                AS move_Type,
                    aj.name                     AS journal_name,
                    am.name                     ,
                    am.ref                      ,
                    am.payment_reference        AS referencia_pago,
                    rpu.name                    AS invoice_user_name,
                    am.narration,
                    
                    -- Datos financieros
                    aml.debit,
                    aml.credit,
                    aml.amount_residual,
                    aml.tax_base_amount,
                    aml.price_subtotal,
                    aa.id                       AS account_id,
                    aa.name                     AS account_name,
                    aa.account_type,
                    
                    -- Producto / Línea
                    aml.product_id,
                    COALESCE(
                        pt.name::json ->> 'es_EC',
                        pt.name::json ->> 'en_US'
                    )                           AS producto_dscr,
                    pt.default_code             AS rfi,
                    aml.name                    AS descripcion_linea,
                    aml.quantity,
                    aml.price_unit,
                    COALESCE(
                        uom.name::json ->> 'es_EC',
                        uom.name::json ->> 'en_US'
                    )                           AS uom_name,
                    
                    -- Datos específicos
                    apt.id                      AS payment_term_id,
                    COALESCE(
                        apt.name::json ->> 'es_EC',
                        apt.name::json ->> 'en_US'
                    )                           AS termino_pago_dscr,
                    ldt.name                    AS tipo_documento_dscr,
                    ldt.code                    AS tipo_documento_codigo,
                    
                    -- Analíticas
                    aal.account_id              AS account_analytic_id,
                    aaa.name                    AS account_analytic_name,

					-- Partner Relacionado
                    rpr.id                       AS related_partner_id,
                    rpr.name                     AS related_partner_name
                    
                    
                FROM account_move_line aml
                INNER JOIN account_move am 
                    ON am.id = aml.move_id
                INNER JOIN account_journal aj 
                    ON aj.id = am.journal_id
                INNER JOIN res_company rc 
                    ON rc.id = am.company_id
                LEFT JOIN res_partner rp 
                    ON rp.id = COALESCE(aml.partner_id, am.partner_id, rc.partner_id)
                LEFT JOIN product_product pp 
                    ON pp.id = aml.product_id
                LEFT JOIN product_template pt 
                    ON pt.id = pp.product_tmpl_id
                LEFT JOIN account_payment_term apt 
                    ON apt.id = am.invoice_payment_term_id
                LEFT JOIN l10n_latam_document_type ldt 
                    ON ldt.id = am.l10n_latam_document_type_id
                LEFT JOIN res_users ruc 
                    ON ruc.id = am.invoice_user_id
                LEFT JOIN res_partner rpu 
                    ON rpu.id = ruc.partner_id
                LEFT JOIN account_analytic_line aal 
                    ON aal.move_line_id = aml.id
                LEFT JOIN account_analytic_account aaa 
                    ON aaa.id = aal.account_id
                LEFT JOIN uom_uom uom 
                    ON uom.id = aml.product_uom_id
                LEFT JOIN account_account aa 
                    ON aa.id = aml.account_id

				LEFT JOIN res_partner rpr 
                    ON rpr.id = COALESCE(aa.empresa_relacionada_id,aml.partner_id, am.partner_id, rc.partner_id)


				
                WHERE am.state = 'posted'
              )
        """)

    _order="company_id asc,id desc"