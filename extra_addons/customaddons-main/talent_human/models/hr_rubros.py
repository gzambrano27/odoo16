# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-2014 TabonoIT (http://tabonoit.com.ec).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, fields, models, _


class hr_rubros(models.Model):

    _name = "hr.rubros"

    codigo = fields.Char('Codigo', size=3)
    name = fields.Selection([('Desayuno','Desayuno'),
                             ('Almuerzo','Almuerzo'),
                             ('Merienda','Merienda'),
                             ('Combustible','Combustible'),
                             ('Valija','Envio de Valija'),
                             ('Parqueo','Parqueo'),
                             ('Lavada','Lavada de Vehiculo'),
                             ('Peaje','Peaje'),
                             ('Alimentacion','Alimentacion en Viaje'),
                             ('Lavado','Lavado de Vehiculo'),
                             ('Alquiler','Alquiler de Vehiculo'),
                             ('Movilizacion','Movilizacion Tramites de Oficina'),
                             ('Eventos','Eventos Sociales'),
                             ('Cafeteria','Cafeteria'),
                             ('Agua','Botellon de Agua'),
                             ('Limpieza','Suministros de Limpieza'),
                             ('Oficina','Suministros de Oficina'),
                             ('Medicina','Botiquin de Oficina'),
                             ('Mantenimiento','Mantenimiento de Oficina'),
                             ('Computacion','Mantenimiento de Equipos de Computo'),
                             ('Comisiones','Comisiones Bancarias'),
                             ('Tramites','Tramites Administrativos'),
                             ('Hospedaje','Viaticos por hospedaje'),
                             ('Fumigacion','Fumigacion en pista'),
                             ('Limpieza_racimo','Limpieza de Racimo'),
                             ('Devmulta','Devolucion Multa'),
                             ('Varios','Varios'),
                             ('Evafruta','Evaluacion de fruta')
                             ],    'Rubro', default='Almuerzo')
    unidad_administrativa = fields.Many2one('establecimientos', string='Unidad Administrativa')
    valor = fields.Float(digits=(4,2))
    otros = fields.Boolean('Varios')
    account_debit = fields.Many2one('account.account', 'Debit Account', domain=[('deprecated', '=', False)])
    account_credit = fields.Many2one('account.account', 'Credit Account', domain=[('deprecated', '=', False)])

    #debo cambiar elnombre para presentar en los campos many2one
    #@api.multi
    @api.depends('unidad_administrativa', 'name')
    def name_get(self):
        data = []
        for x in self:
            name = u'{0} {1}'.format(
                x.name,
                x.unidad_administrativa.name or '*'
            )
            data.append((x.id, name))
        return data


class lista_blanca_rubros(models.Model):
    _name = "hr.lista.blanca.rubros"
#
#     empleado = fields.Many2one("hr.employee", "Empleado")
#     tipo_rubro = fields.Many2one("hr.rubros", "Tipos")
#     reembolso = fields.Boolean("Reembolsa")
#     #unidad_administrativa = fields.Many2one(related = 'empleado.unidad_administrativa',store = True,string='Unidad Administrativa')
#     tipo_rol = fields.Many2one(related='empleado.tipo_rol', store=True, string='Tipo Rol')
#     estado = fields.Selection([
#                     ('activo', 'Activo'),
#                     ('inactivo', 'Inactivo'),
#                     ],'Estado', default='activo')
    
    
    # @api.multi
    # @api.onchange('unidad_administrativa')
    # def set_domain(self):
    #     if self.unidad_administrativa:
    #         obj_rubros = self.env['hr.rubros']
    #         ids_rubros =  obj_rubros.search([('unidad_administrativa','=',self.unidad_administrativa.id)]).mapped("id")
    #         #print ids_rubros
    #         domain = {'tipo_rubro': [('id','in', ids_rubros)]}
    #         #print domain
    #         return {'domain': {'tipo_rubro': [('id','in', ids_rubros)]}}
        
    
    