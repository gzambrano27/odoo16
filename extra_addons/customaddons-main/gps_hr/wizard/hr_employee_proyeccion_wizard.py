# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID
import base64
from xml.etree.ElementTree import Element, SubElement, tostring
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager

fileO = FileManager()
dateO = DateManager()
calendarO = CalendarManager()


class HrEmployeeProyeccionWizard(models.Model):
    _name = 'hr.employee.proyeccion.wizard'
    _description = 'Asistente para Generar Empresas'

    period_id = fields.Many2one("hr.deductible.expenses.period", "Periodo", required=True)
    contract_ids = fields.Many2many('hr.contract', "proyeccion_wizard_empl_rel","wizard_id","employee_id",string='Empleados')

    def process(self):
        for brw_each in self:
            if not brw_each.contract_ids:
                raise ValidationError(_("Debes definir al menos un contrato"))
            for brw_contract in brw_each.contract_ids:
                srch=self.env["hr.deductible.expenses.contract.period.template"].search([('contract_id','=',brw_contract.id),
                                                                                         ('state','=','draft')
                                                                                         ])
                if srch:
                    raise ValidationError(_("El contrato de %s ya tiene una actualizacion pendiente") % (brw_contract.employee_id.name,))
                self.env["hr.deductible.expenses.contract.period.template"].create(
                    {
                        "contract_id":brw_contract.id,
                        "period_id":brw_each.period_id.id,
                        "vivienda":0.00,
                        "alimentacion": 0.00,
                        "vestimenta": 0.00,
                        "salud": 0.00,
                        "turismo": 0.00,
                        "educacion": 0.00,
                        "active":True,
                        "state":"draft"
                    }
                )
        return True