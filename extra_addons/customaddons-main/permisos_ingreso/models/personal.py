# Importa las clases y módulos necesarios de Odoo para definir modelos y manejar excepciones
import xlrd
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
import base64
import io
import xlsxwriter

# Define el modelo 'Personal', que representa una persona en el sistema
class Personal(models.Model):
    # Nombre técnico del modelo en Odoo
    _name = 'permisos_ingreso.personal'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    # Descripción del modelo que aparecerá en la interfaz de Odoo
    _description = 'Personal'
    _order = 'apellidos asc'

    # Campo calculado para almacenar el nombre completo de la persona, combinando apellidos y nombres
    name = fields.Char('Personal Name', compute='_compute_name', store=True)
    # Campo de texto para almacenar la cédula de identidad, que es obligatoria
    cedula = fields.Char(string='Cédula', tracking=True)
    # Campo de texto para almacenar los apellidos de la persona, obligatorio
    apellidos = fields.Char(string='Apellidos', tracking=True)
    # Campo de texto para almacenar los nombres de la persona, obligatorio
    nombres = fields.Char(string='Nombres', tracking=True)
    actividad_personal = fields.Char(string='Actividad', tracking=True)
    placa_personal = fields.Char(string='Placa', tracking=True)
    # Campo de relación uno a muchos (One2many) que enlaza los dispositivos asignados a la persona
    dispositivos = fields.One2many('permisos_ingreso.dispositivo', 'personal_id', string='Dispositivos')
    company_id = fields.Many2one("res.partner", string="Compañía", copy=False, domain="[('is_company', '=', True)]", tracking=True)
    # Nuevo campo de selección para el estado
    estado = fields.Selection([
        ('no_aprobado', 'No Aprobado'),
        ('aprobado_sf', 'Aprobado por Seguridad Física')
    ], string='Estado', default='no_aprobado', tracking=True,)

    # Metodo para calcular el campo 'name' concatenando los apellidos y nombres
    @api.depends('cedula', 'apellidos', 'nombres')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.cedula} - {record.apellidos} {record.nombres}"

    # Restricciones SQL para garantizar que la cédula y la combinación de apellidos y nombres sean únicos
    _sql_constraints = [
        ('unique_cedula', 'unique(cedula)', 'La cédula debe ser única.'),
        ('unique_apellidos_nombres', 'unique(apellidos, nombres)', 'Los apellidos y nombres deben ser únicos.')
    ]

    # Metodo de validación adicional para garantizar la unicidad de la cédula y la combinación de apellidos y nombres
    @api.constrains('cedula', 'apellidos', 'nombres')
    def _check_unique_fields(self):
        for record in self:
            if self.search_count([('cedula', '=', record.cedula), ('id', '!=', record.id)]) > 0:
                raise ValidationError('La cédula %s ya existe, debe ser única.' % record.cedula)
            if self.search_count([
                ('apellidos', '=', record.apellidos),
                ('nombres', '=', record.nombres),
                ('id', '!=', record.id)
            ]) > 0:
                raise ValidationError('La combinación de apellidos %s y nombres %s ya existe, debe ser única.' % (
                record.apellidos, record.nombres))

    def export_personal_dispositivos_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Personal_Dispositivos')

        # Definir el formato para los encabezados
        header_format = workbook.add_format({'bold': True, 'border': 1})

        # Se incluyen los encabezados, ahora con la columna de "Compañía" y "Estado"
        headers = ['Cédula', 'Apellidos', 'Nombres', 'Actividad', 'Compañía', 'Estado']
        max_dispositivos = 0

        # Determinar el máximo número de dispositivos para ajustar los encabezados
        personal_records = self.search([])
        for record in personal_records:
            num_dispositivos = len(record.dispositivos)
            if num_dispositivos > max_dispositivos:
                max_dispositivos = num_dispositivos

        # Agregar encabezados para cada columna de dispositivo
        for i in range(max_dispositivos):
            headers.extend([f'Tipo {i + 1}', f'Modelo {i + 1}', f'Serie {i + 1}', f'Color {i + 1}'])

        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
            sheet.set_column(col, col, 20)  # Ajustar el ancho de la columna

        row = 1
        for record in personal_records:
            sheet.write(row, 0, record.cedula)
            sheet.write(row, 1, record.apellidos)
            sheet.write(row, 2, record.nombres)
            sheet.write(row, 3, record.actividad_personal or '')
            # Se usa company_id en lugar de compania_id
            sheet.write(row, 4, record.company_id.name if record.company_id else '')
            sheet.write(row, 5, record.estado)  # Agregar columna de Estado
            col = 6  # Comienza después de Estado
            for dispositivo in record.dispositivos:
                sheet.write(row, col, dispositivo.tipo)
                sheet.write(row, col + 1, dispositivo.modelo)
                sheet.write(row, col + 2, dispositivo.serie)
                sheet.write(row, col + 3, dispositivo.color)
                col += 4
            row += 1

        workbook.close()
        output.seek(0)
        xls_data = output.getvalue()

        attachment = self.env['ir.attachment'].create({
            'name': 'Personal_Dispositivos.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(xls_data),
            'store_fname': 'Personal_Dispositivos.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    import_file = fields.Binary(string="Archivo Excel")
    import_filename = fields.Char(string="Nombre del Archivo")

    def import_personal_dispositivos_excel(self):
        self.ensure_one()

        if not self.import_file or not self.import_filename.endswith('.xlsx'):
            raise UserError(_("Por favor, cargue un archivo Excel válido."))

        try:
            # Decodificar y leer el archivo Excel
            file_data = base64.b64decode(self.import_file)
            file_content = io.BytesIO(file_data)
            workbook = xlrd.open_workbook(file_contents=file_content.read())
            sheet = workbook.sheet_by_index(0)

            headers = [cell.value for cell in sheet.row(0)]
            data_rows = [sheet.row_values(i) for i in range(1, sheet.nrows)]

            for row in data_rows:
                if len(row) < len(headers):
                    raise UserError(_("El archivo Excel tiene filas con menos columnas que los encabezados."))

                # Mapeo de columnas según los encabezados:
                cedula = row[0]
                apellidos = row[1]
                nombres = row[2]
                # Ahora leemos también actividad_personal
                actividad = row[3]
                compania = row[4]
                estado = row[5]

                # Preparamos lista de dispositivos a partir de la columna 6
                dispositivos = []
                for col_idx in range(6, len(row), 4):
                    if row[col_idx]:
                        dispositivo_vals = {
                            'tipo': row[col_idx],
                            'modelo': row[col_idx + 1],
                            'serie': row[col_idx + 2],
                            'color': row[col_idx + 3],
                        }
                        dispositivos.append((0, 0, dispositivo_vals))

                # Buscar partner por nombre de compañía
                partner = self.env['res.partner'].search([
                    ('name', '=', compania),
                    ('is_company', '=', True)
                ], limit=1)

                # Buscar si ya existe registro con esa cédula
                existing_person = self.search([('cedula', '=', cedula)], limit=1)

                # Valores a escribir o crear
                vals = {
                    'apellidos': apellidos,
                    'nombres': nombres,
                    'actividad_personal': actividad,
                    'company_id': partner.id if partner else False,
                    'estado': estado,
                    'dispositivos': [(5, 0, 0)] + dispositivos,
                }

                if existing_person:
                    # Actualiza el registro existente
                    existing_person.write(vals)
                else:
                    # Crea uno nuevo incluyendo la cédula
                    vals['cedula'] = cedula
                    self.create(vals)

            # Limpiar el binario tras procesar
            self.write({'import_file': False, 'import_filename': False})
            return True

        except Exception as e:
            raise UserError(_("Error al procesar el archivo Excel: %s") % str(e))

    def action_export_excel(self):
        return self.export_personal_dispositivos_excel()

    # Funciones para cambiar el estado de los registros
    def action_aprobar_sf(self):
        """Cambia el estado del registro a 'Aprobado por SF'."""
        for record in self:
            record.estado = 'aprobado_sf'
        return True

    def action_no_aprobado(self):
        """Restablece el estado del registro a 'No Aprobado'."""
        for record in self:
            record.estado = 'no_aprobado'
        return True

class Dispositivo(models.Model):
    # El nombre técnico del modelo es 'permisos_ingreso.dispositivo'
    _name = 'permisos_ingreso.dispositivo'

    # Descripción del modelo que será mostrada en la interfaz de Odoo
    _description = 'Dispositivo'

    # Define un campo de selección para el tipo de dispositivo. Los valores posibles son 'computadora', 'telefono' y 'herramienta'
    tipo = fields.Selection(
        [('computadora', 'Computadora'), ('telefono', 'Teléfono'), ('herramienta', 'Herramienta')],
        string='Tipo',  # Nombre del campo que aparecerá en la interfaz
        required=True  # Este campo es obligatorio
    )

    # Define un campo de texto (cadena de caracteres) para el modelo del dispositivo
    modelo = fields.Char(
        string='Modelo',  # Nombre del campo que aparecerá en la interfaz
        required=True  # Este campo es obligatorio
    )

    # Define un campo de texto (cadena de caracteres) para el número de serie del dispositivo
    serie = fields.Char(
        string='Serie'  # Nombre del campo que aparecerá en la interfaz
    )

    # Define un campo de texto (cadena de caracteres) para el color del dispositivo
    color = fields.Char(
        string='Color'  # Nombre del campo que aparecerá en la interfaz
    )

    # Define una relación muchos a uno (Many2one) con el modelo 'personal'. Esto vincula el dispositivo a un personal.
    personal_id = fields.Many2one(
        'permisos_ingreso.personal',  # El modelo con el que se hace la relación
        string='Personal',  # Nombre del campo que aparecerá en la interfaz
        ondelete='cascade'  # Si el personal relacionado es eliminado, el dispositivo también será eliminado
    )