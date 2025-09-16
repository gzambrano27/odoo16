from odoo import exceptions, _
from odoo import api, fields, models, _


class RangosConfiguracionLead(models.Model):
    _name = 'rangos.crm'
    _description = 'Rangos para CRM'
    _rec_name="color"

    company_id = fields.Many2one("res.company",string="Empresa",required=True, index=True,
        default=lambda self: self.env.company)
    type=fields.Selection([('lead','Rangos Lead'),('oportunidad','Rangos Oportunidad')],string="Tipo",default="lead")
    margin_from =fields.Float(string="Desde %",required=True)
    margin_to = fields.Float(string="Hasta %", required=True)
    color = fields.Selection([('danger', 'Danger(Rojo)'),
                              ('warning', 'Warning(Amarillo)'),
                              ('success', 'Success(Verde)')],string="Color")

    action=fields.Selection([('none','Nada')],default="none")
    tipo_cliente=fields.Selection([('A','A'),('AA','AA'),('AAA','AAA')],string="Tipo Cliente",default="A")

    def evaluate_margin_in_range(self, value,type):
        """
        Esta función evalúa si un valor dado está dentro del rango de margen
        definido por los campos margin_from y margin_to del registro.

        :param value: El valor que se desea evaluar.
        :return: El registro si el valor está dentro del rango, o None si no lo está.
        """
        # Buscar el primer registro que cumpla con la condición
        DEC=2
        margin_flag = self.search([
            ('margin_from', '<=', round(value,DEC)),  # El valor debe ser mayor o igual al margen de inicio
            ('margin_to', '>=', round(value,DEC)) ,
            ('type','=',type)
            # El valor debe ser menor o igual al margen final
        ], limit=1)  # Limitar a 1 resultado (solo el primer registro que cumpla la condición)

        if margin_flag:
            return margin_flag.color
        return None