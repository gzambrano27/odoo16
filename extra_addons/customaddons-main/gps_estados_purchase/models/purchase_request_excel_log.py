
from odoo import models, fields, api, _
import xlsxwriter
import base64
import io
from datetime import datetime


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    historial_file = fields.Binary("Archivo Historial")
    historial_filename = fields.Char("Nombre Archivo")

    def button_descargar_historial_excel(self):
        print('a')
