from odoo import models, fields, _
from odoo.exceptions import UserError
import base64
import io
from datetime import datetime
import pandas as pd

class WizardImportStockValuation(models.TransientModel):
    _name = 'wizard.import.stock.valuation'
    _description = 'Importar líneas de stock.valuation.layer desde Excel'

    file = fields.Binary(string="Archivo Excel", required=True)
    filename = fields.Char(string="Nombre del archivo")

    def action_import(self):
        try:
            df = pd.read_excel(io.BytesIO(base64.b64decode(self.file)))
        except Exception as e:
            raise UserError(_("Error leyendo el archivo Excel: %s") % e)

        required_cols = ['Item', 'Costo unitario', 'AJUSTAR CANTIDAD', 'Suma de Valor total', 'Descripcion']
        for col in required_cols:
            if col not in df.columns:
                raise UserError(_("Falta la columna requerida: %s") % col)

        StockValuation = self.env['stock.valuation.layer']
        Product = self.env['product.product']

        insertados = 0
        for index, row in df.iterrows():
            default_code = str(row['Item']).strip()
            cost = float(row['Costo unitario'])
            qty = float(row['AJUSTAR CANTIDAD'])
            value = float(row['Suma de Valor total'])
            desc = str(row['Descripcion']).strip()
            company = row['company_id']
            product = Product.search([('default_code', '=', default_code)], limit=1)
            if not product:
                raise UserError(_("No se encontró el producto con código: %s") % default_code)

            StockValuation.create({
                'product_id': product.id,
                'quantity': qty,
                'unit_cost': cost,
                'value': value,
                'description': desc,
                'create_date': fields.Datetime.now(),
                'write_date': fields.Datetime.now(),
                'company_id': company,
            })
            insertados += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Importación completada"),
                'message': _("%s registros importados correctamente." % insertados),
                'type': 'success',
                'sticky': False,
            }
        }