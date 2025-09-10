from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MaterialPurchaseRequisition(models.Model):
    _name = "material.requisition.order"
    _description = "Work Order"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]
    _order = "id desc"

    def unlink(self):
        for rec in self:
            if rec.state not in ("draft", "cancel", "reject"):
                raise UserError(
                    _("You can not delete Work Order which is not in draft or cancelled or rejected state.")
                )
        return super(MaterialPurchaseRequisition, self).unlink()

    name = fields.Char(
        string="Number",
        index=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "New"),
            ("dept_confirm", "Waiting Department Approval"),
            ("ir_approve", "Waiting IR Approval"),
            ("approve", "Approved"),
            ("cancel", "Cancelled"),
            ("reject", "Rejected"),
        ],
        default="draft",
        tracking=True,
    )
    request_date = fields.Date(
        string="Work Order Date",
        default=fields.Date.today(),
        required=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        required=True,
        copy=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        default=lambda self: self.env["hr.employee"].search(
            [("user_id", "=", self.env.uid)], limit=1
        ),
        required=True,
        copy=True,
    )
    approve_manager_id = fields.Many2one(
        "hr.employee",
        string="Department Manager",
        readonly=True,
        copy=False,
    )
    reject_manager_id = fields.Many2one(
        "hr.employee",
        string="Department Manager Reject",
        readonly=True,
    )
    approve_employee_id = fields.Many2one(
        "hr.employee",
        string="Approved by",
        readonly=True,
        copy=False,
    )
    reject_employee_id = fields.Many2one(
        "hr.employee",
        string="Rejected by",
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        copy=True,
    )
    requisition_line_ids = fields.One2many(
        "material.requisition.order.line",
        "requisition_id",
        string="Work Orders Line",
        copy=True,
    )
    date_end = fields.Date(
        string="Work Order Deadline",
        readonly=True,
        help="Last date for the product to be needed",
        copy=True,
    )
    date_done = fields.Date(
        string="Date Done",
        readonly=True,
        help="Date of Completion of Work Order",
    )
    managerapp_date = fields.Date(
        string="Department Approval Date",
        readonly=True,
        copy=False,
    )
    manareject_date = fields.Date(
        string="Department Manager Reject Date",
        readonly=True,
    )
    userreject_date = fields.Date(
        string="Rejected Date",
        readonly=True,
        copy=False,
    )
    userrapp_date = fields.Date(
        string="Approved Date",
        readonly=True,
        copy=False,
    )

    receive_date = fields.Date(
        string="Received Date",
        readonly=True,
        copy=False,
    )

    reason = fields.Text(
        string="Reason for Work Order",
        required=False,
        copy=True,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        copy=True,
    )
    requisiton_responsible_id = fields.Many2one(
        "hr.employee",
        string="Work Order Responsible",
        copy=True,
    )
    employee_confirm_id = fields.Many2one(
        "hr.employee",
        string="Confirmed by",
        readonly=True,
        copy=False,
    )
    confirm_date = fields.Date(
        string="Confirmed Date",
        readonly=True,
        copy=False,
    )
    global_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Vendor",
        required=False,
    )

    @api.model
    def create(self, vals):
        vals["name"] = self.env["ir.sequence"].next_by_code("work.order.seq")
        return super(MaterialPurchaseRequisition, self).create(vals)

    def requisition_confirm(self):
        for rec in self:
            manager_mail_template = self.env.ref(
                "material_requisitions_order.custom_email_confirm_material_requisition_order"
            )
            rec.employee_confirm_id = rec.employee_id.id
            rec.confirm_date = fields.Date.today()
            rec.state = "dept_confirm"
            if manager_mail_template:
                manager_mail_template.send_mail(self.id)

    def requisition_reject(self):
        for rec in self:
            rec.state = "reject"
            rec.reject_employee_id = self.env["hr.employee"].search(
                [("user_id", "=", self.env.uid)], limit=1
            )
            rec.userreject_date = fields.Date.today()

    def manager_approve(self):
        for rec in self:
            rec.managerapp_date = fields.Date.today()
            rec.approve_manager_id = self.env["hr.employee"].search(
                [("user_id", "=", self.env.uid)], limit=1
            )
            employee_mail_template = self.env.ref(
                "material_requisitions_order.custom_email_purchase_requisition_iruser_custom"
            )
            email_iruser_template = self.env.ref(
                "material_requisitions_order.custom_email_purchase_requisition"
            )
            employee_mail_template.sudo().send_mail(self.id)
            email_iruser_template.sudo().send_mail(self.id)
            rec.state = "ir_approve"

    def user_approve(self):
        for rec in self:
            rec.userrapp_date = fields.Date.today()
            rec.approve_employee_id = self.env["hr.employee"].search(
                [("user_id", "=", self.env.uid)], limit=1
            )
            rec.state = "approve"

    def reset_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancel"

    @api.onchange("employee_id")
    def set_department(self):
        for rec in self:
            rec.department_id = rec.employee_id.sudo().department_id.id

import re

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def _get_dynamic_prefix(self):
        """Calcula el prefijo dinámico usando la abreviatura de la compañía.
        Si el nombre tiene al menos dos palabras, toma las 3 primeras letras de la primera y 3 de la segunda;
        en caso contrario, toma solo las 3 primeras letras."""
        prefix = self.prefix or ''
        if self.company_id:
            # Elimina espacios innecesarios y divide en palabras
            words = re.split(r'\s+', self.company_id.name.strip())
            if len(words) >= 2:
                abbr = words[0][:3] + words[1][:3]
            else:
                abbr = words[0][:3]
            abbr = abbr.upper()
            return "{}-{}".format(abbr, prefix)
        return prefix

    @api.model
    def _next(self, sequence_date=None, **kwargs):
        for seq in self:
            seq.prefix = seq._get_dynamic_prefix()
        return super(IrSequence, self)._next(sequence_date=sequence_date, **kwargs)