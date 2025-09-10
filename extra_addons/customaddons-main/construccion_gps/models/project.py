from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning

class ProjectTask(models.Model):
    _inherit = "project.task"

    planned_date_begin = fields.Datetime('Inicio Fecha Planeada')
    planned_date_end = fields.Datetime('Fin Fecha Planeada')
    overlap_warning = fields.Char('overlap_warning')
    user_names = fields.Char('user_names')
    allocated_hours = fields.Float('allocated_hours')


class ProjectProject(models.Model):
    _inherit = 'project.project'

    sale_order_id = fields.Many2one('sale.order', string='Orden de Venta', tracking=True)
    allow_analytic_account = fields.Boolean("Cuenta analítica", default=True)
    plantilla_tarea_id = fields.Boolean("Cuenta analítica", default=True)
    #purchase_request_id = fields
    #service_request_id

    def unlink(self):
        for record in self:
            if record.analytic_account_id:
                raise UserError(_("No puedes eliminar un proyecto que tiene una cuenta analítica asociada."))
        return super().unlink()
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Crear una cuenta analítica si el proyecto tiene activado 'allow_analytic_account'
        y no se ha proporcionado una cuenta analítica.
        """
        defaults = self.default_get(['allow_analytic_account', 'analytic_account_id','allow_timesheets'])
        
        for vals in vals_list:
            allow_timesheets = vals.get('allow_timesheets', 
                                              vals.get('allow_timesheets', defaults.get('allow_timesheets', False)))
            
            allow_analytic_account = vals.get('allow_analytic_account', 
                                              vals.get('allow_analytic_account', defaults.get('allow_analytic_account', False)))
            
            if not allow_analytic_account and allow_timesheets:
                raise UserError(_(
                        "Debes chequear cuenta analitica "
                        "cuando este chequeado parte de horas."
                    ))
            analytic_account_id = vals.get('analytic_account_id', defaults.get('analytic_account_id'))

            # Si el usuario no ha especificado 'allow_analytic_account', aseguramos que usemos el valor correcto
            if 'allow_analytic_account' not in vals:
                allow_analytic_account = defaults.get('allow_analytic_account', False)

            # Verificamos si se debe crear una cuenta analítica
            if allow_analytic_account and not analytic_account_id:
                analytic_account = self._create_analytic_account_from_values(vals)
                if analytic_account:
                    vals['analytic_account_id'] = analytic_account.id
        
        return super().create(vals_list)

class Proyecto(models.Model):
    _name = 'projects.proyecto'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Proyecto'

    name = fields.Char(string='Nombre del Proyecto', required=True, tracking=True)

class Permiso(models.Model):
    _name = 'projects.permiso'
    _description = 'Permisos y Aprobaciones'

    proyecto_id = fields.Many2one(
        comodel_name='projects.proyecto',
        string='Proyecto',
        required=True,
    )
    fecha = fields.Date(string='Fecha', required=True)
    tipo_documento = fields.Selection([
        ('pdf', 'PDF'),
        ('xls', 'Excel'),
        ('otro', 'Otro'),
    ], string='Tipo de Documento', required=True)
    documento = fields.Binary(string='Documento Subido', required=True)
    subido_por = fields.Many2one('res.users', string='Subido por', default=lambda self: self.env.user)
    feedback = fields.Text(string='Feedback')
    estado = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ], string='Estado', default='pendiente')


