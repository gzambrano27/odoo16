# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

TICKET_PRIORITY = [
    ('0', 'Low priority'),
    ('1', 'Medium priority'),
    ('2', 'High priority'),
    ('3', 'Urgent'),
]

class PostventaRequest(models.Model):
    _name = "postventa.request"
    _description = "Requerimiento de Servicio PostVenta"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_create desc, id desc"

    date_create = fields.Datetime(
        string="Fecha de Creación",
        default=fields.Datetime.now,
        readonly=True,
    )
    name = fields.Char(
        string="Número de Referencia",
        required=True,
        copy=False,
        readonly=True,
        default="Nuevo",
    )

    prioridad = fields.Selection(TICKET_PRIORITY, string='Prioridad', default='0')


    categoria = fields.Selection(
        [
            ('garantia', 'Garantía'),
            ('mantenimiento_correctivo', 'Mantenimiento Correctivo'),
            ('mantenimiento_preventivo', 'Mantenimiento Preventivo'),
            ('emergencia', 'Emergencia'),
        ],
        string="Categoría",
        required=True,
        default='mantenimiento_correctivo',
    )
    fecha_limite = fields.Date(string="Fecha Límite")
    partner_id = fields.Many2one('res.partner', string="Empresa / Cliente", required=True)

    user_id = fields.Many2one('res.users', string="Solicitante", default=lambda self: self.env.uid, readonly=True)
    requester_company = fields.Char(string="Compañía", related="user_id.company_id.name", readonly=True, store=True)
    requester_email = fields.Char(string="Email de Trabajo", related="user_id.email", readonly=True, store=True)
    requester_department = fields.Char(
        string="Departamento",
        compute="_compute_requester_department",
        readonly=True,
        store=True,
    )

    reference_type = fields.Selection(
        [
            ('factura', 'Factura'),
            ('serv_autorizado', 'Serv. Autorizado'),
        ],
        string="Referencia",
        required=True,
        default='factura',
    )
    analytic_account_id = fields.Many2one('account.analytic.account', string="Cuenta Analítica")
    description = fields.Html(string="Descripción del Servicio", sanitize=False)

    stage = fields.Selection(
        [
            ('borrador', 'Borrador'),
            ('en_proceso', 'En Proceso'),
            ('aprobado', 'Aprobado'),
            ('cancelado', 'Cancelado'),
        ],
        string="Etapa",
        default='borrador',
        tracking=True,
    )

    process_date = fields.Datetime(string="Fecha de Paso a Proceso", readonly=True)
    service_type = fields.Selection(
        [
            ('preventivo', 'Preventivo'),
            ('correctivo', 'Correctivo'),
            ('garantia', 'Garantía'),
            ('emergencia', 'Emergencia'),
        ],
        string="Tipo de Servicio",
    )
    # Ya no usamos observacion aquí, porque pasamos a la tabla de líneas.
    approver_id = fields.Many2one('res.users', string="Aprobado por", readonly=True)
    approval_date = fields.Datetime(string="Fecha de Aprobación", readonly=True)

    note_ids = fields.One2many('postventa.request.note', 'request_id', string="Notas de Seguimiento")
    line_ids = fields.One2many('postventa.request.line', 'request_id', string="Detalles de Seguimiento")

    @api.depends('user_id')
    def _compute_requester_department(self):
        for rec in self:
            dept = ''
            if rec.user_id and rec.user_id.employee_ids:
                emp = rec.user_id.employee_ids[0]
                if emp.department_id:
                    dept = emp.department_id.name
            rec.requester_department = dept

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            seq = self.env['ir.sequence'].next_by_code('postventa.request') or 'Nuevo'
            vals['name'] = seq
        return super().create(vals)

    def action_set_pendiente(self):
        for rec in self:
            rec.stage = 'pendiente'

    def action_set_en_proceso(self):
        for rec in self:
            rec.stage = 'en_proceso'
            if not rec.process_date:
                rec.process_date = fields.Datetime.now()

    def action_set_aprobado(self):
        for rec in self:
            rec.stage = 'aprobado'
            rec.approver_id = self.env.uid
            rec.approval_date = fields.Datetime.now()

    def action_set_cancelado(self):
        for rec in self:
            rec.stage = 'cancelado'

    def create_followup_note(self):
        self.ensure_one()
        return {
            'name': _('Nueva Nota de Seguimiento'),
            'res_model': 'postventa.request.note',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }


class PostventaRequestNote(models.Model):
    _name = "postventa.request.note"
    _description = "Nota de Seguimiento de Requerimiento"
    _order = "create_date desc"

    request_id = fields.Many2one('postventa.request', string="Requerimiento", required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string="Creado por", default=lambda self: self.env.uid, readonly=True)
    note = fields.Text(string="Comentario", required=True)
    create_date = fields.Datetime(string="Fecha", default=fields.Datetime.now, readonly=True)

    @api.model
    def create(self, vals):
        if not vals.get('request_id'):
            raise UserWarning(_("Debe especificar el Requerimiento para la nota"))
        return super().create(vals)


class PostventaRequestLine(models.Model):
    _name = "postventa.request.line"
    _description = "Líneas de Seguimiento en Postventa"

    request_id = fields.Many2one('postventa.request', string="Requerimiento", required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string="Producto", required=True)
    descripcion = fields.Char(string="Descripción")
    cantidad = fields.Float(string="Cantidad")
    observacion = fields.Text(string="Observación")
