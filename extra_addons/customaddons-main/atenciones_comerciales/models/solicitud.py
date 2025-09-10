from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError
from datetime import timedelta
from odoo.exceptions import UserError
import base64

class SolicitudAprobacionAtenciones(models.Model):
    _name = 'solicitud.aprobacion.atenciones'
    _description = 'Solicitud de Aprobación de Atenciones Comerciales'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    # Campo para la secuencia (Número de Solicitud)
    name = fields.Char(string="Número de Solicitud", required=True, copy=False, readonly=True, default="Nuevo")
    # Campo de estado: registrado, a_aprobar, aprobado
    state = fields.Selection([
        ('registrado', 'Registrado'),
        ('revision', 'Revisión'),
        ('a_aprobar', 'A Aprobar'),
        ('aprobado', 'Aprobado'),
    ], string="Estado", default="registrado", tracking=True)
    # Campo de empresa y moneda
    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company, required=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='company_id.currency_id', store=True, readonly=True)
    # Otros campos
    check_confirmacion = fields.Boolean(
        string='Confirmación especial',
        help='Confirmación realizada por Aprobador o Presidente para omitir validación de los 7 días.'
    )
    solicitante_id = fields.Many2one('res.users', string='Solicitante', required=True, default=lambda self: self.env.uid)
    employee_id = fields.Many2one('hr.employee', string='Empleado', compute='_compute_employee_id', store=True)
    cargo = fields.Char(string='Cargo', compute='_compute_cargo_area', store=True)
    area = fields.Char(string='Área', compute='_compute_cargo_area', store=True)
    fecha_solicitud = fields.Date(string='Fecha de Solicitud', default=fields.Date.context_today, required=True)
    fecha_salida = fields.Date(string='Fecha de Salida', required=True)
    fecha_retorno = fields.Date(string='Fecha de Retorno', required=True)
    cliente_id = fields.Many2one('res.partner', string='Cliente', domain=[('is_company', '=', True)])
    ciudad = fields.Char(string='Ciudad')
    dias_viaje = fields.Integer(string='Días de Viaje', compute='_compute_dias_viaje', store=True)
    delegado_ids = fields.One2many('solicitud.aprobacion.atenciones.delegado', 'solicitud_id', string='Delegados')
    movilizacion_ids = fields.One2many('solicitud.aprobacion.atenciones.movilizacion', 'solicitud_id', string='Gastos de Movilización')
    alimentacion_ids = fields.One2many('solicitud.aprobacion.atenciones.alimentacion', 'solicitud_id', string='Gastos de Alimentación')
    total_movilizacion = fields.Float(string='Total Movilización', compute='_compute_total_movilizacion', store=True)
    total_alimentacion = fields.Float(string='Total Alimentación', compute='_compute_total_alimentacion', store=True)
    total_solicitud = fields.Float(string='Total Solicitud', compute='_compute_total_solicitud', store=True)

    @api.depends('solicitante_id.employee_id')
    def _compute_employee_id(self):
        for rec in self:
            # Se asigna el empleado relacionado al solicitante (si existe)
            rec.employee_id = rec.solicitante_id.employee_id

    @api.depends('solicitante_id.employee_id.job_id', 'solicitante_id.employee_id.department_id')
    def _compute_cargo_area(self):
        for rec in self:
            if rec.solicitante_id and rec.solicitante_id.employee_id:
                rec.cargo = rec.solicitante_id.employee_id.job_id.name or 'No asignado'
                rec.area = rec.solicitante_id.employee_id.department_id.name or 'No asignado'

    @api.depends('fecha_salida', 'fecha_retorno')
    def _compute_dias_viaje(self):
        for rec in self:
            if rec.fecha_salida and rec.fecha_retorno:
                delta = rec.fecha_retorno - rec.fecha_salida
                rec.dias_viaje = delta.days if delta.days >= 0 else 0
            else:
                rec.dias_viaje = 0

    @api.depends('movilizacion_ids.monto')
    def _compute_total_movilizacion(self):
        for rec in self:
            rec.total_movilizacion = sum(line.monto for line in rec.movilizacion_ids)

    @api.depends('alimentacion_ids.monto')
    def _compute_total_alimentacion(self):
        for rec in self:
            rec.total_alimentacion = sum(line.monto for line in rec.alimentacion_ids)

    @api.depends('total_movilizacion', 'total_alimentacion')
    def _compute_total_solicitud(self):
        for rec in self:
            rec.total_solicitud = rec.total_movilizacion + rec.total_alimentacion

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') in ['Nuevo', False]:
            vals['name'] = self.env['ir.sequence'].next_by_code('solicitud.aprobacion.atenciones') or 'Nuevo'
        return super(SolicitudAprobacionAtenciones, self).create(vals)

    # @api.constrains('fecha_salida', 'fecha_solicitud')
    # def _check_fecha_salida(self):
    #     for rec in self:
    #         if rec.fecha_solicitud and rec.fecha_salida:
    #             if rec.fecha_salida < rec.fecha_solicitud + timedelta(days=7):
    #                 raise ValidationError("La fecha de salida debe ser al menos 7 días después de la fecha de solicitud.")

    @api.constrains('fecha_retorno', 'fecha_salida')
    def _check_fecha_retorno(self):
        for rec in self:
            if rec.fecha_salida and rec.fecha_retorno:
                if rec.fecha_retorno < rec.fecha_salida + timedelta(days=1):
                    raise ValidationError("La fecha de retorno debe ser al menos un día después de la fecha de salida.")

    def _validar_lineas_incompletas(self):
        for rec in self:
            vacios = []
            # Validar delegados (siempre obligatorio)
            if not rec.delegado_ids:
                vacios.append("Delegados")
            # Si hay delegados, debe haber al menos una línea en movilización o alimentación
            if rec.delegado_ids and not (rec.movilizacion_ids or rec.alimentacion_ids):
                vacios.append("Movilización o Alimentación")
            return vacios

    # Restricción al guardar o modificar
    @api.constrains('delegado_ids','movilizacion_ids','alimentacion_ids')
    def _check_lineas_registro(self):
        for rec in self:
            vacios = rec._validar_lineas_incompletas()
            if vacios:
                raise ValidationError(
                    "Debe registrar al menos una línea en cada uno de los siguientes bloques obligatorios: Delegados, Movilización o Alimentación.\n"
                    f"Faltan líneas en: {', '.join(vacios)}."
                )

    # Validación para los botones de cambio de estado
    def _check_lineas_obligatorias(self):
        for rec in self:
            vacios = rec._validar_lineas_incompletas()
            if vacios:
                raise ValidationError(
                    "No puede cambiar el estado de la solicitud sin haber completado todos los bloques obligatorios.\n"
                    f"Faltan líneas en: {', '.join(vacios)}."
                )

    def action_send_for_approval(self):
        self.ensure_one()
        self._check_lineas_obligatorias()

        dias_diferencia = (self.fecha_salida - self.fecha_solicitud).days
        if dias_diferencia < 7 and not self.check_confirmacion:
            return {
                'name': 'Confirmación Fecha de Salida',
                'type': 'ir.actions.act_window',
                'res_model': 'confirmar.fecha.salida.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_solicitud_id': self.id,
                    'default_mensaje': (
                        f"<p><strong>Atención:</strong> La fecha de salida ({self.fecha_salida.strftime('%d/%m/%Y')}) "
                        f"es menor a 7 días desde la fecha de solicitud ({self.fecha_solicitud.strftime('%d/%m/%Y')}).</p>"
                        "<p>¿Desea continuar de todos modos?</p>"
                    ),
                }
            }

        for rec in self:
            rec.state = 'a_aprobar'

            # Reporte PDF
            report = self.env.ref('atenciones_comerciales.report_solicitud_aprobacion_atenciones',
                                  raise_if_not_found=False)
            if not report:
                continue  # Saltar si no hay reporte

            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(report.report_name, rec.id)

            attachment = self.env['ir.attachment'].create({
                'name': f'Solicitud_{rec.name}.pdf',
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': rec._name,
                'res_id': rec.id,
                'mimetype': 'application/pdf',
            })

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            form_url = f"{base_url}/web#id={rec.id}&model=solicitud.aprobacion.atenciones&view_type=form"

            mail_values = {
                'subject': f'{rec.name} - Solicitud de Atenciones Comerciales',
                'body_html': f"""
                <div style="font-family: Verdana, sans-serif; background-color: #f4f4f4; padding: 30px;">
                  <table align="center" width="600" cellpadding="0" cellspacing="0"
                         style="background: #ffffff; border-radius: 10px; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1); border-collapse: collapse;">
                    <tr>
                      <td style="background-color: #a93226; padding: 20px; text-align: center; color: #ffffff;
                                 font-size: 20px; font-weight: bold; border-top-left-radius: 10px; border-top-right-radius: 10px;">
                        Solicitud de Atenciones Comerciales
                      </td>
                    </tr>
                    <tr>
                      <td style="padding: 25px; color: #333333; font-size: 14px; line-height: 1.6;">
                        <p><strong>Número de Solicitud:</strong> {rec.name}</p>
                        <p><strong>Solicitante:</strong> {rec.solicitante_id.name}</p>
                        <p><strong>Fecha de Solicitud:</strong> {rec.fecha_solicitud.strftime('%d/%m/%Y') if rec.fecha_solicitud else ''}</p>
                        <p>Se ha generado una nueva solicitud. Adjunto encontrará el documento PDF con el detalle completo.</p>
                        <div style="text-align: center; margin-top: 30px;">
                          <a href="{form_url}" target="_blank"
                             style="display: inline-block; padding: 12px 24px; background-color: #a93226; color: #ffffff;
                                    border-radius: 5px; text-decoration: none; font-size: 14px;">
                            Ver Solicitud en Odoo
                          </a>
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding: 15px; text-align: center; color: #888888; font-size: 12px; border-top: 1px solid #dddddd;">
                        Este mensaje ha sido generado automáticamente por el sistema.
                      </td>
                    </tr>
                  </table>
                </div>
                """,
                'email_to': 'aarriola@gpsgroup.com.ec',
                'email_from': self.env.user.email,
                'attachment_ids': [attachment.id],
            }

            self.env['mail.mail'].create(mail_values).send()

            # Agregar mensaje en el chatter
            rec.message_post(
                body="La solicitud fue enviada por correo para su aprobación.",
                attachment_ids=[attachment.id]
            )

        return True

    def action_approve(self):
        self._check_lineas_obligatorias()
        for rec in self:
            if rec.state != 'a_aprobar':
                raise ValidationError("La solicitud debe estar en estado 'A Aprobar' para poder aprobarse.")
            rec.state = 'aprobado'
        return True

    def action_reset_to_registrado(self):
        for rec in self:
            rec.state = 'registrado'
        return True

    # Validación al duplicar/copy
    def copy(self, default=None):
        for rec in self:
            vacios = rec._validar_lineas_incompletas()
            if vacios:
                raise UserError(
                    "No puede duplicar esta solicitud porque falta información obligatoria en los siguientes bloques:\n"
                    f"{', '.join(vacios)}."
                )
        return super(SolicitudAprobacionAtenciones, self).copy(default)

    def unlink(self):
        if not self.env.user.has_group('atenciones_comerciales.group_administrador'):
            raise AccessError("Solo los usuarios con permisos de Administrador pueden eliminar una solicitud.")
        return super(SolicitudAprobacionAtenciones, self).unlink()

# Modelos secundarios: Delegado, Movilización, Alimentación
class SolicitudAprobacionAtencionesDelegado(models.Model):
    _name = 'solicitud.aprobacion.atenciones.delegado'
    _description = 'Delegados para Solicitud de Atenciones Comerciales'

    name = fields.Char(string='Nombre del Delegado', required=True)
    puesto = fields.Char(string='Puesto / Cargo', required=True)
    solicitud_id = fields.Many2one('solicitud.aprobacion.atenciones', string='Solicitud')

class SolicitudAprobacionAtencionesMovilizacion(models.Model):
    _name = 'solicitud.aprobacion.atenciones.movilizacion'
    _description = 'Gastos de Movilización de la Solicitud'

    concepto = fields.Char(string='Concepto', required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='solicitud_id.currency_id', store=True, readonly=True)
    monto = fields.Monetary(string='Monto', currency_field='currency_id', required=True)
    observaciones = fields.Text(string='Observaciones')
    solicitud_id = fields.Many2one('solicitud.aprobacion.atenciones', string='Solicitud')

class SolicitudAprobacionAtencionesAlimentacion(models.Model):
    _name = 'solicitud.aprobacion.atenciones.alimentacion'
    _description = 'Gastos de Alimentación de la Solicitud'

    concepto = fields.Char(string='Concepto', required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', related='solicitud_id.currency_id', store=True, readonly=True)
    monto = fields.Monetary(string='Monto', currency_field='currency_id', required=True)
    observaciones = fields.Text(string='Observaciones')
    solicitud_id = fields.Many2one('solicitud.aprobacion.atenciones', string='Solicitud')