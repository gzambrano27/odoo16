import base64
import mimetypes
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class Subproyecto(models.Model):
    _name = 'projects.subproyecto'
    _description = 'Subproyecto'

    name = fields.Char(string='Nombre del Subproyecto', required=True)
    codigo = fields.Char(string='Código del Subproyecto', required=True)
    proyecto_id = fields.Many2one('projects.proyecto', string="Proyecto", required=True)  # Relación con el proyecto

    # Campos relacionados con el proyecto, almacenados y de solo lectura
    direccion = fields.Char(related='proyecto_id.direccion', string='Dirección', store=True, readonly=True)
    pais = fields.Many2one(related='proyecto_id.pais', string='País', store=True, readonly=True)
    provincia = fields.Many2one(related='proyecto_id.provincia', string='Provincia', store=True, readonly=True)
    ciudad = fields.Char(related='proyecto_id.ciudad', string='Ciudad', store=True, readonly=True)
    codigo_postal = fields.Char(related='proyecto_id.codigo_postal', string='Código Postal', store=True, readonly=True)
    longitud = fields.Char(related='proyecto_id.longitud', string='Longitud Geográfica', store=True, readonly=True)
    latitud = fields.Char(related='proyecto_id.latitud', string='Latitud Geográfica', store=True, readonly=True)
    fecha_inicio = fields.Date(related='proyecto_id.fecha_inicio', string='Fecha de Inicio', store=True, readonly=True)
    fecha_final = fields.Date(related='proyecto_id.fecha_final', string='Fecha Final', store=True, readonly=True)
    contacto = fields.Many2one(related='proyecto_id.contacto', string='Detalles de Contacto', store=True, readonly=True)

    # Relación con otros modelos del subproyecto
    personal_ids = fields.One2many('projects.subproyecto.personal', 'subproyecto_id', string='Personal Asignado')
    documentos_ids = fields.One2many('projects.subproyecto.documento', 'subproyecto_id', string='Documentos')
    gastos_extras_ids = fields.One2many('projects.subproyecto.gasto.extra', 'subproyecto_id', string='Gastos Extras')


import base64

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SubproyectoDocumento(models.Model):
    _name = 'projects.subproyecto.documento'
    _description = 'Documento del Subproyecto'

    titulo = fields.Char(string='Título', required=True)
    documento = fields.Many2many(
        'ir.attachment',
        string='Documento adjunto',
        required=True,
        help="Documentos relacionados con el subproyecto."
    )
    subproyecto_id = fields.Many2one('projects.subproyecto', string='Subproyecto', required=True)

    @api.model
    def create(self, vals):
        """
        Sobrescribe el método create para realizar validaciones al momento de crear el registro.
        """
        if 'documento' in vals and not vals.get('titulo'):
            raise ValidationError(_("Debe proporcionar un título para el documento."))
        return super(SubproyectoDocumento, self).create(vals)

    def write(self, vals):
        """
        Sobrescribe el método write para realizar validaciones al momento de actualizar el registro.
        """
        if 'documento' in vals and not vals.get('titulo'):
            raise ValidationError(_("El título del documento no puede estar vacío."))
        return super(SubproyectoDocumento, self).write(vals)

    def unlink(self):
        """
        Sobrescribe unlink para eliminar los documentos adjuntos asociados al registro.
        """
        for record in self:
            if record.documento:
                record.documento.unlink()
        return super(SubproyectoDocumento, self).unlink()

class GastoExtra(models.Model):
    _name = 'projects.subproyecto.gasto.extra'
    _description = 'Gastos Extras del Subproyecto'

    fecha = fields.Date(string='Fecha', required=True)
    vendedor = fields.Many2one('res.partner', string='Vendedor', required=True)
    cuenta_analitica = fields.Many2one('account.analytic.account', string='Cuenta Analítica', required=True)
    nota = fields.Text(string='Nota')
    cantidad = fields.Float(string='Cantidad', required=True)
    costo = fields.Float(string='Costo Unitario', required=True)
    total = fields.Float(string='Costo Total', compute='_compute_total', store=True)
    factura_id = fields.Many2one('account.move', string='Factura')
    subproyecto_id = fields.Many2one('projects.subproyecto', string='Subproyecto', required=True)

    @api.depends('cantidad', 'costo')
    def _compute_total(self):
        for record in self:
            record.total = record.cantidad * record.costo

class SubproyectoPersonal(models.Model):
    _name = 'projects.subproyecto.personal'
    _description = 'Personal del Subproyecto'

    subproyecto_id = fields.Many2one('projects.subproyecto', string='Subproyecto', required=True)
    partner_id = fields.Many2one('res.partner', string='Contacto del Personal', required=True)
    rol = fields.Char(string='Rol en el Subproyecto', help="Rol o función que desempeña esta persona en el subproyecto.")
    notas = fields.Text(string='Notas Adicionales')
