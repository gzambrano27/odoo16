from odoo import models, fields, api, _

class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    equipment_ids = fields.One2many("hr.recruitment.equipment", "applicant_id", string="Equipos a Requerir")


    @api.model
    def cron_assign_all_applicants(self):
        #usuarios a excluir
        excluded_user_ids = [125, 333, 339, 64, 303, 342, 63, 23, 71, 19, 31, 171, 7,
                             217, 2, 158, 297, 159, 427, 37, 269, 39, 268, 36]

        # Buscar usuarios excluyendo los anteriores
        usuarios = self.env['res.users'].search([
            ('id', 'not in', excluded_user_ids)
        ])
        for x in usuarios:
            self.assign_menus_by_department(x.id, 'ventas')

    @api.model
    def assign_menus_by_department(self, user_id, department):
        """Asigna menús a un usuario en base a su departamento"""
        cr = self.env.cr
        # Diccionario de menús por departamento
        menus_by_dept = {
            'compras': [5,112,113,131,133,137,172,177,178,189,193,196,198,200,204,233,258,391,455,478,492,517,691,722,786,802,812,815,847,864,885,887,888,890,893,936,994,995,1036,1091,1093],
            # puedes añadir más departamentos aquí
            'ventas': [5,112,113,131,133,137,172,177,178,189,193,196,198,199,200,204,233,317,391,455,478,492,517,691,722,786,802,812,815,847,864,885,887,888,890,893,936,994,995,1036,1091,1093],
            # 'contabilidad': [...],
        }

        menu_ids = menus_by_dept.get(department.lower())
        if not menu_ids:
            raise ValueError(f"No hay menús definidos para el departamento '{department}'.")

        # Eliminar menús actuales del usuario
        cr.execute("DELETE FROM user_menu_rel WHERE user_id = %s", (user_id,))

        # Insertar los nuevos
        for mid in menu_ids:
            cr.execute("INSERT INTO user_menu_rel (user_id, menu_id) VALUES (%s, %s)", (user_id, mid))