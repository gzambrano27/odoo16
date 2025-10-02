# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo import tools

class PurchaseOrderView(models.Model):
    _name = 'purchase.order.view'
    _description = 'Vista de Ordenes de Compra'
    _auto = False


    id = fields.Integer(string="ID", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    company_name = fields.Char(string="Company Name", readonly=True)
    fecha_aprobacion = fields.Date(string="Fecha Aprobacion", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    partner_name = fields.Char(string="Partner Name", readonly=True)
    product_id = fields.Many2one("product.product", string="Producto", readonly=True)
    producto_dscr = fields.Text(string="Nombre Producto", readonly=True)
    codigo_producto = fields.Char(string="Referencia Interna", readonly=True)
    descripcion_linea = fields.Char(string="Descripcion Linea", readonly=True)
    tipo_costo = fields.Char(string="Tipo Costo", readonly=True)
    precio_subtotal = fields.Monetary(string="Precio Subtotal", readonly=True)
    precio_unitario = fields.Monetary(string="Precio Unitario", readonly=True)
    estado = fields.Char(string="Estado", readonly=True)
    fecha_orden = fields.Date(string="Fecha Orden", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, default=lambda self: self.env.company.currency_id.id)
    rubro = fields.Char(string="Rubro", readonly=True)
    product_qty = fields.Float(string="Cantidad", readonly=True)
    descuento = fields.Float(string="Descuento", readonly=True)
    descuento_presupuesto = fields.Float(string="Descuento Presupuesto", readonly=True)
    cuenta_analitica = fields.Text('Cuenta Analitica', readonly=True)
    val_cuenta_analitica = fields.Float('Valor Cuenta Analitica', readonly=True)
    nombre_cuenta_analitica = fields.Text('Descripcion Cuenta Analitica', readonly=True)
    fecha_anticipo_pago = fields.Date(string="Fecha Ant. Pago", readonly=True)
    payment_term_id = fields.Many2one("account.payment.term", string="Termino de Pago ID", readonly=True)
    nombre_payment_term = fields.Char(string="Descripcion Term. Pago", readonly=True)
    es_importacion = fields.Boolean(string="Es Importacion", readonly=True)
    es_admin = fields.Boolean(string="Es Administrativa", readonly=True)
    es_presidencia = fields.Boolean(string="Es Presidencia", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'purchase_order_view')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW purchase_order_view AS (                            
                SELECT po.id,
                --Fechas
                po.date_order                  AS fecha_orden,
                po.date_approve                AS fecha_aprobacion,
                po.date_advance_payment        AS fecha_anticipo_pago ,
                
                -- Compañía
                rc.id                          AS company_id,
                rc.name                        AS company_name,
                
                -- Partner (Proveedor)
                po.partner_id,
                rp.name                        AS partner_name,
                
                -- Producto y descripción
                pp.id                          AS product_id,
                COALESCE(
                    pt.name::json ->> 'es_EC',
                    pt.name::json ->> 'en_US'
                )                              AS producto_dscr,
                pt.default_code                AS codigo_producto,
                pol.name                       AS descripcion_linea,
                
                -- Datos generales de la orden/línea
                pol.product_qty,
                pol.price_unit                  as precio_unitario,
                pol.price_subtotal              as precio_subtotal,
                pol.discount                    as descuento,
                pol.descuento_presupuesto,
                po.state                        as estado,
                
                -- Datos específicos
                tcos.name                      AS tipo_costo,
                pol.rubro                      AS rubro,
                
                -- Distribución analítica
                dist.key::text                 AS cuenta_analitica,
                dist.value::numeric            AS val_cuenta_analitica,
                aaa.name                       AS nombre_cuenta_analitica,
                
                -- Condiciones de pago
                apt.id                         AS payment_term_id,
                COALESCE(
                    apt.name::json ->> 'es_EC',
                    apt.name::json ->> 'en_US'
                )                              AS nombre_payment_term,
                
                --Flags de control
                po.importacion                  AS es_importacion,
                po.es_admin,
                po.es_presidencia
                
            FROM purchase_order po
            INNER JOIN purchase_order_line pol ON pol.order_id = po.id
            INNER JOIN tipo_costo tcos         ON tcos.id = pol.tipo_costo_id
            INNER JOIN res_company rc          ON rc.id = po.company_id
            INNER JOIN product_product pp      ON pp.id = pol.product_id
            INNER JOIN product_template pt     ON pt.id = pp.product_tmpl_id
            LEFT JOIN LATERAL json_each_text(pol.analytic_distribution::json) AS dist(key, value) ON TRUE
            LEFT JOIN account_analytic_account aaa ON aaa.id::varchar = dist.key::varchar
            LEFT JOIN account_payment_term apt     ON apt.id = po.payment_term_id
            LEFT JOIN res_partner rp               ON rp.id = po.partner_id
            );
        """)

    _order="company_id asc, id desc"