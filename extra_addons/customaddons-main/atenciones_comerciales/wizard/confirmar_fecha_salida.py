from odoo import api, fields, models
from odoo.exceptions import UserError

class ConfirmarFechaSalidaWizard(models.TransientModel):
    _name = 'confirmar.fecha.salida.wizard'
    _description = 'Confirmación por fecha de salida menor a 7 días'

    solicitud_id = fields.Many2one('solicitud.aprobacion.atenciones', string='Solicitud')
    mensaje = fields.Html(readonly=True)

    def action_confirmar(self):
        solicitud = self.solicitud_id
        solicitud.state = 'revision'

        # Enviar correo
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        form_url = f"{base_url}/web#id={solicitud.id}&model=solicitud.aprobacion.atenciones&view_type=form"

        body = f"""
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
                <p><strong>Número de Solicitud:</strong> {solicitud.name}</p>
                <p><strong>Solicitante:</strong> {solicitud.solicitante_id.name}</p>
                <p><strong>Fecha de Solicitud:</strong> {solicitud.fecha_solicitud.strftime('%d/%m/%Y') if solicitud.fecha_solicitud else ''}</p>
                <p style="color: #c0392b;"><strong>Advertencia:</strong> La fecha de salida ({solicitud.fecha_salida.strftime('%d/%m/%Y')}) es menor a 7 días desde la fecha de solicitud.</p>
                <p>La solicitud ha sido enviada para revisión anticipada.</p>
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
        """

        self.env['mail.mail'].create({
            'subject': f'{solicitud.name} - Solicitud en revisión anticipada',
            'body_html': body,
            'email_to': 'ooyague@gpsgroup.com.ec',
            'email_from': self.env.user.email,
        }).send()

        return {'type': 'ir.actions.act_window_close'}
