# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
from werkzeug.wrappers import Response
import os
class PurchaseOrderController(http.Controller):

    @http.route('/gps_purchases/purchase_orders.json', type='http', auth='public', methods=['GET'])
    def get_purchase_orders(self, **post):
        # Obtener las órdenes de compra
        module_root = os.path.dirname(__file__)

        file_path = os.path.join(module_root, 'static', 'files', 'purchase_orders.json')

        companies = request.env['res.company'].search([])
        row = 1
        orders_data=[]
        for company in companies:
            orders = request.env['purchase.order'].sudo().search([('company_id', '=', company.id)])
            tipo_orden = ''
            status_fact = ''
            for record in orders:  # Ejemplo: obtendremos los 10 primeros contactos
                for det in record.order_line:
                    if det.analytic_distribution:
                        first_key = next(iter(det.analytic_distribution))
                        centro_costo = request.env['account.analytic.account'].sudo().browse(int(first_key)).name
                    else:
                        centro_costo = 'No Asignado'
                    if str(record.purchase_order_type) == 'service':
                        tipo_orden = 'Servicio'
                    elif str(record.purchase_order_type) == 'product':
                        tipo_orden = 'Producto'
                    else:
                        tipo_orden = 'Producto y Servicio'
                    if str(record.invoice_status) == 'no':
                        status_fact = 'Nada a Facturar'
                    elif str(record.invoice_status) == 'to invoice':
                        status_fact = 'Facturas en espera'
                    else:
                        status_fact = 'Totalmente Facturado'
                    if str(record.state) == 'draft':
                        estado = 'SdP'
                    elif str(record.state) == 'sent':
                        estado = 'Enviado'
                    elif str(record.state) == 'purchase':
                        estado = 'Orden de Compra'
                    elif str(record.state) == 'done':
                        estado = 'Realizado'
                    elif str(record.state) == 'cancel':
                        estado = 'Cancelado'
                    else:
                        estado = 'Por Aprobar'
                    orders_data.append({
                        'Fecha Creacion':record.create_date.strftime('%Y-%m-%d'),
                        'Fecha Confirmacion':record.date_approve and record.date_approve.strftime('%Y-%m-%d') or None,
                        'Company':record.company_id.name,
                        'Cuenta Analitica':str(centro_costo),
                        'Origen':record.origin,
                        'Solicitante':str(record.solicitante.name),
                        'Comprador':str(record.user_id.name),
                        'Referencia del Pedido':str(record.name),
                        'Proveedor':str(record.partner_id.name),
                        'Estado':str(estado),
                        'Aprobacion Financiero': 'Si' if record.requiere_aprobacion else 'No',
                        'Estado Facturacion':str(status_fact),
                        'Producto':str(det.product_id.name),
                        'Rubro':str(det.rubro),
                        'Descripcion':str(det.name),
                        'Tipo Orden': str(tipo_orden),
                        'Precio Unitario':det.price_unit,
                        'Precio Venta':det.precio_venta,
                        'Descuento':det.discount,
                        'Cantidad':det.product_qty,
                        'Subtotal PSP':(det.product_qty * det.precio_venta),
                        'Base Imponible':det.price_subtotal,
                        'Base Imponible Total':record.amount_untaxed
                    })
                    row += 1
        json_data = json.dumps(orders_data)
        with open(file_path, 'w') as f:  # Abrir en modo escritura ('w')
            f.write(json_data)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                json_data = f.read()
            return Response(
                json_data,
                content_type='application/json',
                headers=[('Content-Disposition', 'attachment; filename="purchase_orders.json"')]
            )
        else:
            return Response("El archivo no existe.", status=404)
