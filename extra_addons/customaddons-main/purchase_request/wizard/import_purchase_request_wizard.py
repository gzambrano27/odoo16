from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import pandas as pd

class ImportPurchaseRequestWizard(models.TransientModel):
    _name = 'import.purchase.request.wizard'
    _description = 'Importador de Requisiciones de Compra'

    file = fields.Binary(string="Archivo Excel", required=True)
    filename = fields.Char(string="Nombre del archivo")

    def action_import(self):
        if not self.file:
            raise UserError("Debe cargar un archivo Excel.")

        file_content = base64.b64decode(self.file)
        df = pd.read_excel(io.BytesIO(file_content), sheet_name='Requisiciones')

        grouped = df.groupby('name')
        created_requests=[]
        for name, lines in grouped:
            first = lines.iloc[0]
            request = self.env['purchase.request'].create({
                #'name': name if name != 'New' else False,
                'origin': first.get('origin'),
                'description': first.get('description'),
                'requested_by': self._find_user(first.get('requested_by')).id,
                'priority': str(int(first.get('priority'))) if pd.notna(first.get('priority')) else '0',
                'date_start': fields.Date.today(),
            })
            created_requests.append(request.id)
            for _, row in lines.iterrows():
                default_code = str(row['product_id']).strip()
                product = self.env['product.product'].sudo().search([('default_code', '=', default_code)], limit=1)
                #uom = self.env['uom.uom'].search([('name', '=', row['uom'])], limit=1)
                query = """
                    SELECT id FROM uom_uom
                    WHERE name->>%s = %s
                    LIMIT 1
                """
                self.env.cr.execute(query, ('es_EC', row['uom']))
                result = self.env.cr.fetchone()
                if result:
                    uom = self.env['uom.uom'].browse(result[0])

                if not product:# or not uom:
                    raise UserError(f"Producto o UoM no encontrado: {row['product_id']} / {row['uom']}")

                employee_codes = [
                    ('0' + code.strip()) if len(code.strip()) == 9 else code.strip()
                    for code in str(row.get('employees_ids') or '').split(',')
                    if code.strip()
                ]#['0' + code.strip() for code in str(row.get('employees_ids') or '').split(',') if code.strip()]
                employee_ids = self.env['hr.employee'].sudo().search([('identification_id', 'in', employee_codes)])

                if len(employee_codes) != len(employee_ids):
                    raise UserError(f"Algunos empleados no encontrados en: {employee_codes}")
                
                distribution_str = str(row.get('analytic_distribution') or '')
                distribution_dict = {}
                if distribution_str:
                    for part in distribution_str.split('|'):
                        parts = part.split(':', 1)
                        if len(parts) != 2:
                            continue
                        code, percent_str = parts
                        code = code.strip()
                        percent = float(percent_str.strip())

                        account = self.env['account.analytic.account'].sudo().search([('code', '=', code)], limit=1)
                        if not account:
                            raise UserError(f"Cuenta analítica no encontrada: {code}")

                        distribution_dict[account.id] = percent

                self.env['purchase.request.line'].create({
                    'request_id': request.id,
                    'product_id': product.id,
                    'product_qty': row['qty'],
                    'product_uom_id': uom.id,
                    'date_required': row['date_required'],
                    'name': row.get('description') or product.name,
                    'employees_ids': [(6, 0, employee_ids.ids)],
                    'analytic_distribution': distribution_dict,
                    'un_solo_custodio':row['un_solo_custodio'],
                })

        # Redireccionar al final
        if len(created_requests) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Requisición de Compra',
                'view_mode': 'form',
                'res_model': 'purchase.request',
                'res_id': created_requests[0],
                'target': 'current',
            }
        elif created_requests:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Requisiciones de Compra',
                'view_mode': 'tree,form',
                'res_model': 'purchase.request',
                'domain': [('id', 'in', created_requests)],
                'target': 'current',
            }

    def _find_user(self, login):
        user = self.env['res.users'].search([('login', '=', login)], limit=1)
        if not user:
            raise UserError(_("Usuario no encontrado: %s") % login)
        return user
