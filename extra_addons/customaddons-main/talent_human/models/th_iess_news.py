from odoo import api, fields, models, tools, netsvc, _

class ThIessNews(models.Model):
    _name="th.iess.news"
    _description="Novedades del iess"
    
    name = fields.Text("Referencia")
    #partner_id = fields.Many2one("employee_id","partner_id",type="many2one",relation="res.partner",string="Proveedor"),
    partner_id = fields.Many2one("res.partner",string="Proveedor")
    employee_id = fields.Many2one("hr.employee","Empleado")
    #vat = fields.related("partner_id","vat",type="char",string="ID",size=32),
    vat = fields.Char(string="ID",size=32)
    date = fields.Date("Fecha")

    