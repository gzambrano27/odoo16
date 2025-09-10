import base64
import io
import pytz
from datetime import datetime
# Importa las clases y módulos necesarios de Odoo
from odoo import models, fields, api, _
# Importa la excepción ValidationError para manejar errores de validación personalizados
from odoo.exceptions import ValidationError
from odoo.exceptions import AccessError, UserError
from datetime import date, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import xlsxwriter

# Define el modelo 'Permiso', que representa un permiso de ingreso en el sistema
class Permiso(models.Model):
    # Nombre técnico del modelo en Odoo
    _name = 'permisos_ingreso.permiso'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    # Descripción del modelo que aparecerá en la interfaz de Odoo
    _description = 'Permiso de Ingreso'

    # Campo que almacena el nombre del permiso, generado automáticamente en función de la fecha y el proyecto
    name = fields.Char('Permiso Name', compute='_compute_name', store=True)
    # Campo de fecha para registrar la fecha del permiso de ingreso
    fecha_permiso = fields.Date(string='Fecha del Permiso', tracking = True)
    # Campo que define una relación muchos a uno con el modelo 'Proyecto'
    proyecto_id = fields.Many2one('permisos_ingreso.proyecto', string='Proyecto', tracking = True)
    # Campo de relación uno a muchos para enlazar múltiples registros de personal al permiso
    permiso_personal_ids = fields.One2many('permisos_ingreso.permiso_personal', 'permiso_id', string='Personal')

    personal_ids = fields.Many2many('permisos_ingreso.personal', string='Personal', required=False, compute='_get_personal_ids')

    state = fields.Selection([
        ('draft', 'Borrador'),('to_approve', 'Para Aprobar'),('approved', 'Aprobado'),('cancelled', 'Cancelado'),
    ], string="Estado", default='draft', tracking=True)

    _sql_constraints = [
        ('unique_fecha_proyecto', 'UNIQUE(fecha_permiso, proyecto_id)',
         'No se puede duplicar la fecha y el proyecto en los permisos.')
    ]

    def copy(self, default=None):
        pass

    # def copy(self, default=None):
    #     self.ensure_one()
    #     default = dict(default or {})
    #     # Copiar líneas de permiso_personal sin modificar el original
    #     new_permiso_personal_ids = []
    #     for line in self.permiso_personal_ids:
    #         line_data = line.copy_data()[0]
    #         line_data['usuario_creador'] = self.env.uid
    #         new_permiso_personal_ids.append((0, 0, line_data))
    #
    #     default.update({
    #         'fecha_permiso': False,
    #         # Asegurar que se copie el proyecto original
    #         'proyecto_id': self.proyecto_id.id,
    #         'state': 'draft',
    #         'permiso_personal_ids': new_permiso_personal_ids,
    #     })
    #     return super(Permiso, self).copy(default)

    @api.depends('permiso_personal_ids')
    @api.onchange('permiso_personal_ids')
    def _get_personal_ids(self):
        for brw_each in self:
            personal_ids=brw_each.permiso_personal_ids.mapped('personal_id')
            brw_each.personal_ids=personal_ids

    def action_submit(self):
        """Enviar permiso para aprobación"""
        if not self.env.user.has_group('permisos_ingreso.group_permiso_medio') and not self.env.user.has_group('permisos_ingreso.group_permiso_superior'):
            raise AccessError("No tienes permiso para enviar un permiso para aprobación.")
        self.write({'state': 'to_approve'})

    def action_approve(self):
        """Aprobar permiso"""
        if not self.env.user.has_group('permisos_ingreso.group_permiso_superior'):
            raise AccessError("No tienes permiso para aprobar este permiso.")
        self.write({'state': 'approved'})

    def action_cancel(self):
        """Cancelar permiso"""
        if not self.env.user.has_group('permisos_ingreso.group_permiso_medio') and not self.env.user.has_group('permisos_ingreso.group_permiso_superior'):
            raise AccessError("No tienes permiso para cancelar este permiso.")
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """Reiniciar a borrador"""
        if not self.env.user.has_group('permisos_ingreso.group_permiso_superior'):
            raise AccessError("No tienes permiso para reiniciar este permiso a borrador.")
        self.write({'state': 'draft'})

    # Metodo para calcular el valor del campo 'name' basado en la fecha y el proyecto
    @api.depends('fecha_permiso', 'proyecto_id.name')
    def _compute_name(self):
        for record in self:
            proyecto_name = record.proyecto_id.name if record.proyecto_id else ''
            fecha_permiso = record.fecha_permiso.strftime('%d/%m/%Y') if record.fecha_permiso else 'Sin Fecha'
            record.name = f"{fecha_permiso} - {proyecto_name}"

    @api.model
    def create(self, vals):
        # Validar que la fecha del permiso no sea mayor a 7 días respecto al día actual
        if 'fecha_permiso' in vals and vals.get('fecha_permiso'):
            permit_date = fields.Date.from_string(vals['fecha_permiso'])
            tz = pytz.timezone('America/Guayaquil')
            today = datetime.now(tz).date()
            if permit_date and abs((permit_date - today).days) > 7:
                raise UserError(_("La fecha del permiso debe estar dentro de 7 días desde hoy."))
        self._check_duplicate_personal(vals)
        return super(Permiso, self).create(vals)

    def write(self, vals):
        # Validar que la fecha del permiso no sea mayor a 7 días respecto al día actual
        if 'fecha_permiso' in vals and vals.get('fecha_permiso'):
            new_date = fields.Date.from_string(vals['fecha_permiso'])
            tz = pytz.timezone('America/Guayaquil')
            today = datetime.now(tz).date()
            if new_date and abs((new_date - today).days) > 7:
                raise UserError(_("La fecha del permiso debe estar dentro de 7 días desde hoy."))
        self._check_duplicate_personal(vals)
        return super(Permiso, self).write(vals)

    def _check_duplicate_personal(self, vals):
        """
        Valida que no haya personal duplicado y que ninguno esté en la lista negra.
        """
        # Obtener los IDs del personal desde las líneas modificadas o existentes.
        personal_ids = []

        if 'permiso_personal_ids' in vals:
            # Analiza las líneas para extraer los IDs del personal.
            for line in vals['permiso_personal_ids']:
                if line[0] == 0:  # Línea nueva
                    personal_ids.append(line[2]['personal_id'])
                elif line[0] == 1:  # Línea modificada
                    personal_ids.append(self.env['permisos_ingreso.permiso_personal'].browse(line[1]).personal_id.id)
        else:
            # Obtener todos los IDs de las líneas existentes si no hay cambios en `permiso_personal_ids`.
            personal_ids = self.permiso_personal_ids.mapped('personal_id.id')

        # Verificar si hay duplicados en las líneas de esta transacción.
        if len(personal_ids) != len(set(personal_ids)):
            raise ValidationError(
                'No se puede agregar el mismo personal más de una vez en el listado de permisos.')

        # Verificar duplicados en otros registros.
        fecha_permiso = vals.get('fecha_permiso', self.fecha_permiso)
        proyecto_id = vals.get('proyecto_id', self.proyecto_id.id)

        existing_personal_ids = self.env['permisos_ingreso.permiso_personal'].search([
            ('permiso_id.fecha_permiso', '=', fecha_permiso),
            ('personal_id', 'in', personal_ids),
            ('permiso_id.proyecto_id', '=', proyecto_id),
            ('permiso_id', '!=', self.id)
        ])

        if existing_personal_ids:
            raise ValidationError(
                'No se puede duplicar el permiso para el mismo personal en la misma fecha y proyecto.')

        # Verificar si algún personal está en la lista negra.
        for personal_id in personal_ids:
            personal = self.env['permisos_ingreso.personal'].browse(personal_id)
            lista_negra_entry = self.env['permisos_ingreso.lista_negra'].search([('cedula', '=', personal.cedula)])
            if lista_negra_entry:
                raise ValidationError(
                    'El personal con cédula %s (%s %s) se encuentra en la lista negra.' %
                    (personal.cedula, personal.apellidos, personal.nombres))

    def export_to_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Permisos')

        # Define los encabezados con la columna "Persona recibe" agregada después de "Garita"
        headers = [
            'FECHA', 'NI', 'CATEGORIA', 'GARITA', 'PERSONA RECIBE',
            'ACTIVIDAD', 'PLACA', 'CEDULA', 'APELLIDOS', 'NOMBRES'
        ]

        # Formatos con bordes añadidos
        center_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter',
            'font_name': 'Verdana', 'font_size': 11, 'border': 1
        })
        header_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'bold': True,
            'font_name': 'Verdana', 'font_size': 11, 'border': 1
        })
        wrap_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
            'font_name': 'Verdana', 'font_size': 11, 'border': 1
        })
        # Formato para celdas de fecha (columna FECHA)
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'align': 'center', 'valign': 'vcenter',
            'font_name': 'Verdana', 'font_size': 11, 'border': 1
        })

        # Escribir los encabezados
        worksheet.write_row(0, 0, headers, header_format)

        # Inicializar los anchos de columna según la longitud de cada encabezado
        column_widths = [len(header) for header in headers]

        row = 1
        for record in self:
            for permiso_personal in record.permiso_personal_ids:
                actividad = permiso_personal.actividad if permiso_personal.actividad else ''
                dispositivos = (
                    ' / '.join([
                        f"{(d.modelo or '').strip()} {(d.serie or '').strip()} {(d.color or '').strip()}".strip()
                        for d in permiso_personal.personal_id.dispositivos
                    ])
                ) if permiso_personal.personal_id.dispositivos else ''

                # Consolidar actividad y dispositivos, si aplica
                if actividad:
                    actividad_consolidada = f"{actividad} / {dispositivos}" if dispositivos else actividad
                else:
                    actividad_consolidada = ''

                # Construir la lista de datos; se inserta columna vacía para "Persona recibe"
                # Se coloca la fecha como objeto, para usar write_datetime con el formato correcto.
                data = [
                    record.fecha_permiso,  # Objeto datetime (o None)
                    permiso_personal.numero_ingreso,
                    'MEDIA',
                    record.proyecto_id.nombre if record.proyecto_id else '',
                    '',  # Columna "Persona recibe" vacía
                    actividad_consolidada,
                    permiso_personal.placa_vehiculo if permiso_personal.placa_vehiculo else '',
                    permiso_personal.personal_id.cedula,
                    permiso_personal.personal_id.apellidos,
                    permiso_personal.personal_id.nombres
                ]

                for col_num, cell_data in enumerate(data):
                    if col_num == 0:
                        # Para la columna FECHA: si existe la fecha, escribirla como fecha; de lo contrario, escribir cadena vacía
                        if cell_data:
                            worksheet.write_datetime(row, col_num, cell_data, date_format)
                            # Se considera 10 caracteres para formato 'dd/mm/yyyy'
                            column_widths[col_num] = max(column_widths[col_num], 10)
                        else:
                            worksheet.write(row, col_num, '', center_format)
                    elif col_num == 5:
                        # Columna ACTIVIDAD con wrap_format para texto
                        worksheet.write(row, col_num, cell_data, wrap_format)
                        column_widths[col_num] = max(column_widths[col_num], len(str(cell_data)))
                    else:
                        worksheet.write(row, col_num, cell_data, center_format)
                        column_widths[col_num] = max(column_widths[col_num], len(str(cell_data)))
                row += 1

        # Ajustar el ancho de las columnas con anchos personalizados
        for col_num in range(len(headers)):
            if col_num == 0:  # Fecha
                worksheet.set_column(col_num, col_num, 15)
            elif col_num == 1:  # NI
                worksheet.set_column(col_num, col_num, 4)
            elif col_num == 2:  # Categoria
                worksheet.set_column(col_num, col_num, 12)
            elif col_num == 3:  # Garita
                worksheet.set_column(col_num, col_num, 10)
            elif col_num == 4:  # Persona recibe (nueva columna)
                worksheet.set_column(col_num, col_num, 15)
            elif col_num == 5:  # Actividad
                worksheet.set_column(col_num, col_num, 75)
            elif col_num == 6:  # Placa
                worksheet.set_column(col_num, col_num, 10)
            elif col_num == 7:  # Cedula
                worksheet.set_column(col_num, col_num, 15)
            elif col_num == 8:  # Apellidos
                worksheet.set_column(col_num, col_num, 28)
            elif col_num == 9:  # Nombres
                worksheet.set_column(col_num, col_num, 28)
            else:
                worksheet.set_column(col_num, col_num, column_widths[col_num])

        workbook.close()
        output.seek(0)
        xls_data = output.read()
        output.close()

        # Definición del diccionario para convertir el número del mes en su abreviatura en español
        meses = {
            1: 'ENE',
            2: 'FEB',
            3: 'MAR',
            4: 'ABR',
            5: 'MAY',
            6: 'JUN',
            7: 'JUL',
            8: 'AGO',
            9: 'SEP',
            10: 'OCT',
            11: 'NOV',
            12: 'DIC'
        }

        # Se obtiene la fecha del permiso con el formato deseado: día-mes_abreviado-año (dos dígitos)
        if record.fecha_permiso:
            dia = record.fecha_permiso.day
            mes = record.fecha_permiso.month
            ano = record.fecha_permiso.year % 100  # Dos últimos dígitos del año
            fecha_permiso = f"{dia:02d}-{meses[mes]}-{ano:02d}"
        else:
            fecha_permiso = 'Sin_Fecha'

        # Se obtiene el nombre del proyecto; si no existe, se asigna 'Sin_Proyecto'
        proyecto_name = record.proyecto_id.nombre if record.proyecto_id else 'Sin_Proyecto'

        # Crear el attachment utilizando la fecha y el nombre del proyecto para formar el nombre del archivo.
        attachment = self.env['ir.attachment'].create({
            'name': f'FORMATO PERMISOS {proyecto_name} {fecha_permiso}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(xls_data),
            'store_fname': f'FORMATO PERMISOS {proyecto_name} {fecha_permiso}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_send_email_with_permissions(self):
        """Envía un correo con los permisos separados por proyecto en formato Excel."""
        from datetime import datetime, timedelta
        import io
        import pytz
        import base64

        # Obtener la fecha actual en zona de Ecuador
        ecuador_tz = pytz.timezone("America/Guayaquil")
        today = datetime.now(ecuador_tz).date()

        # Determinar el rango de fechas
        if today.weekday() == 4:  # Si es viernes
            # Consideramos sábado, domingo y lunes
            start_date = today + timedelta(days=1)
            end_date = today + timedelta(days=3)
            days = [today + timedelta(days=i) for i in (1, 2, 3)]
        else:
            # Solo día siguiente
            start_date = today + timedelta(days=1)
            end_date = start_date
            days = [start_date]

        # Diccionario para abreviar meses
        meses = {
            1: 'ENE', 2: 'FEB', 3: 'MAR', 4: 'ABR', 5: 'MAY', 6: 'JUN',
            7: 'JUL', 8: 'AGO', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DIC'
        }

        # Construir fecha_rango para el asunto y nombre de archivos
        months_year = {(d.month, d.year) for d in days}
        if len(months_year) == 1:
            m, y = months_year.pop()
            seq = "-".join(f"{d.day:02d}" for d in days)
            fecha_rango = f"{seq}/{meses[m]}-{y % 100:02d}"
        else:
            primero, *medios, ultimo = days
            parts = [f"{primero.day:02d}/{primero.month:02d}/{primero.year}"]
            parts += [f"{d.day:02d}" for d in medios]
            parts.append(f"{ultimo.day:02d}/{ultimo.month:02d}/{ultimo.year}")
            fecha_rango = "-".join(parts)

        # Buscar los permisos en el rango de fechas
        permisos = self.search([
            ('fecha_permiso', '>=', start_date.strftime(DEFAULT_SERVER_DATE_FORMAT)),
            ('fecha_permiso', '<=', end_date.strftime(DEFAULT_SERVER_DATE_FORMAT)),
            ('state', '=', 'approved')
        ])
        if not permisos:
            raise ValidationError('No hay permisos para enviar en el rango de fechas especificado.')

        # Agrupar permisos
        grupos = {}
        if today.weekday() == 4:
            # Agrupar solo por proyecto
            for permiso in permisos:
                grupos.setdefault(permiso.proyecto_id, []).append(permiso)
        else:
            # Agrupar por (proyecto, fecha_permiso)
            for permiso in permisos:
                key = (permiso.proyecto_id, permiso.fecha_permiso)
                grupos.setdefault(key, []).append(permiso)

        attachments = []
        # Generar un Excel por cada grupo
        for key, permisos_grupo in grupos.items():
            if today.weekday() == 4:
                proyecto = key
                fecha_celda = fecha_rango
            else:
                proyecto, fecha_permiso_group = key
                m, y = fecha_permiso_group.month, fecha_permiso_group.year % 100
                fecha_celda = f"{fecha_permiso_group.day:02d}-{meses[m]}-{y:02d}"

            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Permisos')

            # Encabezados
            headers = [
                'FECHA', 'NI', 'CATEGORIA', 'GARITA', 'PERSONA RECIBE',
                'ACTIVIDAD', 'PLACA', 'CEDULA', 'APELLIDOS', 'NOMBRES'
            ]
            header_fmt = workbook.add_format({
                'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1
            })
            center_fmt = workbook.add_format({
                'align': 'center', 'valign': 'vcenter', 'border': 1
            })
            wrap_fmt = workbook.add_format({
                'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'border': 1
            })
            date_fmt = workbook.add_format({
                'num_format': 'dd/mm/yyyy', 'align': 'center', 'valign': 'vcenter', 'border': 1
            })
            worksheet.write_row(0, 0, headers, header_fmt)

            row = 1
            for permiso in permisos_grupo:
                for pers in permiso.permiso_personal_ids:
                    actividad = pers.actividad or ''
                    dispositivos = ''
                    if pers.personal_id.dispositivos:
                        dispositivos = ' / '.join(
                            f"{d.modelo or ''} {d.serie or ''} {d.color or ''}".strip()
                            for d in pers.personal_id.dispositivos
                        )
                    actividad_consolidada = (f"{actividad} / {dispositivos}"
                                             if actividad and dispositivos
                                             else actividad)

                    # Fecha en celda
                    if today.weekday() == 4:
                        celda_fecha = fecha_rango
                    else:
                        celda_fecha = permiso.fecha_permiso

                    data = [
                        celda_fecha,
                        pers.numero_ingreso,
                        'MEDIA',
                        permiso.proyecto_id.nombre or '',
                        '',
                        actividad_consolidada,
                        pers.placa_vehiculo or '',
                        pers.personal_id.cedula,
                        pers.personal_id.apellidos,
                        pers.personal_id.nombres,
                    ]
                    for col, val in enumerate(data):
                        if col == 0 and today.weekday() != 4:
                            if val:
                                dt = datetime.combine(val, datetime.min.time())
                                worksheet.write_datetime(row, col, dt, date_fmt)
                            else:
                                worksheet.write(row, col, '', center_fmt)
                        elif col == 5:
                            worksheet.write(row, col, val, wrap_fmt)
                        else:
                            worksheet.write(row, col, val, center_fmt)
                    row += 1

            # Ajustar anchos
            widths = [15, 4, 12, 10, 15, 75, 10, 15, 28, 28]
            for idx, w in enumerate(widths):
                worksheet.set_column(idx, idx, w)

            workbook.close()
            output.seek(0)
            xls_data = output.read()
            output.close()

            filename = f"FORMATO PERMISOS {proyecto.nombre} {fecha_celda}.xlsx"
            attachment = self.env['ir.attachment'].sudo().create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(xls_data),
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            })
            attachments.append(attachment)

        # Preparar asunto
        subject_date = fecha_rango if today.weekday() == 4 else fecha_celda
        subject = f"{subject_date} - PERMISOS IPSP TODAS LAS FINCAS"

        # Encontrar servidor de correo
        mail_server = self.env['ir.mail_server'].search(
            [('name', '=', 'Correo de permisos')], limit=1)
        if not mail_server:
            raise ValidationError('El servidor de correo especificado no existe.')

        # Crear y enviar el mail
        mail_values = {
            'subject': subject,
            'body_html': """
                <div style="font-family: Verdana; font-size: 14px; text-transform: uppercase;">
                    <p>Buenas tardes estimada Ing. Angie,</p>
                    <p>Esperando se encuentre muy bien, le adjunto el listado del personal para la correspondiente generación de códigos para las distintas fincas que se detallan a continuación:</p>

                    <p><strong>CHANDUY</strong><br/>
                    - Trabajos internos eléctricos de media tensión, y en estaciones de bombeo<br/>
                    - Levantamientos de estaciones de cuarto de bombeo y cuartos eléctricos de generación</p>

                    <p><strong>CABALA 1</strong><br/>
                    - Trabajos civiles de postería, estudio de suelo para cuarto eléctrico y bombeo<br/>
                    - Trabajos en línea de media tensión</p>

                    <p><strong>CABALÁ 2</strong><br/>
                    RODILLO LISO CATERPILLAR 3TM00713<br/>
                    RETRO KOMATSU S4D1061FH</p>

                    <p><strong>TAURA 2</strong><br/>
                    - Trabajos de obra civil, estacado y construcción de línea de media tensión<br/>
                    - Trabajos de barrenado y cimentación en cuartos de bombeo</p>

                    <p><strong>TAURA 7</strong><br/>
                    - Trabajos de aireación<br/>
                    - Inspección para trabajos de obra civil<br/>
                    - Trabajos en construcción de banco de reguladores</p>

                    <p><strong>Cabala 1:</strong><br/>
                    7.2-12-002668 KOMATSU WB 140-2 CHASIS 30351. RETROEXCAVADORA<br/>
                    7.2-01-001274 RETROEXCAVADORA JOHN DEERE<br/>
                    8.2-14399 RODILLO</p>

                    <p><strong>Cabala 2:</strong><br/>
                    7.2-12-002668 KOMATSU WB 140-2 CHASIS 30351. RETROEXCAVADORA<br/>
                    8.2-5-000607 RODILLO<br/>
                    7.2-9-000610 RETROEXCAVADORA KOMATSU S4D1061FH<br/>
                    T0310GX928444 Retroexcavadora<br/>
                    7.2-9-000786 Retroexcavadora</p>

                    <p><strong>California:</strong><br/>
                    18119002455 – Pluma</p>

                    <p><strong>Taura 2:</strong><br/>
                    18.10-9-001645 GRÚA MÓVIL HITACHI CH125-2<br/>
                    17.1-9-002306 – MARTINETE D30<br/>
                    18.8-22533 – CAMIÓN GRÚA HIAB – REO 100<br/>
                    CAT 416-ID NO: M-10069, SERIAL NO. L9P07493<br/>
                    7.1-16261 EXCAVADORA DRILL ORUGA<br/>
                    18.11-9-002022 GRÚA ZAMBORELLY<br/>
                    7.1-16261 EXCAVADORA CAT 320<br/>
                    13.0-9-000934 TRACK-DRILL SULLARY<br/>
                    REX INGERSOLL-RAND 8.2-5477<br/>
                    JOHN DEERE 410G-7.2-1-001274<br/>
                    18.11-9-001000</p>
                </div>
            """,
            'email_from': 'operaciones@gpsgroup.com.ec',
            'email_to': 'angie.freire@ipsp-produccion.com',
            'email_cc': 'angie.freire@ipsp-profremar.com, bpazmino@gpsgroup.com.ec, evelyn.muguerza@ipsp-produccion.com, jefferson.cueva@ipsp-produccion.com, jose.plaza@ipsp-produccion.com, jramirez@gpsgroup.com.ec, cbazurto@gpsgroup.com.ec',
            'attachment_ids': [(4, a.id) for a in attachments],
            'mail_server_id': mail_server.id,
        }
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()

        return True

class PermisosIngresoConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    permiso_time_limit = fields.Float(
        string="Hora límite de creación de permisos",
        config_parameter="permisos_ingreso.time_limit",
        widget="float_time",
        help="Hora límite (HH:MM) para crear registros de PermisoPersonal",
    )
