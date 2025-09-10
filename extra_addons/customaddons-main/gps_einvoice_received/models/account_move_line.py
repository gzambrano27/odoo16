# coding: utf-8
from odoo import api, fields, models, exceptions, tools, _
from odoo.exceptions import ValidationError

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    locked=fields.Boolean("Bloqueado",default=False)
    imported_code=fields.Char("Codigo Importado")
    imported_description=fields.Char("Descripcion Importado")
    imported_price=fields.Float("Precio Importado",digits=(16,8),default=0.00)
    imported_qty = fields.Char("Cantidad Importada")
    ref2=fields.Char("Referencia 2")

    @api.onchange('product_id')
    def onchange_lock_product_id(self):
        if self.locked:
            self.name=self.imported_description
            self.price_unit=self.imported_price

            