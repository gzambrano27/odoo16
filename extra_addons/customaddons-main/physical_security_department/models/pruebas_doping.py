from io import BytesIO
import xlsxwriter
import base64
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError

class PruebasDoping(models.Model):
    _name = 'physical_security.pruebas_doping'
    _description = 'Pruebas Doping'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    codigo = fields.Char(string='Código', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].sudo().next_by_code('physical_security.pruebas_doping') or _('Nuevo'))
    name = fields.Char('Nombre', compute='_compute_name', store=True)
    fecha_doping = fields.Date(string='Fecha de Doping', required=True, tracking=True)
    line_ids = fields.One2many('physical_security.pruebas_doping_line', 'doping_id', string='Personal')
    personal_ids = fields.Many2many('physical_security.personal_contratista', string='Personas',compute='_get_personal_ids')
    state = fields.Selection([
        ('en_proceso', 'En Proceso'),
        ('doping_realizado', 'Doping Realizado'),
    ], string='Estado', default='en_proceso', tracking=True)

    def action_start_proceso(self):
        """Marca la prueba como En Proceso"""
        for rec in self:
            rec.state = 'en_proceso'

    def action_complete_doping(self):
        """
        Marca la prueba como Doping Realizado, crea en permisos_ingreso.personal
        los registros aprobados, genera un Excel con los datos de la prueba
        y envía un único correo a todos los responsables.
        """
        for rec in self:
            # 1) Cambiar estado y crear permisos
            personal_permiso_obj = self.env['permisos_ingreso.personal']
            responsables_emails = set()
            rec.state = 'doping_realizado'
            for line in rec.line_ids:
                if line.aprobado_doping:
                    responsables_emails.add(line.responsable_id.partner_id.email or '')
                    existing = personal_permiso_obj.search([
                        ('cedula', '=', line.personal_id.cedula),
                        ('apellidos', '=', line.personal_id.apellidos),
                        ('nombres', '=', line.personal_id.nombres),
                    ], limit=1)
                    if existing:
                        # Si ya existe, actualizamos su estado
                        existing.write({'estado': 'aprobado_sf'})
                    else:
                        # Si no existe, lo creamos
                        personal_permiso_obj.create({
                            'cedula': line.personal_id.cedula,
                            'apellidos': line.personal_id.apellidos,
                            'nombres': line.personal_id.nombres,
                            'estado': 'aprobado_sf',
                        })

            # 2) Generar Excel en memoria
            output   = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            # Formatos
            title_fmt    = workbook.add_format({
                'bold': True, 'font_size': 16, 'align': 'center',
                'valign': 'vcenter', 'font_name': 'Verdana',
                'bg_color': '#4F81BD', 'color': '#ffffff'
            })
            hdr_fmt      = workbook.add_format({
                'bold': True, 'bg_color': '#DCE6F1', 'font_name': 'Verdana',
                'border': 1, 'align': 'center', 'valign': 'vcenter'
            })
            data_fmt     = workbook.add_format({
                'text_wrap': True, 'font_name': 'Verdana', 'border': 1,
                'valign': 'top'
            })

            sheet = workbook.add_worksheet("Doping")
            sheet.set_column(0, 0, 12)
            sheet.set_column(1, 1, 20)
            sheet.set_column(2, 2, 20)
            sheet.set_column(3, 3, 15)
            sheet.set_column(4, 4, 18)
            sheet.set_column(5, 5, 12)

            # Título combinado
            sheet.merge_range(0, 0, 0, 6, f"PRUEBA DOPING {rec.codigo}", title_fmt)

            # Datos de la prueba
            sheet.write(1, 0, "Código", hdr_fmt)
            sheet.merge_range(1, 1, 1, 6, rec.codigo, data_fmt)
            sheet.write(2, 0, "Fecha Doping", hdr_fmt)
            sheet.merge_range(2, 1, 2, 6, rec.fecha_doping.strftime('%Y-%m-%d'), data_fmt)
            sheet.write(3, 0, "Estado", hdr_fmt)
            sheet.merge_range(3, 1, 3, 6, dict(self._fields['state'].selection).get(rec.state), data_fmt)

            # Encabezados de tabla de líneas
            headers = ['Cédula', 'Apellidos', 'Nombres', 'Cargo', 'Responsable', 'Aprobado', 'Asistencia']
            row0 = 4
            for col, h in enumerate(headers):
                sheet.write(row0, col, h, hdr_fmt)

            # Preparar lista de anchos basados en encabezados
            col_widths = [len(h) for h in headers]

            for idx, line in enumerate(rec.line_ids, start=row0 + 1):
                vals = [
                    line.personal_id.cedula,
                    line.personal_id.apellidos,
                    line.personal_id.nombres,
                    line.cargo,
                    line.responsable_id.name or '',
                    'Sí' if line.aprobado_doping else 'No',
                    'Sí' if line.asistencia else 'No',
                ]
                for col, v in enumerate(vals):
                    sheet.write(idx, col, v, data_fmt)

            # Auto-ajustar ancho de columnas con un padding extra
            for col, width in enumerate(col_widths):
                sheet.set_column(col, col, width + 5)

            workbook.close()
            output.seek(0)
            data_b64 = base64.b64encode(output.read()).decode('ascii')

            # 3) Crear attachment
            attachment = self.env['ir.attachment'].create({
                'name':      f'PruebaDoping_{rec.codigo}.xlsx',
                'type':      'binary',
                'datas':     data_b64,
                'res_model': rec._name,
                'res_id':    rec.id,
                'mimetype':  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })

            # 4) Preparar y enviar correo
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            link = f"{base_url}/web#id={rec.id}&model=physical_security.pruebas_doping&view_type=form"
            to_emails = ",".join(filter(None, responsables_emails)) or self.env.user.company_id.email
            body_html = (
                '<div style="font-family:Verdana,sans-serif;background:#f0f0f0;padding:20px;">'
                '  <table align="center" width="600" cellpadding="0" cellspacing="0" '
                'style="background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">'
                '    <tr><td style="background:#a93226;padding:15px;color:#fff;font-size:18px;text-align:center;">'
                f'      Prueba Doping {rec.codigo} Realizada'
                '    </td></tr>'
                '    <tr><td style="padding:20px;color:#333;font-size:14px;line-height:1.5;">'
                f'      Se ha completado la prueba de doping con código <strong>{rec.codigo}</strong> '
                f'para la fecha {rec.fecha_doping}.<br/><br/>'
                '      Adjuntamos un informe en Excel con los detalles.'
                '      <div style="text-align:center;margin-top:20px;">'
                f'        <a href="{link}" '
                'style="display:inline-block;padding:10px 20px;background:#a93226;'
                'color:#fff;border-radius:5px;text-decoration:none;">'
                'Ver Prueba en Odoo'
                '</a>'
                '      </div>'
                '    </td></tr>'
                '  </table>'
                '</div>'
            )
            mail_vals = {
                'email_from': self.env.user.company_id.email or self.env.user.email,
                'email_to':   to_emails,
                'subject':    _('Prueba Doping %s realizada') % rec.codigo,
                'body_html':  body_html,
                'attachment_ids': [(4, attachment.id)],
                'auto_delete': True,
            }
            mail_server = self.env['ir.mail_server'].sudo().search(
                [('name', '=', 'Correo de permisos')], limit=1)
            if mail_server:
                mail_vals['mail_server_id'] = mail_server.id

            self.env['mail.mail'].sudo().create(mail_vals).send()

        return True

    @api.model
    def create(self, vals):
        if not vals.get('codigo') or vals.get('codigo') == _('Nuevo'):
            vals['codigo'] = self.env['ir.sequence'] \
                                 .sudo().next_by_code('physical_security.pruebas_doping') or _('Nuevo')
        return super().create(vals)

    @api.depends('fecha_doping', 'codigo')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.codigo} – Prueba Doping {record.fecha_doping}"

    @api.depends('line_ids')
    @api.onchange('line_ids')
    def _get_personal_ids(self):
        for brw_each in self:
            personal_ids = brw_each.line_ids.mapped('personal_id')
            brw_each.personal_ids = personal_ids

    def action_crear_personal_permiso(self):
        """
        Crea en el modelo permisos_ingreso.personal los registros para los que tienen
        aprobado la prueba de doping, asignando también el estado 'aprobado_sf'.
        """
        personal_permiso_obj = self.env['permisos_ingreso.personal']
        for line in self.line_ids:
            if line.aprobado_doping:
                existing = personal_permiso_obj.search([
                    ('cedula', '=', line.personal_id.cedula),
                    ('apellidos', '=', line.personal_id.apellidos),
                    ('nombres', '=', line.personal_id.nombres)
                ], limit=1)
                if not existing:
                    personal_permiso_obj.create({
                        'cedula': line.personal_id.cedula,
                        'apellidos': line.personal_id.apellidos,
                        'nombres': line.personal_id.nombres,
                        'estado': 'aprobado_sf',  # nuevo campo estado
                    })
        return True

class PruebasDopingLine(models.Model):
    _name = 'physical_security.pruebas_doping_line'
    _description = 'Línea de Pruebas Doping'

    doping_id = fields.Many2one('physical_security.pruebas_doping', string='Prueba Doping', required=True, ondelete='cascade')
    referencia = fields.Many2one('physical_security.lista_solicitud', string='Referencia de Solicitud')
    personal_id = fields.Many2one('physical_security.personal_contratista', string='Contratista', required=True)
    cargo = fields.Char(string='Cargo', related='personal_id.cargo', readonly=True, store=True)
    responsable_id = fields.Many2one('res.users', string='Responsable', readonly=True)
    aprobado_doping = fields.Boolean(string='Aprobado PD')
    asistencia = fields.Boolean(string='Asistencia')

    @api.onchange('aprobado_doping')
    def _onchange_aprobado(self):
        # Si apruebo la prueba, marco asistencia automáticamente
        for rec in self:
            if rec.aprobado_doping:
                rec.asistencia = True

    def action_send_to_blacklist(self):
        """
        Envía el personal a la lista negra (modelo permisos_ingreso.lista_negra)
        validando que no exista ya un registro con la misma cédula, apellidos y nombres.
        """
        lista_negra_obj = self.env['permisos_ingreso.lista_negra']
        existing = lista_negra_obj.search([
            ('cedula', '=', self.personal_id.cedula),
            ('apellidos', '=', self.personal_id.apellidos),
            ('nombres', '=', self.personal_id.nombres)
        ], limit=1)
        if existing:
            raise ValidationError(_("El personal %s ya está en la lista negra.") % (self.personal_id.name_get()[0][1]))
        else:
            lista_negra_obj.create({
                'cedula': self.personal_id.cedula,
                'apellidos': self.personal_id.apellidos,
                'nombres': self.personal_id.nombres,
            })
        return True

    def action_go_to_solicitud(self):
        """Abre el formulario de la solicitud de origen."""
        self.ensure_one()
        if not self.referencia:
            raise ValidationError(_("No hay Solicitud asociada a esta línea."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Solicitud %s') % self.referencia.codigo,
            'res_model': 'physical_security.lista_solicitud',
            'res_id': self.referencia.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_enlace_documento(self):
        """Abre en una nueva pestaña el enlace almacenado en el registro de PersonalContratista."""
        self.ensure_one()
        url = self.personal_id.enlace_documento
        if not url:
            raise ValidationError(_("El Personal Contratista no tiene un enlace asociado."))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }