from odoo import api, fields, models, _


class HrDepartment(models.Model):

    _inherit = "hr.department"

    area = fields.Many2one('account.area','Area', required=False)
    member_ids = fields.One2many('hr.contract', 'department_id', 'Members', readonly=True)
    