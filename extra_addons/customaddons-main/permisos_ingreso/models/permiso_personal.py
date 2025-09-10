# Importa las clases necesarias de Odoo para definir modelos y campos
from email.policy import default

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import pytz

# Define el modelo 'PermisoPersonal', que representa los detalles de un permiso específico asignado a una persona
class PermisoPersonal(models.Model):
    _name = 'permisos_ingreso.permiso_personal'
    _description = 'Permiso Personal'

    # Campo de relación muchos a uno (Many2one) para enlazar este registro con un permiso específico
    permiso_id = fields.Many2one('permisos_ingreso.permiso', string='Permiso',required=True, ondelete='cascade')

    # Campo de relación muchos a uno (Many2one) para enlazar este registro con una persona específica
    personal_id = fields.Many2one('permisos_ingreso.personal', string='Personal', required=True)

    # Campo de texto para describir la actividad que realizará la persona
    actividad = fields.Char(string='Actividad', required=True)

    # Campo de texto para almacenar el número de ingreso asignado a la persona
    numero_ingreso = fields.Char(string='N° Ingreso', required=True, help='Ingrese solo números para el número de ingreso.', default='4',)

    # Campo de texto para almacenar el número de placa del vehículo de la persona (si aplica)
    placa_vehiculo = fields.Char(string='Placa',)

    # Campo para registrar el usuario que creó el registro
    usuario_creador = fields.Many2one('res.users', string='Usuario Creador', default=lambda self: self.env.uid, readonly=True)

    @api.onchange('personal_id')
    def _onchange_personal_id(self):
        """Cargar actividad_personal y placa_personal en los campos actividad y placa_vehiculo.
        Si no existen las columnas en la tabla de Personal, se crean vía ALTER TABLE."""
        if not self.personal_id:
            self.actividad = ''
            self.placa_vehiculo = ''
            return

        cr = self.env.cr
        table = self.personal_id._table  # normalmente 'permisos_ingreso_personal'

        # Comprobar qué columnas existen
        cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
              AND column_name IN ('actividad_personal','placa_personal')
        """, (table,))
        existing = {row[0] for row in cr.fetchall()}

        # Crear las columnas faltantes
        if 'actividad_personal' not in existing:
            cr.execute(f'ALTER TABLE "{table}" ADD COLUMN actividad_personal VARCHAR;')
        if 'placa_personal' not in existing:
            cr.execute(f'ALTER TABLE "{table}" ADD COLUMN placa_personal VARCHAR;')

        # Invalidar cache para que Odoo reconozca las nuevas columnas
        self.personal_id.invalidate_cache(fnames=['actividad_personal', 'placa_personal'])

        # Asignar los valores al formulario
        self.actividad = getattr(self.personal_id, 'actividad_personal', '') or ''
        self.placa_vehiculo = getattr(self.personal_id, 'placa_personal', '') or ''

    @api.model
    def create(self, vals):
        # Solo aplica si el usuario está en el grupo medio o en el de registro de permisos
        if (self.env.user.has_group('permisos_ingreso.group_permiso_medio')
                or self.env.user.has_group('permisos_ingreso.group_registro_permiso')):
            # Obtener límite desde Ajustes (por defecto 13.50 = 13:30)
            limit_str = self.env['ir.config_parameter'].sudo().get_param(
                'permisos_ingreso.time_limit', '13.50'
            )
            limit = float(limit_str)
            # Hora actual en zona America/Guayaquil
            now = datetime.now(pytz.timezone('America/Guayaquil'))
            hora_actual = now.hour + now.minute / 60.0
            if hora_actual > limit:
                raise ValidationError(
                    _("No se pueden crear registros después de %02d:%02d.") %
                    (int(limit), int((limit - int(limit)) * 60))
                )
        return super(PermisoPersonal, self).create(vals)

    def unlink(self):
        for record in self:
            # Si el usuario logueado no es el creador y además no pertenece al grupo "group_permiso_superior", se impide la eliminación
            if record.usuario_creador and record.usuario_creador.id != self.env.uid and not self.env.user.has_group(
                    'permisos_ingreso.group_permiso_superior'):
                raise UserError(
                    _("El usuario logueado no es el creador del registro y no pertenece al grupo superior, por lo que no puede eliminarlo."))
        return super(PermisoPersonal, self).unlink()

    def write(self, vals):
        for record in self:
            # Si no es el creador, y no está en grupo superior ni en grupo medio, no puede modificar
            if record.usuario_creador \
                    and record.usuario_creador.id != self.env.uid \
                    and not self.env.user.has_group('permisos_ingreso.group_permiso_superior') \
                    and not self.env.user.has_group('permisos_ingreso.group_permiso_medio'):
                raise UserError(
                    _("El usuario logueado no es el creador del registro ni pertenece a los grupos permitidos, por lo que no puede modificarlo.")
                )
        return super(PermisoPersonal, self).write(vals)

    @api.constrains('numero_ingreso')
    def _check_numero_ingreso(self):
        for record in self:
            if not record.numero_ingreso.isdigit():  # Verificar que el campo contiene solo dígitos
                raise ValidationError('El Número de ingreso debe contener solo números positivos.')
            if int(record.numero_ingreso) <= 0:  # Validar que el número sea positivo
                raise ValidationError('El Número de ingreso no puede ser cero o negativo.')

    @api.constrains('permiso_id', 'personal_id')
    def _check_duplicate_personal_in_permiso(self):
        for record in self:
            duplicates = self.search([
                ('permiso_id', '=', record.permiso_id.id),
                ('personal_id', '=', record.personal_id.id),
                ('id', '!=', record.id)
            ])
            if duplicates:
                raise ValidationError('No se puede agregar el mismo personal más de una vez en el mismo permiso.')

    _sql_constraints = [
        ('unique_personal_in_permiso', 'UNIQUE(permiso_id, personal_id)', 'No se puede agregar el mismo personal más de una vez en el mismo permiso.')
    ]

    @api.onchange('personal_id', 'permiso_id.permiso_personal_ids')
    def onchange_personal_id(self):
        print(self._context)
        print(self.permiso_id.permiso_personal_ids)
        permiso_personal = self.permiso_id.permiso_personal_ids._origin
        permiso = permiso_personal.mapped('personal_id')
        print(permiso)
