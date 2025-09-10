from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class MaintenanceEquipmentCaracteristicas(models.Model):
    _name = 'maintenance.equipment.caracteristicas'

    name = fields.Char('Descripcion')
    detalle = fields.Char('Detalle')
    mantenimiento_id = fields.Many2one('maintenance.equipment', 'Mantenimiento', ondelete='cascade')

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    product_id = fields.Many2one('product.product', string='Producto/Equipo')
    caracteristicas_ids = fields.One2many('maintenance.equipment.caracteristicas', 'mantenimiento_id', 'Caracteristicas Lines')

    _sql_constraints = [
        ('serial_no', 'unique(serial_no)', "¡Ya existe otro activo con este número de serie!"),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'serial_no' in vals and vals['serial_no']:
                # Verificar si existe un equipo con el mismo número de serie
                equipo_existente = self.env['maintenance.equipment'].search([
                    ('serial_no', '=', vals['serial_no'])
                ], limit=1)
                if equipo_existente:
                    raise ValidationError(
                        _("El número de serie '%s' ya está en uso para otro equipo.") % vals['serial_no'])
        return super(MaintenanceEquipment, self).create(vals_list)

    def write(self, vals):
        if 'serial_no' in vals and vals['serial_no']:
            for record in self:
                # Verificar si existe un equipo con el mismo número de serie, excluyendo el registro actual
                equipo_existente = self.env['maintenance.equipment'].search([
                    ('serial_no', '=', vals['serial_no']),
                    ('id', '!=', record.id)
                ], limit=1)
                if equipo_existente:
                    raise ValidationError(
                        _("El número de serie '%s' ya está en uso para otro equipo.") % vals['serial_no'])
        return super(MaintenanceEquipment, self).write(vals)

    def name_get(self):
        """
        Personaliza cómo se muestra el nombre del equipo, incluyendo el número de serie si está disponible.
        """
        result = []
        for equipo in self:
            name = equipo.name
            if equipo.serial_no:
                name = f"[{equipo.serial_no}] {name}"
            result.append((equipo.id, name))
        return result

class MaintenanceActa(models.Model):
    _name = 'maintenance.acta'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Acta de Entrega o Recepción'

    name = fields.Char('Name', required=True, readonly=True, copy=False, index=True)
    tipo = fields.Selection([
        ('entrega', 'Acta de Entrega'),
        ('recepcion', 'Acta de Recepción'),
    ], required=True, string="Tipo de Acta", default='entrega', tracking=True)
    fecha = fields.Date(string="Fecha", default=fields.Date.context_today, tracking=True)
    empleado_recibe = fields.Many2one('hr.employee', string="Empleado que Recibe", tracking=True)
    persona_entrega = fields.Many2one('hr.employee', string="Empleado que Entrega", tracking=True)
    equipo_recibe = fields.Many2one('maintenance.equipment', string="Equipo a Recibir", tracking=True)
    ubicacion = fields.Char(string="Ubicación", help="Ubicación del equipo o del acto de entrega/recepción", tracking=True)
    observacion = fields.Text(string="Observación", tracking=True)
    codigo = fields.Char(string="Código de Acta", readonly=True, copy=False, index=True)

    # Nuevo campo para estados
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('open', 'Abierto'),
        ('closed', 'Cerrado'),
        ('damaged', 'Dañado'),
    ], string="Estado", default='draft', tracking=True)

    def presenta_nombre_equipo(self):
        """
        Devuelve el nombre del equipo relacionado con el acta.
        Si no está especificado, devuelve 'No especificado'.
        """
        if self.equipo_recibe and self.equipo_recibe.name:
            return self.equipo_recibe.name
        return 'No especificado'

    # Nuevos métodos para obtener el modelo y el número de serie
    def presenta_modelo_equipo(self):
        """
        Devuelve el modelo del equipo relacionado con el acta.
        Si no está especificado, devuelve 'No especificado'.
        """
        if self.equipo_recibe and self.equipo_recibe.model:
            return self.equipo_recibe.model
        return 'No especificado'

    def presenta_serial_no_equipo(self):
        """
        Devuelve el número de serie del equipo relacionado con el acta.
        Si no está especificado, devuelve 'No especificado'.
        """
        if self.equipo_recibe and self.equipo_recibe.serial_no:
            return self.equipo_recibe.serial_no
        return 'No especificado'

    # Métodos para cambiar de estado
    def action_set_draft(self):
        """Cambiar estado a Borrador"""
        self.state = 'draft'

    def action_open(self):
        """Cambiar estado a Abierto"""
        self.state = 'open'

    def action_close(self):
        """Cambiar estado a Cerrado"""
        self.state = 'closed'

    def action_damage(self):
        """Cambiar estado a Dañado"""
        self.state = 'damaged'

    @api.model
    def create(self, vals):
        # --- tu lógica actual de generación de código y name ---
        tipo = vals.get('tipo', 'entrega')
        if 'codigo' not in vals:
            if tipo == 'entrega':
                sec = self.env['ir.sequence'].next_by_code('maintenance.acta.entrega') or '0001'
            else:
                sec = self.env['ir.sequence'].next_by_code('maintenance.acta.recepcion') or '0001'
            vals['codigo'] = sec
        vals['name'] = vals['codigo']
        # ------------------------------------------------------
        record = super(MaintenanceActa, self).create(vals)
        # ——— aquí actualizamos el equipo relacionado ———
        if record.equipo_recibe:
            if record.tipo == 'entrega':
                # al entregar, asignamos el empleado que recibe
                record.equipo_recibe.write({'employee_id': record.empleado_recibe.id})
            else:
                # al recepcionar, limpiamos la asignación
                record.equipo_recibe.write({'employee_id': False})
        return record

    def write(self, vals):
        res = super(MaintenanceActa, self).write(vals)
        for record in self:
            # ——— si cambiaron tipo o empleado_recibe ———
            if any(f in vals for f in ('tipo', 'empleado_recibe')) and record.equipo_recibe:
                if record.tipo == 'entrega':
                    record.equipo_recibe.write({'employee_id': record.empleado_recibe.id})
                elif record.tipo == 'recepcion':
                    record.equipo_recibe.write({'employee_id': False})
            # ——— si el acta pasó a estado 'closed' ———
            if vals.get('state') == 'closed' and record.equipo_recibe:
                record.equipo_recibe.write({'employee_id': False})
        return res

    caracteristicas_ids = fields.One2many(comodel_name='maintenance.equipment.caracteristicas', inverse_name='mantenimiento_id',
        string="Características del equipo", compute="_compute_caracteristicas_ids", store=False,)

    @api.depends('equipo_recibe')
    def _compute_caracteristicas_ids(self):
        for record in self:
            if record.equipo_recibe:
                record.caracteristicas_ids = record.equipo_recibe.caracteristicas_ids
            else:
                record.caracteristicas_ids = False

    def presenta_ubicacion(self):
        """
        Devuelve la ubicación del acta. Si no está especificada, devuelve 'No especificado'.
        """
        return self.ubicacion or 'No especificado'

    def presenta_observacion(self):
        """
        Devuelve la observación del acta.
        Si no está especificada, devuelve 'No especificada'.
        """
        return self.observacion or 'No especificada'

    # Métodos para obtener la información de los empleados
    def presenta_nombre_empleado_recibe(self):
        if self.empleado_recibe:
            return self.empleado_recibe.name
        return 'No especificado'

    def presenta_identificacion_empleado_recibe(self):
        if self.empleado_recibe:
            return self.empleado_recibe.identification_id
        return 'No especificado'

    def presenta_departamento_empleado_recibe(self):
        if self.empleado_recibe and self.empleado_recibe.department_id:
            return self.empleado_recibe.department_id.name
        return 'No especificado'

    def presenta_compania_empleado_recibe(self):
        """
        Devuelve el nombre de la compañía del empleado que recibe el equipo.
        """
        if self.empleado_recibe and self.empleado_recibe.company_id:
            return self.empleado_recibe.company_id.name
        return 'No especificado'

    def presenta_identificacion_compania_empleado_recibe(self):
        """
        Devuelve la identificación de la compañía del empleado que recibe el equipo.
        """
        if self.empleado_recibe and self.empleado_recibe.company_id:
            return self.empleado_recibe.company_id.partner_id.vat
        return 'No especificado'

    def presenta_nombre_persona_entrega(self):
        if self.persona_entrega:
            return self.persona_entrega.name
        return 'No especificado'

    def presenta_identificacion_persona_entrega(self):
        if self.persona_entrega:
            return self.persona_entrega.identification_id
        return 'No especificado'

    def presenta_departamento_persona_entrega(self):
        if self.persona_entrega and self.persona_entrega.department_id:
            return self.persona_entrega.department_id.name
        return 'No especificado'

    def presenta_compania_persona_entrega(self):
        """
        Devuelve el nombre de la compañía de la persona que entrega el equipo.
        """
        if self.persona_entrega and self.persona_entrega.company_id:
            return self.persona_entrega.company_id.name
        return 'No especificado'

    def presenta_identificacion_compania_persona_entrega(self):
        """
        Devuelve la identificación de la compañía de la persona que entrega el equipo.
        """
        if self.persona_entrega and self.persona_entrega.company_id:
            return self.persona_entrega.company_id.partner_id.vat
        return 'No especificado'

    def formato_fecha(self):
        """
        Devuelve la fecha en el formato día / MES (nombre del mes en mayúsculas) / año.
        Ejemplo: 03 / DICIEMBRE / 2024
        """
        if self.fecha:
            fecha_obj = fields.Date.from_string(self.fecha)
            return fecha_obj.strftime('%d / %B / %Y').upper()
        return 'Fecha no especificada'

    # Nueva función para obtener el código
    def presenta_codigo(self):
        """
        Devuelve el código del acta.
        """
        if self.codigo:
            return self.codigo
        return 'No especificado'

    @api.onchange('tipo')
    def _onchange_tipo(self):
        if self.tipo == 'entrega':
            self.observacion = False
        elif self.tipo == 'recepcion':
            self.equipo_recibe = False
