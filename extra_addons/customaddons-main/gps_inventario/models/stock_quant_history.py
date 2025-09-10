# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models, _


class StockQuantHistory(models.Model):
    _name = "stock.quant.history"
    description="Historial de Stock"

    date=fields.Char("Fecha",required=True)
    company_id = fields.Many2one("res.company", "Compañía", required=True)
    currency_id = fields.Many2one(related="company_id.currency_id",store=False,readonly=True)
    product_id=fields.Many2one("product.product","Producto",required=True)
    warehouse_id = fields.Many2one("stock.warehouse", "Bodega", required=False)
    location_id = fields.Many2one("stock.location", "Ubicacion", required=True)
    quantity=fields.Float("Cantidad",required=False,default=0.00)
    price_unit = fields.Float("Precio Unitario", required=False, default=0.00,digits=(16,8))
    cost = fields.Float("Costo", required=False, default=0.00, digits=(16, 8))

    _rec_name="date"

    _order="date asc,company_id asc,product_id asc"

    @api.model
    def update_stock_history(self):
        last_companies=self.env["res.company"].sudo().search([])
        for brw_company in last_companies:
            srch_product=self.env["product.product"].sudo().search(['|',('company_id','=',False),
                                                                    ('company_id','=',brw_company.id),
                                                                    ('detailed_type','=','product')
                                                                    ])
            srch_warehouse= self.env["stock.warehouse"].sudo().search(['|', ('company_id', '=', False),
                                                                      ('company_id', '=', brw_company.id)])

            self._cr.execute("""select sl.id, sl.location_id 

                from stock_location sl 
                inner join stock_warehouse wh on wh.id=sl.warehouse_id
            	inner join stock_location slv on slv.id=sl.location_id
                where sl.usage='internal' and slv.usage='view'
                and wh.company_id=%s and wh.id in %s""", (brw_company.id, tuple(srch_warehouse.ids)))

            location_results=self._cr.fetchall()
            location_ids=[*dict(location_results)]
            location_ids+=[-1,-1]

            date_to =fields.Date.context_today(self)
            product_ids=srch_product and srch_product.ids or []
            result=self.env["stock.quant"].sudo().search([('product_id','in',product_ids),
                                                          ('company_id','=',brw_company.id)
                                                          ])
            OBJ_HISTORY=self.env["stock.quant.history"].sudo()
            srch_product_quant=OBJ_HISTORY.search([
                ('company_id','=',brw_company.id),
                ('date','=',date_to)
            ])
            if srch_product_quant:
                srch_product_quant.unlink()
            if result:
                for each_result in result:
                    brw_product=each_result.product_id#self.env["product.product"].sudo().browse(each_result["product_id"])
                    brw_location = each_result.location_id#self.env["stock.location"].sudo().browse(each_result["location_id"])
                    if brw_location.usage=='internal':
                        OBJ_HISTORY.create({
                            'date':date_to,
                            'company_id':brw_company.id,
                            'product_id':brw_product.id,
                            'warehouse_id':brw_location.warehouse_id and brw_location.warehouse_id.id or False,
                            'location_id':brw_location.id,
                            'quantity':each_result.quantity,
                            'price_unit':brw_product.list_price,
                            'cost': brw_product.standard_price,
                        })
            #####
            OBJ_COST_HISTORY=self.env["stock.cost.history"].sudo()
            srch_product_cost = OBJ_COST_HISTORY.search([
                ('company_id', '=', brw_company.id)
            ])
            if srch_product_cost:
                srch_product_cost.unlink()
            self._cr.execute(""";WITH variables AS (
    SELECT %s::INTEGER[] AS company_ids,
           ARRAY[]::INTeger[] AS product_ids
) ,
valoracion_ini as ( 
     SELECT 
         svl.company_id,
        svl.product_id, 
		svl.quantity,
        sm.date::date as date,
        sm.date AS fecha_hasta, 
        svl.unit_cost,
		(case when(svl.quantity!=0.00) then svl.value/svl.quantity else 0.00 end ) as cost_unit_compute,
        (LAG(DATE(sm.date), 1, '2019-12-31') OVER (PARTITION BY svl.product_id ORDER BY DATE(sm.date))+ INTERVAL '1 DAY')::date AS fecha_Desde
    FROM stock_valuation_layer svl
	inner join variables on svl.company_id=ANY(variables.company_ids)  
				AND (
         (
            array_length(variables.product_ids, 1) > 0 AND svl.product_id = ANY(variables.product_ids))
            OR (array_length(variables.product_ids, 1) IS NULL OR array_length(variables.product_ids, 1) = 0
          )
        )
    INNER JOIN stock_move sm ON sm.id = svl.stock_move_id
    WHERE sm.date = (
            SELECT MAX(sm2.date)
            FROM stock_move sm2
            INNER JOIN stock_valuation_layer svl2 ON sm2.id = svl2.stock_move_id
			inner join variables on svl2.company_id=ANY(variables.company_ids) 
					AND (
         (
            array_length(variables.product_ids, 1) > 0 AND svl2.product_id = ANY(variables.product_ids))
            OR (array_length(variables.product_ids, 1) IS NULL OR array_length(variables.product_ids, 1) = 0
          )
        )
            WHERE svl2.product_id = svl.product_id
                AND svl2.company_id = svl.company_id
                AND DATE(sm2.date) = DATE(sm.date)
        )
),costeos as (
	SELECT 
		  company_id,
		  product_id,
		  fecha_Desde,
		  fecha_hasta,
		  -- Movimiento: la cantidad (positivo para entrada, negativo para salida)
		  quantity AS movimiento,
		  cost_unit_compute,
		  -- Valor del movimiento: cantidad x costo unitario de la transacción
		  quantity * cost_unit_compute AS valor_movimiento,
		  -- Saldo acumulado de cantidad
		  SUM(quantity) OVER (PARTITION BY product_id ORDER BY fecha_hasta, fecha_Desde) AS saldo_cantidad,
		  -- Saldo acumulado de valor
		  SUM(quantity * cost_unit_compute) OVER (PARTITION BY product_id ORDER BY fecha_hasta, fecha_Desde) AS saldo_valor,
		  -- Costo promedio del saldo (si el saldo de cantidad es 0, se evita la división)
		  CASE 
		    WHEN SUM(quantity) OVER (PARTITION BY product_id ORDER BY fecha_hasta, fecha_Desde) <> 0
		    THEN SUM(quantity * cost_unit_compute) OVER (PARTITION BY product_id ORDER BY fecha_hasta, fecha_Desde) /
		         SUM(quantity) OVER (PARTITION BY product_id ORDER BY fecha_hasta, fecha_Desde)
		    ELSE 0
		  END AS costo_promedio_saldo
		FROM valoracion_ini
		ORDER BY date, fecha_Desde--fecha_hasta
),
valoracion as (
    SELECT company_id,product_id, fecha_desde::date AS fecha_desde, 
		fecha_hasta::date AS fecha_hasta,  costo_promedio_saldo as cost_unit,movimiento,cost_unit_compute 
    FROM costeos
)

select * from valoracion""", ([brw_company.id], ))
            result_cost=self._cr.dictfetchall()
            if result_cost:
                for each_result_cost in result_cost:
                    OBJ_COST_HISTORY.create({
                        "company_id":each_result_cost["company_id"],
                        "product_id": each_result_cost["product_id"],
                        "date_from": each_result_cost["fecha_desde"],
                        "date_to": each_result_cost["fecha_hasta"],
                        "cost": each_result_cost["cost_unit"],
                        "qty": each_result_cost["movimiento"],
                        "value": each_result_cost["cost_unit_compute"]
                    })
        return True


class StockCostHistory(models.Model):
    _name = "stock.cost.history"
    description="Historial de Costos"

    date_from = fields.Char("Desde", required=True)
    date_to=fields.Char("Hasta",required=True)
    company_id = fields.Many2one("res.company", "Compañía", required=True)
    currency_id = fields.Many2one(related="company_id.currency_id",store=False,readonly=True)
    product_id=fields.Many2one("product.product","Producto",required=True)
    qty = fields.Float("Cantidad", required=False, default=0.00, digits=(16, 2))
    value = fields.Float("Valor", required=False, default=0.00, digits=(16, 8))
    cost = fields.Float("Costo", required=False, default=0.00, digits=(16, 8))

    _rec_name="date_from"

    _order="company_id asc,product_id asc,date_from asc"