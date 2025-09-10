from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    require_requisition_po = fields.Boolean(
        string='Validar Requisición en Orden de Compra',
        #config_parameter='purchase.require_requisition_po',
        readonly=False, #company_dependent=True,
        #related='company_id.require_requisition_po',
        help='Si está activo, se requerirá que cada orden de compra tenga una requisición asociada.'
    )
    dias_eval = fields.Integer(
        string='Dias de Evaluacion',
        related='company_id.dias_eval',
        help='Dias a evaluar de una requisicion aprobada para convertirse en OC.'
    )

class ResCompany(models.Model):
    _inherit = 'res.company'

    require_requisition_po = fields.Boolean(
        string='Validar Requisición en Orden de Compra',
        default=False,
        help='Si está activo, se requerirá que cada orden de compra tenga una requisición asociada en esta compañía.'
    )
    dias_eval = fields.Integer(
        string='Días de Evaluación',
        default=0,
        help='Días máximos en que una requisición puede estar aprobada sin ser enviada a OC.'
    )