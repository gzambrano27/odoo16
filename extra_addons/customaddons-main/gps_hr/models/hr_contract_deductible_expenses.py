# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _, SUPERUSER_ID
import base64
from odoo.exceptions import ValidationError


class HrDeductibleExpenses(models.Model):
    _name = "hr.deductible.expenses.period"
    _description = "Gastos Deducibles por Contrato"

    @api.model
    def _get_default_year(self):
        date=fields.Date.context_today(self)
        return date.year

    year=fields.Integer("Periodo",default=_get_default_year)
    active=fields.Boolean("Activo",default=True)
    line_ids=fields.One2many("hr.deductible.expenses.period.lines","period_id","Detalle")

    _rec_name="year"

    _order="year desc"

class HrDeductibleExpensesLines(models.Model):
    _name = "hr.deductible.expenses.period.lines"
    _description = "Detalle de Gastos Deducibles por Contrato"

    period_id=fields.Many2one("hr.deductible.expenses.period","Periodo",ondelete="cascade")
    fraccion_basica=fields.Float("Fraccion Basica",required=True,digits=(16,2))
    exceso_hasta = fields.Float("Exceso Hasta", required=True, digits=(16, 2))
    imp_fraccion_basica = fields.Float("Impuesto Fraccion Basica", required=True, digits=(16, 2))
    imp_fraccion_excedente = fields.Float("Impuesto Fraccion Excedente", required=True, digits=(16, 2))

    _rec_name="fraccion_basica"
#####################################################################################################3333

class HrDeductibleContractExpenses(models.Model):
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "portal.mixin",
    ]
    _name = "hr.deductible.expenses.contract.period"
    _description = "Gastos Deducibles por Contrato"

    contract_id = fields.Many2one("hr.contract", "Contrato", ondelete="cascade")
    employee_id = fields.Many2one(related="contract_id.employee_id",string="Empleado",readonly=True,store=False)
    period_id = fields.Many2one("hr.deductible.expenses.period", "Periodo",required=True)
    company_id=fields.Many2one(related="contract_id.company_id",readonly=True,store=False)
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True, store=False)
    vivienda=fields.Monetary(string="Vivienda",required=True,digits=(16,2),tracking=True)
    alimentacion = fields.Monetary(string="Alimentación", required=True, digits=(16, 2),tracking=True)
    vestimenta = fields.Monetary(string="Vestimenta", required=True, digits=(16, 2),tracking=True)
    salud = fields.Monetary(string="Salud", required=True, digits=(16, 2),tracking=True)
    turismo = fields.Monetary(string="Turismo", required=True, digits=(16, 2),tracking=True)
    educacion = fields.Monetary(string="Educación", required=True, digits=(16, 2),tracking=True)
    active=fields.Boolean("Activo",default=True,tracking=True)

    _rec_name="period_id"

class HrDeductibleContractTemplateExpenses(models.Model):
    _inherit= "hr.deductible.expenses.contract.period"
    _name = "hr.deductible.expenses.contract.period.template"
    _description = "Plantilla de Gastos Deducibles por Contrato"

    def unlink(self):
        for brw_each in self:
            if self._context.get("validate_unlink", True):
                if brw_each.state != 'draft':
                    raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        return super(HrDeductibleContractTemplateExpenses, self).unlink()

    def action_draft(self):
        for brw_each in self:
            brw_each.write({"state":"draft"})
        return True

    def action_confirmed(self):
        for brw_each in self:
            brw_each.write({"state":"confirmed"})
        return True

    def action_updated(self):
        for brw_each in self:
            brw_each.write({"state":"updated"})
            srch=self.env["hr.deductible.expenses.contract.period"].search([('contract_id','=',brw_each.contract_id.id)])
            if srch:
                srch.write({"active":False})
            brw_new=self.env["hr.deductible.expenses.contract.period"].create({
                "contract_id":brw_each.contract_id.id,
                "period_id":brw_each.period_id.id,
                "vivienda": brw_each.vivienda,
                "alimentacion": brw_each.alimentacion,
                "vestimenta": brw_each.vestimenta,
                "salud": brw_each.salud,
                "turismo": brw_each.turismo,
                "educacion": brw_each.educacion,
                "active":True
            })
        return True

    def action_cancelled(self):
        for brw_each in self:
            brw_each.write({"state":"updated"})
        return True

    state=fields.Selection([('draft','Preliminar'),
                            ('confirmed','Confirmado'),
                            ('updated', 'Actualizado'),
                            ('cancelled', 'Anulado')
                            ],tracking=True,string="Estado",default="draft")
    @api.model
    def _where_calc(self, domain, active_test=True):
        # Si no se proporciona un dominio, inicializamos como vacío
        domain = domain or []

        # Si el contexto tiene "only_user", no modificamos el dominio
        if not self._context.get("only_user", False):
            return super(HrDeductibleContractTemplateExpenses, self)._where_calc(domain, active_test)

        # Obtener el usuario actual
        user = self.env["res.users"].sudo().browse(self._uid)

        # Comprobar si el usuario tiene permisos de grupo 'group_empleados_usuarios'
        if user.has_group("gps_hr.group_empleados_usuarios"):
            # Buscar el empleado relacionado con el usuario
            employee = self.env["hr.employee"].sudo().search([('user_id', '=', user.id)], limit=1)

            # Si encontramos un empleado, modificamos el dominio para filtrar por su ID
            if employee:
                domain.append(("contract_id.employee_id", "in", tuple(employee.ids + [-1, -1])))
            else:
                domain.append(("contract_id.employee_id", "=", -1))
        # Llamar a la función original con el dominio modificado
        return super(HrDeductibleContractTemplateExpenses, self)._where_calc(domain, active_test)
