from odoo import exceptions, _
from odoo import api, fields, models, _


class BimMargenes(models.Model):
    _name = 'bim.rangos.margen'
    _description = 'Rangos de margenes para APUS'
    _rec_name="color"

    company_id = fields.Many2one("res.company",string="Empresa",required=True, index=True,
        default=lambda self: self.env.company)
    type=fields.Selection([('margen-apu','Margen Bruto Apu'),('margen-apu-cab','Margen Bruto Cab Apu')],string="Tipo",default="margen-apu")
    margin_from =fields.Float(string="Desde % Margen",required=True)
    margin_to = fields.Float(string="Hasta % Margen", required=True)
    color = fields.Selection([('danger', 'Danger(Rojo)'),
                              ('warning', 'Warning(Naranja)'),
                              ('success', 'Success(Verde)')],string="Color")

    action=fields.Selection([('none','Nada')],default="none")


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