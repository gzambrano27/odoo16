from odoo import models, fields, api, _

class EmployeeContractInfo(models.Model):
    _name = 'employee.contract.info.view'
    _description = 'Employee Contract Info'
    _auto = False

    identificador = fields.Many2one('hr.employee', readonly=True)
    identificador_company = fields.Many2one('res.company', 'Company', readonly=True)
    nombre_empleado = fields.Char('Nombre del empleado', readonly=True)
    fecha_ingreso = fields.Date('Fecha de ingreso', readonly=True)
    rol = fields.Char('rol', readonly=True)
    sueldo = fields.Float('sueldo', readonly=True)
    metodo_pago_quincenal = fields.Char('Modo de pago quincena', readonly=True)
    valor = fields.Float('Valor', readonly=True)
    estado = fields.Char('estado', readonly=True)
    inicio_contrato = fields.Date('Inicio del contrato', readonly=True)
    fin_contrato = fields.Date('Fin del contrato', readonly=True)

    def init(self):
        self.env.cr.execute("""DROP VIEW IF EXISTS employee_contract_info_view;""")
        self.env.cr.execute("""
            create view employee_contract_info_view as
            select 
                he.id as id,
                he.id as identificador,
                he.company_id as identificador_company,
                he."name" as nombre_empleado,
                he.fecha_ingreso as fecha_ingreso,
                tr."name" as rol,
                he.sueldo as sueldo,
                he.active,
                hc.first_fitten_payment_mode as metodo_pago_quincenal,
                hc.value as valor,
                hc.state as estado,
                hc.date_start as inicio_contrato,
                hc.date_end as fin_contrato  
            from hr_employee he
            left join hr_contract hc on he.contract_id = hc.id
            inner join tipo_roles tr on he.tipo_rol = tr.id
            where (hc.state is null or hc.state = 'open') and he.active = true;
        """)
