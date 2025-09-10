from io import BytesIO
import xlsxwriter
import base64
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError

class ListaSolicitud(models.Model):
    _name = 'physical_security.lista_solicitud'
    _description = 'Lista de Solicitud para Seguridad Física'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    codigo = fields.Char(string='Código', required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].sudo().next_by_code('physical_security.lista_solicitud') or 'Nuevo')
    name = fields.Char('Nombre', compute='_compute_name', store=True)
    fecha_actual = fields.Date(string='Fecha de Solicitud', default=fields.Date.context_today, required=True, tracking=True)
    fecha_estimada = fields.Date(string='Fecha Estimada', required=True, tracking=True)
    responsable = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.uid, tracking=True)
    contratista = fields.Many2one('res.partner', string='Contratista', required=True, domain=[('company_type', '=', 'company')], tracking=True)
    cuenta_analitica = fields.Many2one('account.analytic.account', string='Cuenta Analítica', tracking=True)
    line_ids = fields.One2many('physical_security.lista_solicitud_line', 'solicitud_id', string='Personas')
    personal_ids = fields.Many2many('physical_security.personal_contratista', string='Personas', compute='_get_personal_ids')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('solicitud_enviada', 'Solicitud Enviada'),
        ('solicitud_revisada', 'Solicitud Revisada'),
    ], string='Estado', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        # Asegurar que siempre tengamos un código secuencial
        if not vals.get('codigo') or vals.get('codigo') == 'Nuevo':
            vals['codigo'] = self.env['ir.sequence'] \
                                 .sudo().next_by_code('physical_security.lista_solicitud') or 'Nuevo'
        return super(ListaSolicitud, self).create(vals)

    def action_envia_solicitud(self):
        """Pasa el estado a 'solicitud_enviada' y envía un correo de notificación."""
        for rec in self:
            rec.state = 'solicitud_enviada'

            # Construir la URL al registro
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            link = f"{base_url}/web#id={rec.id}&model=physical_security.lista_solicitud&view_type=form"

            # Listado de personas en HTML
            person_items = ''.join(
                f"<li style='margin-bottom:6px;'>{line.personal_id.name}</li>"
                for line in rec.line_ids
            )

            # Cuerpo del correo con fuente Verdana y diseño mejorado en formato tabla para mejor compatibilidad
            body = (
                '<div style="font-family:Verdana, sans-serif; background-color:#f9f9f9; padding:30px;">'
                '  <table align="center" width="600" cellpadding="0" cellspacing="0" '
                'style="background:#ffffff; border-radius:10px; box-shadow:0 4px 16px rgba(0,0,0,0.1); '
                'border-collapse:collapse;">'
                '    <tr>'
                '      <td style="background-color:#a93226; padding:20px; text-align:center; '
                'color:#ffffff; font-size:22px; font-weight:bold;">'
                '        Solicitud de Seguridad Física'
                '      </td>'
                '    </tr>'
                '    <tr>'
                '      <td style="padding:20px; color:#333333; font-size:16px; line-height:1.5;">'
                f'        <p><strong>Nombre:</strong> {rec.codigo}</p>'
                f'        <p><strong>Fecha Solicitud:</strong> {rec.fecha_actual}</p>'
                f'        <p><strong>Fecha Estimada:</strong> {rec.fecha_estimada}</p>'
                f'        <p><strong>Responsable:</strong> {rec.responsable.name}</p>'
                f'        <p><strong>Contratista:</strong> {rec.contratista.name}</p>'
                f'        <p><strong>Cuenta Analítica:</strong> {rec.cuenta_analitica.name or ""}</p>'
                '        <p><strong>Personal:</strong></p>'
                '        <ul style="padding-left:20px; margin:10px 0;">'
                f'          {person_items}'
                '        </ul>'
                '        <div style="text-align:center; margin-top:30px;">'
                f'          <a href="{link}" '
                'style="display:inline-block; padding:12px 30px; background-color:#a93226; '
                'color:#ffffff; border-radius:5px; text-decoration:none; font-size:18px;">'
                '            Ver Solicitud'
                '          </a>'
                '        </div>'
                '      </td>'
                '    </tr>'
                '  </table>'
                '</div>'
            )

            # Buscar el servidor de correo “Correo de permisos”
            mail_server = self.env['ir.mail_server'].sudo().search(
                [('name', '=', 'Correo de permisos')], limit=1
            )

            # Preparar valores del mail
            mail_vals = {
                'email_from': rec.responsable.partner_id.email or self.env.user.company_id.email,
                'email_to': 'gzambrano@gpsgroup.com.ec',
                'subject': f"Nueva Lista de Solicitud: {rec.name}",
                'body_html': body,
                'auto_delete': True,
            }
            if mail_server:
                mail_vals['mail_server_id'] = mail_server.id

            # Crear y enviar el mail con sudo()
            self.env['mail.mail'].sudo().create(mail_vals).send()
        return True

    def action_revisar_solicitud(self):
        """
        - Marca estado 'solicitud_revisada'
        - Procesa cada línea:
            * aprobado_seguridad+generar_doping → crea prueba_doping
            * solo aprobado_seguridad → crea/actualiza permiso con estado 'aprobado_sf'
        - Genera Excel con encabezado de datos de la solicitud + tabla de líneas
        - Envía correo con diseño en "card" y adjunto
        """
        permiso_obj = self.env['permisos_ingreso.personal']
        for rec in self:
            rec.state = 'solicitud_revisada'

            # Procesar líneas
            for line in rec.line_ids:
                if line.aprobado_seguridad:
                    if line.generar_doping and line.fecha_doping:
                        dp = self.env['physical_security.pruebas_doping'].search(
                            [('fecha_doping', '=', line.fecha_doping)], limit=1
                        ) or self.env['physical_security.pruebas_doping'].create({
                            'fecha_doping': line.fecha_doping
                        })
                        exists = self.env['physical_security.pruebas_doping_line'].search([
                            ('doping_id', '=', dp.id),
                            ('personal_id', '=', line.personal_id.id)
                        ], limit=1)
                        if not exists:
                            self.env['physical_security.pruebas_doping_line'].create({
                                'doping_id': dp.id,
                                'referencia': rec.id,
                                'personal_id': line.personal_id.id,
                                'responsable_id': rec.responsable.id,
                            })
                    else:
                        vals = {
                            'cedula':    line.personal_id.cedula,
                            'apellidos': line.personal_id.apellidos,
                            'nombres':   line.personal_id.nombres,
                            'estado':    'aprobado_sf',
                        }
                        existing = permiso_obj.search([
                            ('cedula',    '=', vals['cedula']),
                            ('apellidos', '=', vals['apellidos']),
                            ('nombres',   '=', vals['nombres']),
                        ], limit=1)
                        if existing:
                            existing.write({'estado': 'aprobado_sf'})
                        else:
                            permiso_obj.create(vals)

            # Generar Excel
            output   = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})

            # Formatos
            title_fmt    = workbook.add_format({
                'bold': True, 'font_size': 18, 'align': 'center',
                'valign': 'vcenter', 'font_name': 'Verdana',
                'bg_color': '#4F81BD', 'color': '#ffffff'
            })
            info_lbl_fmt = workbook.add_format({
                'bold': True, 'font_name': 'Verdana', 'bg_color': '#F2F2F2',
                'border': 1, 'valign': 'vcenter'
            })
            info_val_fmt = workbook.add_format({
                'text_wrap': True, 'font_name': 'Verdana',
                'border': 1, 'valign': 'vcenter'
            })
            hdr_fmt      = workbook.add_format({
                'bold': True, 'bg_color': '#DCE6F1', 'font_name': 'Verdana',
                'border': 1, 'align': 'center', 'valign': 'vcenter'
            })
            data_fmt     = workbook.add_format({
                'text_wrap': True, 'font_name': 'Verdana',
                'border': 1, 'valign': 'top'
            })

            sheet = workbook.add_worksheet("Solicitud")
            sheet.freeze_panes(4, 1)

            # Título
            sheet.merge_range(0, 0, 0, 6, f"SOLICITUD {rec.codigo}", title_fmt)

            # Datos de la solicitud
            info = [
                ("Código",           rec.codigo),
                ("Fecha Solicitud",  rec.fecha_actual.strftime('%Y-%m-%d')),
                ("Fecha Estimada",   rec.fecha_estimada.strftime('%Y-%m-%d')),
                ("Responsable",      rec.responsable.name),
                ("Contratista",      rec.contratista.name),
                ("Cuenta Analítica", rec.cuenta_analitica.name or ""),
            ]
            for i, (lbl, val) in enumerate(info, start=1):
                sheet.write(i, 0, lbl, info_lbl_fmt)
                sheet.merge_range(i, 1, i, 6, val, info_val_fmt)

            # Encabezado de tabla de líneas
            start = len(info) + 2
            headers = [
                'Cédula', 'Apellidos', 'Nombres', 'Cargo',
                'Aprobado SF', 'Generar Doping', 'Fecha Doping'
            ]
            for col, h in enumerate(headers):
                sheet.write(start, col, h, hdr_fmt)

            # Filas de datos
            for r, line in enumerate(rec.line_ids, start=start + 1):
                vals = [
                    line.personal_id.cedula,
                    line.personal_id.apellidos,
                    line.personal_id.nombres,
                    line.personal_id.cargo,
                    'Sí' if line.aprobado_seguridad else 'No',
                    'Sí' if line.generar_doping else 'No',
                    line.fecha_doping.strftime('%Y-%m-%d') if line.fecha_doping else 'Sin asignar'
                ]
                for c, v in enumerate(vals):
                    sheet.write(r, c, v, data_fmt)

            # Auto-ajustar ancho
            col_widths = [len(h) for h in headers]
            total_rows = start + len(rec.line_ids) + 1
            for col in range(len(headers)):
                for row in range(start, total_rows):
                    cell = sheet.table.get((row, col))
                    if cell:
                        col_widths[col] = max(col_widths[col], len(str(cell)))
                sheet.set_column(col, col, col_widths[col] + 5)

            workbook.close()
            output.seek(0)
            data_b64 = base64.b64encode(output.read()).decode('ascii')

            # Crear attachment
            attachment = self.env['ir.attachment'].create({
                'name':      f'Listado_{rec.codigo}.xlsx',
                'type':      'binary',
                'datas':     data_b64,
                'res_model': rec._name,
                'res_id':    rec.id,
                'mimetype':  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })

            # Enviar correo en "card" HTML
            base_url  = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            form_link = f"{base_url}/web#id={rec.id}&model=physical_security.lista_solicitud&view_type=form"
            body_html = (
                '<div style="font-family:Verdana,sans-serif;background:#f0f0f0;padding:30px;">'
                '  <table align="center" width="600" cellpadding="0" cellspacing="0" '
                'style="background:#fff;border-radius:8px;box-shadow:0 3px 10px rgba(0,0,0,0.1);">'
                '    <tr>'
                '      <td style="background:#a93226;padding:15px;color:#fff;font-size:20px;text-align:center;">'
                f'        Solicitud {rec.codigo} Revisada'
                '      </td>'
                '    </tr>'
                '    <tr>'
                '      <td style="padding:20px;color:#333;font-size:14px;line-height:1.6;">'
                f'        <p>Hola <strong>{rec.responsable.name}</strong>,</p>'
                '        <p>Tu solicitud ha sido <strong>revisada</strong>. '
                'Adjunto encontrarás el listado de personal.</p>'
                '        <div style="text-align:center;margin-top:25px;">'
                f'          <a href="{form_link}" '
                'style="display:inline-block;padding:12px 28px;background:#a93226;'
                'color:#fff;border-radius:5px;text-decoration:none;font-size:16px;">'
                'Ver Solicitud en Odoo'
                '</a>'
                '        </div>'
                '        <p style="margin-top:30px;">Saludos,<br/>'
                'Departamento de Seguridad Física</p>'
                '      </td>'
                '    </tr>'
                '  </table>'
                '</div>'
            )
            partner_email = rec.responsable.partner_id.email
            if not partner_email:
                raise ValidationError(_("El responsable no tiene correo configurado."))
            mail_vals = {
                'email_from':    self.env.user.company_id.email or self.env.user.email,
                'email_to':      partner_email,
                'subject':       _('Solicitud %s revisada con listado adjunto') % rec.codigo,
                'body_html':     body_html,
                'attachment_ids': [(4, attachment.id)],
                'auto_delete':   True,
            }
            mail_server = self.env['ir.mail_server'].sudo().search(
                [('name', '=', 'Correo de permisos')], limit=1
            )
            if mail_server:
                mail_vals['mail_server_id'] = mail_server.id
            self.env['mail.mail'].sudo().create(mail_vals).send()

    def action_reset_draft(self):
        """Vuelve al estado borrador"""
        for rec in self:
            rec.state = 'draft'

    @api.depends('line_ids')
    @api.onchange('line_ids')
    def _get_personal_ids(self):
        for brw_each in self:
            brw_each.personal_ids = brw_each.line_ids.mapped('personal_id')

    @api.depends('codigo', 'cuenta_analitica', 'responsable', 'contratista')
    def _compute_name(self):
        for rec in self:
            parts = rec.responsable.name.split()
            if len(parts) >= 2:
                responsable_display = f"{parts[0]} {parts[2]}"
            else:
                responsable_display = rec.responsable.name
            rec.name = (
                f"{rec.codigo}: {rec.cuenta_analitica.name} - "
                f"{responsable_display} - {rec.contratista.name}"
            )

class ListaSolicitudLine(models.Model):
    _name = 'physical_security.lista_solicitud_line'
    _description = 'Línea de Lista de Solicitud'

    solicitud_id = fields.Many2one('physical_security.lista_solicitud', string='Solicitud', required=True, ondelete='cascade')
    personal_id = fields.Many2one('physical_security.personal_contratista', string='Contratista', required=True)
    cargo = fields.Char(string='Cargo', related='personal_id.cargo', readonly=True, store=True)
    aprobado_seguridad = fields.Boolean(string='Aprobado SF')
    generar_doping = fields.Boolean(string='Generar Doping')
    fecha_doping = fields.Date(string='Fecha Doping')

    @api.constrains('fecha_doping')
    def _check_fecha_doping_future(self):
        for rec in self:
            if rec.fecha_doping and rec.fecha_doping <= fields.Date.today():
                raise ValidationError(
                    _("La Fecha de Doping (%s) debe ser posterior a la fecha actual.") %
                    rec.fecha_doping.strftime('%d-%m-%Y')
                )

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
        lista_negra_obj.create({
            'cedula': self.personal_id.cedula,
            'apellidos': self.personal_id.apellidos,
            'nombres': self.personal_id.nombres,
        })
        return True

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