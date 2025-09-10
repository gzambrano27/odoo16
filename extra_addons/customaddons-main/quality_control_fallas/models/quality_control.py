# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class QualityControlFallas(models.Model):
    _name = 'quality.control.fallas'
    _description = 'Reporte de Fallas / Garantías'
    _inherit = ['mail.thread']

    # Campos principales
    codigo = fields.Char(string='Código', readonly=True, copy=False)
    name = fields.Char(
        string='Referencia',
        readonly=True,
        copy=False,
        help='Nombre o referencia del reporte. Se genera automáticamente.',
        default='Nuevo'
    )
    equipo = fields.Char(string='Desc. Equipo', required=True)
    equipo_id = fields.Many2one('product.product', string='Equipo', required=True)
    marca = fields.Char(string='Marca', required=True)
    serie = fields.Char(string='Serial', required=True)
    modelo = fields.Char(string='Modelo', required=True)
    cliente_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        domain=[('is_company', '=', True)]
    )
    finca = fields.Char(string='Finca', required=True)
    reportado_por = fields.Many2one(
        'res.users', string='Reportado por',
        default=lambda self: self.env.user,
        help="Usuario que reporta la falla", readonly=True
    )
    fecha_fabricacion = fields.Date(string='Fecha de Fabricación')
    fecha_falla = fields.Date(string='Fecha de la Falla')
    descripcion_falla = fields.Text(string='Descripción de la Falla')
    foto_ids = fields.One2many('quality.control.fallas.fotos', 'falla_id', string='Fotos')

    # Campo de Estado relacionado al proceso del módulo
    state = fields.Selection([
        ('borrador', 'Borrador'),
        ('revision', 'En Revisión'),
        ('proceso', 'En Proceso'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('finalizado', 'Finalizado')
    ], string="Estado", default='borrador')
    company_id = fields.Many2one(
        'res.company', 
        string="Compañía", 
        default = lambda self: self.env['res.company']._company_default_get('quality.control.fallas'),
        store=True, 
        readonly=True
    )
    codigo_proyecto = fields.Many2one(
        'account.analytic.account',
        string='Código Proyecto',
        help='Seleccione la cuenta analítica asociada al reporte.',
        domain="[('company_id', '=', company_id)]"
    )
    motivo_rechazo = fields.Text(string='Motivo de Rechazo')
    tipo_garantia = fields.Selection([
	    ('garantia_cliente', 'Garantía Cliente'),
	    ('garantia_proveedor', 'Garantía Proveedor')
	], string="Tipo de Garantía")
    @api.model
    def create(self, vals):
        if 'codigo' not in vals:
            vals['codigo'] = self.env['ir.sequence'].next_by_code('quality.control.fallas') or '0000'
        vals['name'] = vals.get('codigo')
        return super(QualityControlFallas, self).create(vals)

    @api.constrains('foto_ids')
    def _check_max_fotos(self):
        for record in self:
            if len(record.foto_ids) > 4:
                raise ValidationError("Solo se pueden agregar 4 fotos como máximo por reporte.")

    def get_record_url(self):
        """
        Retorna la URL completa del registro.
        Asegúrese de que el parámetro 'web.base.url' esté configurado con el dominio deseado.
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return '%sweb#id=%s&model=quality.control.fallas&view_type=form' % (base_url, self.id)

    def _send_state_change_email(self):
        """
        Envía un correo notificando el cambio de estado.
        Si el estado es 'revision', el correo se enviará a lgutierrez@gpsgroup.com.ec,
        de lo contrario, se envía al email del usuario que reportó la falla.
        Se presenta el contenido en un card y se incluye un botón para acceder al registro.
        """
        # Obtener el dominio base a través del metodo get_record_url (que lo utiliza internamente)
        for rec in self:
            if rec.state == 'revision':
                destinatario = "lgutierrez@gpsgroup.com.ec"
            else:
                destinatario = rec.reportado_por.partner_id.email if rec.reportado_por and rec.reportado_por.partner_id.email else False

            if destinatario:
                # Obtener la URL completa del registro
                record_url = rec.get_record_url()
                subject = f"Estado cambiado a: {dict(rec._fields['state'].selection).get(rec.state)}"
                body = f"""
                    <div style="max-width:600px; margin:0 auto; border:1px solid #ddd; border-radius:4px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">
                      <div style="background-color:#7b241c; padding:10px 20px; color:#fff; font-size:16px; font-weight:bold; border-top-left-radius:4px; border-top-right-radius:4px;">
                        Notificación de Cambio de Estado
                      </div>
                      <div style="padding:20px; font-family: Verdana; font-size: 14px; line-height:1.6;">
                        <p style="margin-bottom:10px;">Estimado/a <strong>{rec.reportado_por.name if rec.reportado_por else 'Usuario'}</strong>,</p>
                        <p style="margin-bottom:10px;">
                          Le informamos que el estado de su reporte de fallas con código 
                          <strong>{rec.codigo}</strong> ha cambiado a 
                          <strong>{dict(rec._fields['state'].selection).get(rec.state)}</strong>.
                        </p>
                        <p style="margin-bottom:20px;">Por favor, revise los detalles en el sistema.</p>
                        <div style="text-align:center; margin-bottom:20px;">
                          <a href="{record_url}" 
                             style="display: inline-block; padding:10px 20px; background-color:#7b241c; color:#fff; text-decoration:none; border-radius:4px;">
                            Ver Registro
                          </a>
                        </div>
                        <p style="margin-bottom:0;">Atentamente,<br/>El Equipo de Control de Calidad</p>
                      </div>
                    </div>
                """
                mail_values = {
                    'subject': subject,
                    'body_html': body,
                    'email_from': 'lgutierrez@gpsgroup.com.ec',
                    'email_to': destinatario,
                }
                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.send()

    def action_set_borrador(self):
        """Cambia el estado a 'Borrador' y envía notificación."""
        self.write({'state': 'borrador'})
        self._send_state_change_email()
        return True

    def action_set_revision(self):
        """Cambia el estado a 'En Revisión' y envía notificación."""
        self.write({'state': 'revision'})
        self._send_state_change_email()
        return True

    def action_set_proceso(self):
        """Cambia el estado a 'En Proceso' y envía notificación."""
        self.write({'state': 'proceso'})
        self._send_state_change_email()
        return True

    def action_set_aprobado(self):
        """Cambia el estado a 'Aprobado' y envía notificación."""
        self.write({'state': 'aprobado'})
        self._send_state_change_email()
        return True

    def action_set_rechazado(self):
        """Cambia el estado a 'Rechazado' y envía notificación."""
        self.write({'state': 'rechazado'})
        self._send_state_change_email()
        return True

    def action_set_finalizado(self):
        """Cambia el estado a 'Finalizado' y envía notificación."""
        self.write({'state': 'finalizado'})
        self._send_state_change_email()
        return True

    #Nuevo campo para enlazar la requisición
    requisition_id = fields.Many2one(
        'purchase.request',
        string='Requisición Generada',
        readonly=True,
        copy=False
    )

    def action_generar_requisicion(self):
	    """Genera una requisición de servicio con producto RFI003635"""
	    self.ensure_one()

	    # Buscar producto con default_code = "RFI003635"
	    producto = self.env['product.product'].search([('default_code', '=', 'RFI003635')], limit=1)
	    if not producto:
		    raise UserError(_("No existe el producto con código interno 'RFI003635'."))

	    if not self.codigo_proyecto:
		    raise UserError(_("Debe seleccionar un Código de Proyecto antes de generar la requisición."))

	    # Construir la distribución analítica
	    analytic_distribution = {self.codigo_proyecto.id: 100}

	    # Crear requisición
	    requisicion = self.env['purchase.request'].create({
		    'origin': self.name,
		    'requested_by': self.env.user.id,
		    'company_id': self.company_id.id,
		    'request_type': 'service',
		    'analytic_distribution': analytic_distribution,
		    'description': f"Requisición generada desde reporte de fallas {self.codigo}",
	    })

	    # Crear línea de requisición
	    self.env['purchase.request.line'].create({
		    'request_id': requisicion.id,
		    'product_id': producto.id,
		    'product_uom_id': producto.uom_id.id,
		    'product_qty': 1,
		    'name': producto.display_name,
		    'analytic_distribution': analytic_distribution,
	    })

	    # Relacionar con el reporte de fallas
	    self.requisition_id = requisicion.id

	    # Abrir la requisición recién creada
	    return {
		    'type': 'ir.actions.act_window',
		    'res_model': 'purchase.request',
		    'view_mode': 'form',
		    'res_id': requisicion.id,
	    }

class QualityControlFallasFotos(models.Model):
    _name = 'quality.control.fallas.fotos'
    _description = 'Fotos asociadas al reporte de fallas'

    falla_id = fields.Many2one('quality.control.fallas', string='Reporte de Falla')
    imagen = fields.Binary(string='Imagen', attachment=True)
    descripcion = fields.Char(string='Descripción', help='Breve descripción de la foto.')
