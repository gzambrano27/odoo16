from odoo import models, fields,api,_

class MaintenanceActaView(models.Model):
    _name = 'maintenance.acta.view'
    _description = 'Vista de Actas de Entrega'
    _auto = False  # Modelo basado en vista

    codigo = fields.Char("Código")
    fecha = fields.Date("Fecha")
    employee_id = fields.Many2one("hr.employee", string="Empleado que Recibe")
    observacion = fields.Text("Observación")
    ubicacion = fields.Char("Ubicación")
    equipo_recibe = fields.Many2one("maintenance.equipment", string="Equipo Recibido")
    equipo_recibe_name = fields.Char("Nombre del Equipo")
    category_name = fields.Char("Categoría")
    model = fields.Char("Modelo")
    serial_no = fields.Char("Número de Serie")

    def init(self):
        self._cr.execute("""
            CREATE OR REPLACE VIEW maintenance_acta_view AS (
                SELECT 
                    ma.id as id,
                    ma.codigo,
                    ma.fecha,
                    ma.empleado_recibe as employee_id,
                    ma.observacion,
                    ma.ubicacion,
                    ma.equipo_recibe,
                    COALESCE(meq.name->>'es_EC', meq.name->>'en_US') as equipo_recibe_name,
                    COALESCE(meqc.name->>'es_EC', meqc.name->>'en_US') as category_name,
                    meq.model,
                    meq.serial_no
                FROM maintenance_acta ma
                INNER JOIN maintenance_equipment meq ON meq.id = ma.equipo_recibe
                INNER JOIN maintenance_equipment_category meqc ON meqc.id = meq.category_id
                WHERE ma.tipo != 'recepcion' AND ma.state = 'open'
            )
        """)

    @api.model
    def _where_calc(self, domain, active_test=True):
        # Si no se proporciona un dominio, inicializamos como vacío
        domain = domain or []

        # Si el contexto tiene "only_user", no modificamos el dominio
        if not self._context.get("only_user", False):
            return super(MaintenanceActaView, self)._where_calc(domain, active_test)

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
        return super(MaintenanceActaView, self)._where_calc(domain, active_test)