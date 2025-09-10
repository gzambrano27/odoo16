# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import StringIO
import csv
import openerp.addons.decimal_precision as dp
import base64
import urllib
from datetime import datetime, date, time, timedelta
from stdnum.do import cedula
import pandas as pd
from xlwt import *
from pandas import DataFrame
import io
import xlsxwriter

# class archivo_cheques_multi_line(models.TransientModel):
#     _name = 'archivo.cheques.posf.line.file'
#     _description = 'Archivo Cheques Posfechados Detalle'
# 
#     archivo_id = fields.Many2one('archivo.cheques.posfechados', string='Reports')
#     semana = fields.Char('Semana')
#     journal = fields.Char('Diario')
#     partner = fields.Char('Proveedor')
#     fecha_pago = fields.Date('Fecha Pago')
#     num_cheque = fields.Char('Numero Cheque')
#     valor = fields.Float('Valor')
   
    
class WizardBiometricoFileReport(models.TransientModel):
    _name = 'archivo.cheques.posfechados'
    _description = 'Archivo Cheques Posfechados'
    
    @api.model
    def _get_anio(self):
        currentDateTime = datetime.now()
        date = currentDateTime.date()
        year = date.year
        print year
        return self.env['registro.anio.exportacion'].search([('name','=',str(year))]).id
    
    anio = fields.Many2one('registro.anio.exportacion', 'Anio', store=True, default=_get_anio)
    semana_desde = fields.Many2one('periodo.exportacion', 'Semana Desde')
    semana_hasta = fields.Many2one('periodo.exportacion', 'Semana Hasta')
    
    file_output = fields.Binary(string="File Output", readonly=True, help='Output file in xlsx format')
    file_name = fields.Char(string='File Name', invisible=True)
    
    def export_csv(self):
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read([ 'anio','semana_desde','semana_hasta'])[0]
        
        anio =  data['form'].get('anio')
        semana_desde =  data['form'].get('semana_desde')
        semana_hasta =  data['form'].get('semana_hasta')
        #print anio[1], semana_desde[1],semana_hasta[1]
        if semana_hasta[0]<semana_desde[0]:
            raise UserError(_("La semana hasta no debe ser menor que la semana desde!!"))
        self.env.cr.execute("""select semana,
                            j.name diario,
                            (select name from res_partner x where x.id = p.partner_id )proveedor,
                            p.payment_date fecha_pago,
                            p.check_number numero_cheque,
                            p.amount valor
                            from account_payment p
                            inner join account_journal j on j.id = p.journal_id
                            where tipo_cheque = 'posfechado'
                            and check_number is not null
                            and p.state!='cancel'
                            and semana between '"""+str(semana_desde[1])+"""' and '"""+str(semana_hasta[1])+"""'
                            and to_char(payment_date,'YYYY') = '"""+str(anio[1])+"""'""")
        
        path = 'archivo_cheques_posfechados_'+str(semana_desde[1])+'_'+str(semana_hasta[1])+'.xlsx'

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        
        format1 = workbook.add_format({'font_color': 'yellow','color':'yellow' ,'bg_color': 'black','align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Calibri', 'font_size': 10, 'bold': True})
        format2 = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_name': 'Calibri', 'font_size': 10, 'bold': False})
        row_count = 0
        worksheet.write(row_count,0, 'SEMANA', format1)
        worksheet.write(row_count,1, 'DIARIO', format1)
        worksheet.write(row_count,2, 'PROVEEDOR', format1)
        worksheet.write(row_count,3, 'FECHA PAGO', format1)
        worksheet.write(row_count,4, 'NUMERO CHEQUE', format1)
        worksheet.write(row_count,5, 'VALOR', format1)
       
        row_count = row_count + 1
        for x in self.env.cr.dictfetchall():
            worksheet.write(row_count,0, x['semana'], format2)
            worksheet.write(row_count,1, x['diario'], format2)
            worksheet.write(row_count,2, x['proveedor'], format2)
            worksheet.write(row_count,3, x['fecha_pago'], format2)
            worksheet.write(row_count,4, x['numero_cheque'], format2)
            worksheet.write(row_count,5, x['valor'], format2)
          
            row_count = row_count + 1

        form_res = self.env['ir.model.data'].get_object_reference('account_payment_file', 'message_warning_informe_chqpost_view')
        form_id = form_res and form_res[1] or False
        
        
        workbook.close()
        output.seek(0)
        
        self.write({'file_output': base64.b64encode(output.read()), 'file_name': path})
        
        return {
            'name':_("Mensaje"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'archivo.cheques.posfechados',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
             'views': [(form_id, 'form')],
            'target': 'new',
            "res_id":self.ids[0],
            'context': {}
        }
    
    
#     line_ids = fields.One2many('archivo.cheques.posf.line.file','archivo_id', readonly=True, string='Registros', default=lambda self: self._get_payments())
# 
#     csv_export_file = fields.Binary('CSV File')
#     csv_export_filename = fields.Char('CSV Filename', size=50, readonly=True)
#     
#     def _get_payments(self):
#         return self.datos_archivo_biometrico()
#        
#     @api.model
#     def datos_archivo_biometrico(self):
#         
#         context = dict(self._context or {})
#         active_model = context.get('active_model')
#         active_ids = context.get('active_ids')
#         id_wizard = context.get('banco')
#         
#         self.env['archivo.cheques.posfechados'].browse(id_wizard).write({'line_ids':[]})
#         
#         if not active_model or not active_ids:
#             raise UserError(_('Programmation error: wizard action executed without active_model or active_ids in context.'))
#         if active_model != 'account.payment':
#             raise UserError(_('Programmation error: the expected model for this action is "account.payment". The provide one is "%d".') %active_model)
# 
#         payments = self.env[active_model].browse(active_ids)
#                 
#         reg_lines = [ ]
#         if self.line_ids:
#             for x in self.line_ids:
#                 x.unlink()
#         for p in payments: 
#             reg_lines.append([0,0,{
#                 'archivo_id': p.id,
#                 'semana':p.semana,
#                 'journal':p.journal_id.name,
#                 'partner':p.partner_id.name,
#                 'fecha_pago':p.payment_date,
#                 'num_cheque':p.check_number,
#                 'valor':p.amount
#             }])                    
#         self.env['archivo.cheques.posfechados'].browse(id_wizard).write({'line_ids':reg_lines})
#         return reg_lines
# 
#     def export_xls(self):
#         #limpiamos la tabla
#         tabla_datos = self.datos_archivo_biometrico()
#         # Generate the CSV file
#         row_count = 0
#         writer = pd.ExcelWriter('/tmp/archivo_posfechados.xlsx', engine='xlsxwriter')
#         workbook = writer.book
# 
#         df = DataFrame()
#         df.to_excel(writer, "Cheques Posfechados", startrow=row_count, startcol=0, index=False)
#         worksheet = writer.sheets['Cheques Posfechados']
#         
#         format1 = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': True})
#         format11 = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False})
#         worksheet.write(row_count,0, u'Semana', format1)
#         worksheet.write(row_count,1, u'Diario de Pago', format1)
#         worksheet.write(row_count,2, 'Proveedor', format1)
#         worksheet.write(row_count,3, 'Fecha Pago', format1)
#         worksheet.write(row_count,4, u'# Cheque', format1)
#         worksheet.write(row_count,5, 'Valor', format1)
#         
#         workbook.formats[0].set_font_size(12)
#         
#         format4 = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'bold': False})
#         merge_format = workbook.add_format({
#             'bold': 1,
#             'border': 1,
#             'font_size': 12,
#             'align': 'center',
#             'valign': 'vcenter',
#             'fg_color': 'white'
#         })
#         
#         merge_format1 = workbook.add_format({
#             'bold': 1,
#             'border': 1,
#             'font_size': 12,
#             'align': 'center',
#             'valign': 'vcenter',
#             'fg_color': 'white'
#         })
#         
#         row_d = 1
#         for x in self.line_ids:
#             worksheet.write(row_d,0, x.semana, format11)
#             worksheet.write(row_d,1, x.journal, format11)
#             worksheet.write(row_d,2, x.partner, format11)
#             worksheet.write(row_d,3, x.fecha_pago, format11)
#             worksheet.write(row_d,4, x.num_cheque, format11)
#             worksheet.write(row_d,5, x.valor, format11)
#             
#             row_d = row_d + 1
#         writer.save()
#         
#         
#         PREVIEW_PATH = '/tmp/archivo_posfechados.xlsx'
#         encoded_string = ""
#         with open(PREVIEW_PATH, "rb") as image_file:
#             encoded_string = base64.b64encode(image_file.read())
#         
#         self.csv_export_file = encoded_string
#         self.write({
#                 'csv_export_file': encoded_string,
#                 'csv_export_filename': 'archivo_posfechados.xlsx',
#             })
#         
#         file_url = '/web/content?' + urllib.urlencode(dict(
#             model = self._name,
#             field = 'csv_export_file',
#             filename_field = 'csv_export_filename',
#             id = self.id,
#             download = True,
#             filename = self.csv_export_filename,
#             ))
# 
#         return {
#             'type': 'ir.actions.act_url',
#             'url': file_url,
#             'target': 'new'
#         }

        
        
