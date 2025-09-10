from odoo import fields, models, api, _
from odoo.exceptions import UserError
import odoorpc

from odoo import models, api

class PurchaseOrderCopy(models.Model):
    _name = 'purchase.order.copy'
    _description = 'Copy Purchase Orders from One Database to Another'

    @api.model
    def copy_purchase_orders(self, origin_host, origin_db, origin_user, origin_password, destination_host, destination_db, destination_user, destination_password, objeto, fecha_desde, fecha_hasta):
        # Conexión a la base de datos de origen
        origin_db_conn = odoorpc.ODOO(origin_host, port=8069)
        origin_db_conn.login(origin_db, origin_user, origin_password)

        # Conexión a la base de datos de destino
        destination_db_conn = odoorpc.ODOO(destination_host, port=8069)
        destination_db_conn.login(destination_db, destination_user, destination_password)

        if objeto=='purchase.order':
            # Obtener las órdenes de compra de la base de datos de origen
            PurchaseOrder = origin_db_conn.env['purchase.order']
            PaymentOrder = origin_db_conn.env['account.payment']
            purchase_orders = PurchaseOrder.search([
                ('state', 'in', ['purchase', 'draft']),
                #('date_order', '>=', fecha_desde.isoformat()),
                #('date_order', '<=', fecha_hasta.isoformat()),
                ('id','in',[1724,1783,2774,2910,3005])
            ])

            # Crear las órdenes de compra en la base de datos de destino
            DestinationPurchaseOrder = destination_db_conn.env['purchase.order']
            DestinationProduct = destination_db_conn.env['product.product']
            DestinationProveedor = destination_db_conn.env['res.partner']
            for order_id in purchase_orders:
                objorder = PurchaseOrder.browse(order_id)
                #pagos = PaymentOrder.search([('purchase_id', '=', int(order_id)),('state', '=', 'posted')])
                #verifico si hay pagos
                # det_pay = []
                # print(objorder.payment_ids)
                # for pay in objorder.payment_ids:
                #     det_pay.append([0, 0, {
                #         'date_planned': pay.date,
                #         'pay_amount': pay.amount
                #     }])
                # Construir líneas de la orden de compra
                det_oc = []
                for line in objorder.order_line:
                    print(line.product_id.default_code)
                    proddest = DestinationProduct.search([('referencia_anterior','=',line.product_id.default_code)])
                    det_oc.append([0, 0, {
                        'name': line.name,
                        'product_qty': line.product_qty,
                        'price_unit': line.price_unit,
                        'display_type': line.display_type,
                        'product_uom': 1,#line.product_uom.id,
                        'product_id': proddest[0] if proddest else 10,#line.product_id.id,
                    }])

                # Valores para la cabecera de la orden de compra
                partner_dest = DestinationProveedor.search([('vat','=',objorder.partner_id.vat)])
                values_cab = {
                    'partner_id': partner_dest[0] if partner_dest else 1,#27,#objorder.partner_id.id,
                    'date_order': objorder.date_order.strftime('%Y-%m-%d %H:%M:%S'),
                    'company_id': 2 if objorder.company_id.id == 5 else (3 if objorder.company_id.id == 6 else 1),
                    'date_planned': objorder.date_planned.strftime('%Y-%m-%d %H:%M:%S'),
                    'notes': f'Proceso migrado basado en copia de OC NG {objorder.name}',
                    'orden_compra_anterior': objorder.name,
                    'order_line': det_oc,
                    #'account_payment_ids':det_pay
                }

                # Crear la orden de compra en la base de datos de destino
                DestinationPurchaseOrder.create(values_cab)

            return len(purchase_orders)
    
        if objeto=='account.move':
            # Obtener las órdenes de compra de la base de datos de origen
            AccountMove = origin_db_conn.env['account.move']
            account_moves = AccountMove.search([
                #('state', 'in', ['purchase', 'draft']),
                ('invoice_date', '>=', fecha_desde.strftime('%Y-%m-%d')),
                ('invoice_date', '<=', fecha_hasta.strftime('%Y-%m-%d')),
                ('move_type', '=', 'in_invoice')
            ])

            # Crear las órdenes de compra en la base de datos de destino
            DestinationAccountMove = destination_db_conn.env['account.move']

            for order_id in account_moves:
                objorder = AccountMove.browse(order_id)

                # Construir líneas de la orden de compra
                det_oc = []
                for line in objorder.invoice_line_ids:
                    det_oc.append([0, 0, {
                        'name': line.name,
                        'product_qty': line.product_qty,
                        'price_unit': line.price_unit,
                        'display_type': line.display_type,
                        'product_uom': 1,#line.product_uom.id,
                        'product_id': 1,#line.product_id.id,
                    }])

                # Valores para la cabecera de la orden de compra
                values_cab = {
                    'partner_id': 27,#objorder.partner_id.id,
                    'invoice_date': objorder.invoice_date.strftime('%Y-%m-%d'),
                    'company_id': 2 if objorder.company_id.id == 5 else (3 if objorder.company_id.id == 6 else 1),
                    'notes': f'Proceso migrado basado en copia de OC NG {objorder.name}',
                    'orden_compra_anterior': objorder.name,
                    'order_line': det_oc,
                }

                # Crear la orden de compra en la base de datos de destino
                DestinationAccountMove.create(values_cab)

            return len(account_moves)