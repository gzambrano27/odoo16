from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

HOURS_PER_DAY = 8

class ThEspecialidades(models.Model):
    _name = 'th.especialidades'
    
    codigo = fields.Char('Codigo')
    name = fields.Char('Descripcion')
    estado = fields.Selection([
        ('activo', "Activo"),
        ('inactivo', 'Inactivo'),
    ], 'Estado', default='activo')

class HrLeave(models.Model):
    _inherit = 'hr.leave'
    
    
    nombre_novedad = fields.Char(related='holiday_status_id.name',string='Novedad')
    number_of_days = fields.Float(string='Number of Days', digits=(3,2))
    number_of_hours = fields.Float(string='Number of hours',multi='number_of_hours')
    contract_id = fields.Many2one('hr.contract', 'Contract')
    justified = fields.Boolean('justified?', required=False)
    tipo_novedad = fields.Selection([
        ('enfermedad', "Enfermedad"),
        ('enfermedad familiar', 'Enfermedad Familiar'),
        ('mantenimiento oficina', "Mantenimiento Infraestructura Oficina"),
        ('incidentes operativos de oficina', "Incidentes Operativos de Oficina"),
        ('calamidad domestica', "Calamidad Domestica"),
    ], 'Tipo Novedad', default='enfermedad')
    especialidad_id = fields.Many2one('th.especialidades', string='Especialidades')
    # periodo_gozado = fields.Char(related = 'periodos.periodo',string = 'Periodo gozado', store=True)
    periodo_anticipado = fields.Boolean('Anticipado?', required=False)
    dias_pagado = fields.Integer('Dias Pagados')
    periodos = fields.Many2one('hr.vacations.history')
    # dias_pendientes = fields.Float(related = 'periodos.dias_pendientes' , string="Dias Pendientes",store = True, digits=(5,2))
    es_pagado = fields.Boolean('Es pagado?')
    es_medio_dia = fields.Boolean('Es medio dia?')
    tipo_certificado = fields.Selection([
        ('particular', "Particular"),
        ('msp', 'MSP'),
        ('iess', "IESS"),
    ], 'Tipo Certificado', default='iess')
    liquida_periodo = fields.Boolean('Liquida en Periodo?', default = True)
    fecha_ingreso = fields.Date(related = 'employee_id.fecha_ingreso')
    date_from_reg =  fields.Datetime('Fecha Ini Reg', readonly=True, index=True, copy=False)
    date_to_reg = fields.Datetime('Fecha Fin Reg', readonly=True, index=True, copy=False)
    es_servicios_prestados = fields.Boolean('Es Serv Prestados?')
    
    
        
class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type' 

    porcentaje_rem_iess = fields.Float(string='%Remuneracion IESS',digits=(5,2))
    porcentaje_rem_empleador = fields.Float(string='%Remuneracion Empleador',digits=(5,2))

