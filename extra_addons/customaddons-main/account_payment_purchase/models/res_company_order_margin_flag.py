# -*- coding: utf-8 -*-
# © <2024> <Washington Guijarro>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import (
    api,
    models,
    fields,
    _
)


class ResCompanyOrderMarginFlag(models.Model):
    _name = 'res.company.order.margin.flag'
    _description="Margen para ordenes de compra"

    company_id = fields.Many2one("res.company",string="Empresa",required=True)
    type=fields.Selection([('margen-sale','Margen de Venta Individual'),
                           ('margen-purchase','Margen de Compra Individual'),
                           ('margen-sale-global', 'Margen de Venta por Documento'),
                           ('margen-purchase-global', 'Margen de Compra por Documento')

                           ],string="Tipo",default="margen-sale")
    margin_from =fields.Float(string="Desde % Margen",required=True)
    margin_to = fields.Float(string="Hasta % Margen", required=True)
    color = fields.Selection([('danger', 'Danger(Rojo)'),
                              ('warning', 'Warning(Amarillo)'),
                              ('success', 'Success(Verde)'),
                              # ('muted', 'Muted(Plomo)'),
                              # ('info', 'Info(Azul)')
                              ],string="Color")

    action=fields.Selection([('none','Nada')],default="none")

    _rec_name="color"

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