from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError



BANK_TYPE = [('checking', 'Corriente'), ('savings', 'Ahorros')]
class EmployeeHistory(models.Model):
    _name = 'employee.history'
    _order = 'date desc'
    
    name = fields.Char('Subject', size=128, required=True)
    message = fields.Text('Description')
    date = fields.Datetime('Date', required=True)
    user_id = fields.Many2one('res.users', 'User Responsible', readonly=True, default=lambda self: self.env.user)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=False)
                
class ThEmployeeHistoryHealth(models.Model):
    _inherit = 'employee.history'
    _name = 'th.employee.history.health'

    doctor = fields.Char('Doctor', size=256)

class ThEmployeeHistoryNote(models.Model):
    _inherit = 'employee.history'
    _name = 'th.employee.history.note'
    
    state = fields.Selection([('open','Open'),('close','Close'),('resolve','Resolve'),('pending','Pending'),('cancel','Cancel')], 'Status', default='resolve')
    campo = fields.Many2one('ir.model.fields', domain=[('model', '=', 'hr.employee')])

class ThEmployeeHistoryDecimo(models.Model):
    _inherit = 'employee.history'
    _name = 'th.employee.history.decimo'
    
    tipo = fields.Selection([
        ('decter', 'Decimo Tercero'),
        ('deccua', 'Decimo Cuarto'),
        ('vac', 'Vacaciones'),
        ], 'Tipo', track_visibility='onchange', copy=False, default='decter')
    fecha_desde = fields.Date('Fecha Desde')
    fecha_hasta = fields.Date('Fecha Hasta')
    dias = fields.Integer('Dias')
    valor = fields.Float('Valor')

class ThEmployeeContact(models.Model):
    _name = 'th.employee.contact'
    
    employee_id = fields.Many2one('hr.employee', 'Empleado', ondelete='cascade')
    name_contact = fields.Char('Nombre', size=64)
    parentesco = fields.Char('Parentesco', size=240)
    direccion = fields.Char('Direccion', size=64)
    personal_email = fields.Char('E-mail Personal', size=240)
    home_phone = fields.Char('Telefono Domicilio', size=10)
    home_mobile = fields.Char('Telefono Celular', size=10)
    emergency_home_phone = fields.Char('Telefono de Emergencia', size=10)
    emergency_home_mobile = fields.Char('Celular de Emergencia', size=10)

class ThEmployeeLote(models.Model):
    _name = 'th.employee.lote'
    
    employee_id = fields.Many2one('hr.employee', 'Empleado', ondelete='cascade')
    name = fields.Char('Lote', size=240)
    hectarea_hacienda = fields.Float('Hectareaje Hacienda', digits=(4, 4))
    hectarea_plantilla = fields.Float('Hectareaje Plantilla', digits=(4, 4))
    unidad_administrativa = fields.Many2one("establecimientos")
    labor_id = fields.Many2one('hr.job', string='Cargo/Labor')
    hectareas = fields.Float('Hectareaje', digits=(4, 4))
    tipo_hra = fields.Selection([
                    ('hacienda', 'Hacienda'),
                    ('plantilla', 'Plantilla')
                    ], 'Tipo Hra', default='hacienda')

class ThEmployeeBeneficiario(models.Model):
    _name = 'th.employee.beneficiario'
    
    employee_id = fields.Many2one('hr.employee', 'Empleado', ondelete='cascade')
    name = fields.Char('Nombre', size=64)
    parentesco = fields.Char('Parentesco', size=240)
    identificacion = fields.Char('Cedula', size=14)
    tipo_cuenta = fields.Many2one('res.partner.bank.account.type', 'Tipo Cuenta')
    banco = fields.Many2one('res.bank', 'Banco')
    cuenta = fields.Char('Numero Cta', size=20)
    estado = fields.Selection([
                    ('activa', 'Activa'),
                    ('inactiva', 'Inactiva')
                    ], 'Estado', default='activa')

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _order = "last_name asc, mother_last_name asc, first_name asc, second_name asc"
    
    partner_id = fields.Many2one('res.partner', 'Partner', help="Empresa Relacionada")
    identification_id = fields.Char(string='R.U.C / CI', size=32, store=True,tracking=True)
    family_burden_ids = fields.One2many('th.family.burden', 'employee_id', 'Cargas Familiares')
    family_substitute_ids = fields.One2many('th.family.substitute', 'employee_id', 'Family Substitute')
    employee_history_id = fields.One2many('th.employee.history.note', 'employee_id', 'Employee History Notes')
    health_history_id = fields.One2many('th.employee.history.health', 'employee_id', 'Employee History Health')
    decimo_history_id = fields.One2many('th.employee.history.decimo', 'employee_id', 'Employee History Decimo')
    education_ids = fields.One2many('th.education.level', 'employee_id', 'Childrens')
    unemployee = fields.Boolean('Ex-Employee')
    inability = fields.Boolean('Discapacidad', help="Tiene discpacidad emitida por CONADIS?")
    substitute = fields.Boolean('Fml. con Discapacidad', help="Marque esta casilla si el empleado tiene familiares con discapacidad y que adquiere derechos por ellos")
    disability = fields.Many2one('th.disability.type', 'Tipo de Discapacidad')
    percent_disability = fields.Float('% Discapacidad', size=128)
    first_name = fields.Char('Primer Nombre', size=255,tracking=True)
    second_name = fields.Char('Segundo Nombre', size=255,tracking=True)
    last_name = fields.Char('Apellido Paterno', size=255,tracking=True)
    mother_last_name = fields.Char('Apellido Materno', size=255,tracking=True)
    home_phone = fields.Char('Telefono Domicilio', size=10,tracking=True)
    home_mobile = fields.Char('Telefono Celular', size=10,tracking=True)
    personal_email = fields.Char('E-mail Personal', size=240,tracking=True)
    emergency_home_phone = fields.Char('Telefono de Emergencia', size=10)
    emergency_home_mobile = fields.Char('Celular de Emergencia', size=10)
    age = fields.Integer(string='Age', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    marital = fields.Selection([('single', 'Single'), ('married', 'Married'), ('widower', 'Widower'), ('divorced', 'Divorced'),('union','Union Libre')], 'Marital Status', required=True,tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    operadora_emp = fields.Selection([
                    ('Claro', 'Claro'),
                    ('CNT', 'CNT'),
                    ('Movistar', 'Movistar'),
                    ('Tuenty', 'Tuenti'),
                    ], 'Operadora', default='Claro')
    operadora_work = fields.Selection([
                    ('Claro', 'Claro'),
                    ('CNT', 'CNT'),
                    ('Movistar', 'Movistar'),
                    ('Tuenty', 'Tuenti'),
                    ], 'Operadora', default='Claro')
    job_id = fields.Many2one('hr.job', string='Cargo/Labor', required=True)
    job_id_act = fields.Many2one('hr.job', string='Cargo/Labor')
    name_contact = fields.Char('Nombre', size=64)
    direccion = fields.Char('Direccion', size=64)
    parentesco = fields.Char('Parentesco', size=240)
    sueldo = fields.Float('Sueldo')
    tipo_contrato = fields.Many2one('hr.contract.type')
    tipo_rol = fields.Many2one('tipo.roles', required=True)
    condicion_rol = fields.Selection([
                    ('administrativo', 'Administrativo'),
                    ('operativo', 'Operativo'),
                    ], 'Condicion Rol', default='operativo')
    fecha_ingreso = fields.Date('Fecha Ingreso', required=True)
    acumula_fondo_reserva = fields.Boolean('No Acumula Beneficios?')
    unidad_administrativa = fields.Many2one('establecimientos', required=True)
    fecha_salida = fields.Date('Fecha Salida')
    tipo_contrato_salida = fields.Many2one('hr.contract.type')
    tipo_rol_salida = fields.Many2one('tipo.roles')
    fecha_renuncia = fields.Date('Fecha Renuncia')
    fecha_firma_renuncia = fields.Date('Fecha Firma', default=fields.Date.today())
    unidad_administrativa_salida = fields.Many2one('establecimientos')
    provincia_inicio = fields.Many2one('res.country.state', 'Provincia', required=True)
    canton_inicio = fields.Char('Canton')
    ciudad_inicio = fields.Char('Ciudad', required=True)
    provincia_fin = fields.Many2one('res.country.state', 'Provincia', required=True)
    canton_fin = fields.Char('Canton')
    ciudad_fin = fields.Char('Ciudad')
    motivo_renuncia = fields.Selection([
                    ('Despido', 'Despido'),
                    ('Terminacion', 'Terminacion de Contrato'),
                    ('Renuncia', 'Renuncia'),
                    ('Fallecimiento', 'Fallecimiento'),
                    ('Finalizacion', 'Finalizacion de Tarea'),
                    ], 'Motivo', default='')
    contact_ids = fields.One2many('th.employee.contact', 'employee_id', 'Contactos', required=True)
    valor_reembolso = fields.Float('Valor Reembolso', digits=(8, 2))
    valor_caja_chica = fields.Float('Valor Caja Chica', digits=(8, 2))
    reemplazo_activo = fields.Boolean('Reemplazo Activo')
    nombre_reemplazo_act_id = fields.Many2one('hr.employee', 'Nombre')
    codigo_sectorial = fields.Char(string='Codigo Sectorial', size=32, store=True)
    lote_asignado_ids = fields.One2many('th.employee.lote', 'employee_id', 'Lotes')
    tiene_beneficiario = fields.Boolean('Tiene Beneficiario')
    beneficiario_id = fields.Many2one('res.partner', domain="[('supplier', '=', True)]")
    # bank_account_beneficiario_id = fields.Many2one('res.partner.bank', string='Cuenta Bancaria Beneficiario', domain="[('partner_id', '=', beneficiario_id)]", groups='hr.group_hr_user')
    bank_id = fields.Many2one('res.bank', 'Banco', required=True)
    bank_type = fields.Selection(BANK_TYPE, 'Tipo de Cuenta', required=True)
    account_number = fields.Char('Numero de Cuenta', size=20, required=True)
    beneficiario_ids = fields.One2many('th.employee.beneficiario', 'employee_id', 'Beneficiario')
    es_reemplazo = fields.Boolean('Es reemplazo')
    checked = fields.Boolean('Checked Employee', default=False)


    def action_contact_create(self):
        for employee in self:
            partner_vals = {
                'name': employee.name,
                'email': employee.work_email or employee.private_email,
                'phone': employee.work_phone or employee.mobile_phone,
                'company_id': employee.company_id.id,
            }
            try:
                partner = self.env['res.partner'].create(partner_vals)
                employee.partner_id = partner.id
                self.env.user.notify_info(message='Contacto creado correctamente')
            except Exception as e:
                self.env.user.notify_warning(message=f'Error al crear el contacto: {str(e)}')
        return True

    def action_user_create(self):
        for employee in self:
            if not employee.user_id:
                user_vals = {
                    'name': employee.name,
                    'login': employee.work_email or employee.private_email or employee.identification_id,
                    'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
                }
                
                user = self.env['res.users'].create(user_vals)
                employee.user_id = user
                self.env.user.notify_info(message='Usuario creado correctamente')
                # except Exception as e:
                #     self.env.user.notify_warning(message=f'Error al crear el usuario: {str(e)}')
        return True

    
    @api.model
    def load(self, fields, data):
        processed_ids = []
        messages = []
        is_test = self.env.context.get('test_import', False)

        # Obtener índices de los campos necesarios
        field_indices = {
            field: fields.index(field) if field in fields else None
            for field in ['identification_id', 'name', 'company_id', 'department_id', 'job_id', 'provincia_inicio', 'ciudad_inicio', 'sueldo']
        }

        for record in data:
            employee = None
            if field_indices['identification_id'] is not None:
                employee = self.env['hr.employee'].search([
                    ('identification_id', '=', record[field_indices['identification_id']]),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
            
            if not employee:
                complete_name = record[field_indices['name']]
                separacion = complete_name.split(' ')
                id_department = self.env['hr.department'].search([('complete_name', '=', record[field_indices['department_id']])], limit=1).id if field_indices['department_id'] is not None else None
                id_job = self.env['hr.job'].search([('name', '=', record[field_indices['job_id']])], limit=1).id if field_indices['job_id'] is not None else None
                company_id = self.env['res.company'].search([('name', '=', record[field_indices['company_id']])], limit=1).id if field_indices['company_id'] is not None else self.env.company.id
                provincia_inicio_id = self.env['res.country.state'].search([('name', '=', record[field_indices['provincia_inicio']])], limit=1).id if field_indices['provincia_inicio'] is not None else None
                ciudad_inicio = record[field_indices['ciudad_inicio']] if field_indices['ciudad_inicio'] is not None else ''
                sueldo = record[field_indices['sueldo']] if field_indices['sueldo'] is not None else 0.0

                if not id_job:
                    messages.append(_('Job position not found for employee %s') % complete_name)
                    continue


                employee_vals = {
                    'identification_id': record[field_indices['identification_id']] if field_indices['identification_id'] is not None else '',
                    'first_name': separacion[0],
                    'second_name': separacion[1] if len(separacion) > 1 else '',
                    'last_name': separacion[2] if len(separacion) > 2 else '',
                    'mother_last_name': separacion[3] if len(separacion) > 3 else '',
                    'name': record[field_indices['name']],
                    'company_id': company_id,
                    'job_id': id_job,
                    'department_id': id_department,
                    'resource_calendar_id': self.env.company.resource_calendar_id.id,
                    'provincia_inicio': provincia_inicio_id,
                    'ciudad_inicio': ciudad_inicio,
                    'sueldo': sueldo,
                    'active': True,
                    'tz': self.env.user.tz,
                }

                if not is_test:
                    employee = self.create(employee_vals)
                    processed_ids.append(employee.id)
                    messages.append(_('Employee %s created') % employee.name)
                else:
                    messages.append(_('Employee %s would be created (test mode)') % complete_name)
            else:
                
                id_job = self.env['hr.job'].search([('name', '=', record[field_indices['job_id']])], limit=1).id if field_indices['job_id'] is not None else None

                if not id_job:
                    messages.append(_('Job position not found for employee %s') % employee.name)
                    continue
                
                
                update_vals = {
                    'identification_id': record[field_indices['identification_id']] if field_indices['identification_id'] is not None else '',
                    'name': record[field_indices['name']],
                    'company_id': company_id,
                    'job_id': id_job,
                    'department_id': id_department,
                    'resource_calendar_id': self.env.company.resource_calendar_id.id,
                    'provincia_inicio': provincia_inicio_id,
                    'ciudad_inicio': ciudad_inicio,
                    'sueldo': sueldo,
                    'active': True,
                    'tz': self.env.user.tz,

                }
                update_vals=self.update_data_contracts_employees(update_vals)
                if not is_test:
                    employee.write(update_vals)
                    processed_ids.append(employee.id)
                    messages.append(_('Employee %s updated') % employee.name)
                else:
                    messages.append(_('Employee %s would be updated (test mode)') % employee.name)

        # Devolver el formato esperado con 'nextrow'
        return {
            'ids': processed_ids,
            'messages': messages,
            'nextrow': False
        }

    @api.model
    def update_data_contracts_employees(self,update_vals):

        return update_vals

    def write(self, vals):
        for record in self:
            
            if self.env.context.get('skip_validation'):
                return super(HrEmployee, self).write(vals)
            
            old_values = record.read([])[0]
            
            # if 'name' in vals:
            #     nombre_completo = vals['name']
            #
            # else:
            #     nombre_completo = f'{vals.get("firstname", "")} {vals.get("lastname", "")} {vals.get("lastname2", "")}'
            #
            #
            # separacion = nombre_completo.split(' ')
            # vals['first_name'] = separacion[0]
            # vals['second_name'] = separacion[1] if len(separacion) > 1 else ''
            # vals['last_name'] = separacion[2] if len(separacion) > 2 else ''
            # vals['mother_last_name'] = separacion[3] if len(separacion) > 3 else ''
                
            
            

            # if self.env.user.has_group('hr.group_hr_manager'):
            #     if self.checked == False and 'checked' not in vals:
            #         raise UserError('Debes Marcar al empleado como verificado para poder guardar los cambios')
            
            return super(HrEmployee, self).write(vals)

    @api.model
    def create(self, vals):
        # Verificar si es una importación
        # if self.env.context.get('import_file'):
        #     if 'name_contact' in vals and 'name' not in vals:
        #         vals['name'] = vals['name_contact']
        #     else:
        #         nombre_completo = vals['name']
        #         # separacion = nombre_completo.split(' ')
        #         # vals['first_name'] = separacion[0]
        #         # vals['second_name'] = separacion[1] if len(separacion) > 1 else ''
        #         # vals['last_name'] = separacion[2] if len(separacion) > 2 else ''
        #         # vals['mother_last_name'] = separacion[3] if len(separacion) > 3 else ''
        #
        #     # Crear recurso si no existe durante importación
        #     if 'resource_id' not in vals or not vals['resource_id']:
        #         resource_vals = {
        #             'name': vals.get('name', 'Unknown Resource'),
        #             'company_id': vals.get('company_id', self.env.company.id),
        #             'resource_type': 'user',
        #             'active': vals.get('active', True),
        #             'calendar_id': vals.get('calendar_id', self.env.company.resource_calendar_id.id),
        #             'time_efficiency': vals.get('time_efficiency', 100),
        #             'user_id': vals.get('user_id', False),
        #             'tz': self.env.user.tz,
        #         }
        #         resource = self.env['resource.resource'].sudo().create(resource_vals)
        #         vals['resource_id'] = resource.id
        # else:
        #     if 'name' in vals:
        #         nombre_completo = vals['name']
        #     else:
        #         nombre_completo = f"{vals.get('first_name', '')} {vals.get('second_name', '')} {vals.get('last_name', '')} {vals.get('mother_last_name', '')}"
        #
        #     separacion = nombre_completo.split(' ')
        #     # vals['first_name'] = separacion[0]
        #     # vals['second_name'] = separacion[1] if len(separacion) > 1 else ''
        #     # vals['last_name'] = separacion[2] if len(separacion) > 2 else ''
        #     # vals['mother_last_name'] = separacion[3] if len(separacion) > 3 else ''

        # Verificar que el sueldo no sea 0.0
        if vals.get('sueldo', 0.0) == 0.0:
            raise UserError('El empleado no puede tener un sueldo de 0.0')

        # Crear el empleado
        employee = super(HrEmployee, self.with_context(skip_validation=True)).create(vals)

        # Crear un contrato asociado si el rol no es 'ROL SERVICIOS PRESTADOS'
        # rol = self.env['tipo.roles'].browse(vals['tipo_rol'])
        # if rol.name != 'ROL SERVICIOS PRESTADOS':
        contract_vals = {
                'name': _('Contrato del empleado %s') % employee.name,
                'employee_id': employee.id,
                'company_id': employee.company_id.id,
                'date_start': fields.Date.today(),
                'state': 'draft',
                'department_id': employee.department_id.id,
                'job_id': employee.job_id.id,
                'wage': employee.sueldo,
                'working_hours': employee.resource_calendar_id.id,
                'provincia_inicio': employee.provincia_inicio.id,
                'ciudad_inicio': employee.ciudad_inicio,
                "contract_type_id":employee.tipo_contrato and employee.tipo_contrato.id or False
                # Agregar otros valores necesarios para el contrato
            }
        self.env['hr.contract'].create(contract_vals)

        return employee

    _sql_constraints = [
        ('registro_coach_uniq', 'unique(coach_id)', 'El reemplazo debe ser unico!'),
        ('registro_reempact_uniq', 'unique(nombre_reemplazo_act_id)', 'El reemplazo debe ser unico!'),
    ]

