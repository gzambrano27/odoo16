# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID
import base64
from xml.etree.ElementTree import Element, SubElement, tostring
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager
from datetime import timedelta, date
fileO = FileManager()
dateO = DateManager()
calendarO = CalendarManager()


class HrEmployeeUpdateRequestWizard(models.Model):
    _name = 'hr.employee.update.request.wizard'
    _description = 'Asistente para Actualizar Empleados'

    deadline_date = fields.Date(string="Fecha Máxima de Actualización", tracking=True, readonly=False,required=True,default=lambda self: date.today() + timedelta(days=7))
    contract_ids = fields.Many2many('hr.contract', "update_wizard_empl_rel","wizard_id","employee_id",string='Empleados')
    enable_bank_account = fields.Boolean("Habilitar Cuenta Bancaria", default=True)

    @api.constrains('deadline_date')
    def _check_deadline_date(self):
        for rec in self:
            if rec.deadline_date and rec.deadline_date < fields.Date.context_today(self):
                raise ValidationError(_("La Fecha Máxima de Actualización no puede ser menor a hoy."))

    def process(self):
        self.ensure_one()
        if not self.contract_ids:
            raise ValidationError(_("No hay contratos seleccionados"))
        employees=self.contract_ids.mapped('employee_id')
        employees=employees.with_context({"deadline_date":self.deadline_date,"enable_bank_account":self.enable_bank_account})
        return employees.create_update_request()