import base64
import io
import pandas as pd
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class LoadInitialBalanceWizard(models.TransientModel):
    _name = 'load.initial.balance.wizard'
    _description = 'Wizard para cargar saldos iniciales desde Excel'

    file_data = fields.Binary(string="Archivo Excel", required=True)
    file_name = fields.Char(string="Nombre del Archivo")

    def _process_file(self, file_content):
        """Leer y procesar el archivo Excel."""
        try:
            decoded_file = base64.b64decode(file_content)
            file = io.BytesIO(decoded_file)
            df = pd.read_excel(file)

            required_columns = {'account_id', 'name', 'debit', 'credit','journal_id','date','partner_id'}
            if not required_columns.issubset(df.columns):
                raise UserError(_("El archivo debe contener las columnas: %s") % ", ".join(required_columns))

            df['debit'] = pd.to_numeric(df['debit'], errors='coerce').fillna(0.0)
            df['credit'] = pd.to_numeric(df['credit'], errors='coerce').fillna(0.0)

            return df.to_dict('records')
        except Exception as e:
            raise UserError(_("Error al procesar el archivo: %s") % str(e))

    def action_import_initial_balance(self):
        """Crear un único asiento contable con todas las líneas."""
        if not self.file_data:
            raise UserError(_("Por favor, suba un archivo."))

        lines_data = self._process_file(self.file_data)

        journal = self.env['account.journal'].search([('name', '=', 'Saldos Iniciales')], limit=1)
        if not journal:
            raise UserError(_("No se encontró el diario 'Saldos Iniciales'."))

        move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'line_ids': [],
        }

        debit_total, credit_total = 0.0, 0.0
        for line in lines_data:
            account = self.env['account.account'].browse(line['account_id'])
            if not account:
                raise UserError(_("No se encontró la cuenta con ID %s.") % line['account_id'])

            move_line_vals = {
                'account_id': account.id,
                'name': line['name'],
                'debit': line['debit'],
                'credit': line['credit'],
                'partner_id': line['partner_id'],
            }
            move_vals['line_ids'].append((0, 0, move_line_vals))

            debit_total += line['debit']
            credit_total += line['credit']

        if round(debit_total,2) != round(credit_total,2):
            difference = abs(debit_total - credit_total)
            adjustment_line = {
                'account_id': self.env['account.account'].search([], limit=1).id,
                'name': 'Ajuste automático',
                'debit': difference if debit_total < credit_total else 0.0,
                'credit': difference if debit_total > credit_total else 0.0,
            }
            move_vals['line_ids'].append((0, 0, adjustment_line))

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Asientos Contables'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': move.id,
        }
