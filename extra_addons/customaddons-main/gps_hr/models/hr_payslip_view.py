from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrPayslipView(models.Model):
    _name = 'hr.payslip.view'
    _description = 'Vista de Rol de Pago con Mes'
    _auto = False

    employee_id = fields.Integer(  string="ID Empleado", readonly=True)
    payslip_id = fields.Integer(  string="ID Rol", readonly=True)
    employee_name = fields.Char(string="Empleado", readonly=True)
    #payslip_name = fields.Char(string="Nombre del Rol", readonly=True)
    month_name = fields.Char(string="Mes", readonly=True)
    year = fields.Integer(string="Año", readonly=True)
    company_id=fields.Many2one("res.company","Compañia", readonly=True)

    currency_id = fields.Many2one(string="Moneda", related="company_id.currency_id", store=False, readonly=True)

    total_in = fields.Monetary("Ingresos", digits=(16, 2))
    total_out = fields.Monetary("Egresos", digits=(16, 2))
    total_payslip = fields.Monetary("Total", digits=(16, 2))

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW hr_payslip_view AS (
                  SELECT
                    p.id AS id,
                    p.id AS payslip_id,
                    upper(e.name) AS employee_name,                    
                    upper(cm.name) AS month_name,
					hpr.year as year,
					hpr.company_id,
					p.total_payslip,
					p.total_in,
					abs(p.total_out) as total_out,
					p.employee_id ,
					rc.currency_id 
                FROM hr_payslip p
                inner JOIN hr_employee e ON p.employee_id = e.id
				inner join hr_payslip_run hpr on hpr.id=p.payslip_run_id 
				inner join res_company rc on rc.id=hpr.company_id
                inner JOIN calendar_month cm ON hpr.month_id = cm.id 
                where p.state in ('done','paid') and hpr.state in ('close','paid')
            )
        """)

    _order="payslip_id desc"

    @api.model
    def _where_calc(self, domain, active_test=True):
        # Si no se proporciona un dominio, inicializamos como vacío
        domain = domain or []

        # Si el contexto tiene "only_user", no modificamos el dominio
        if not self._context.get("only_user", False):
            return super(HrPayslipView, self)._where_calc(domain, active_test)

        # Obtener el usuario actual
        user = self.env["res.users"].sudo().browse(self._uid)

        # Comprobar si el usuario tiene permisos de grupo 'group_empleados_usuarios'
        if user.has_group("gps_hr.group_empleados_usuarios"):
            # Buscar el empleado relacionado con el usuario
            employee = self.env["hr.employee"].sudo().search([('user_id', '=', user.id)], limit=1)

            # Si encontramos un empleado, modificamos el dominio para filtrar por su ID
            if employee:
                domain.append(("employee_id", "in", tuple(employee.ids + [-1, -1])))
            else:
                domain.append(("employee_id", "=", -1))
        # Llamar a la función original con el dominio modificado
        return super(HrPayslipView, self)._where_calc(domain, active_test)

    def print_payslip(self):
        action = self.env.ref('hr_payroll.action_report_payslip')
        if not action:
            raise ValidationError("No se pudo encontrar el reporte.")
            # Retornamos la acción para imprimir el reporte
        brw_payslip=self.env["hr.payslip"].sudo().browse(self.payslip_id)
        return action.sudo().report_action(brw_payslip)