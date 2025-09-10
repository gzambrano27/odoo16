from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from ...calendar_days.tools import CalendarManager,DateManager,MonthManager
dtObj = DateManager()
BANK_TYPE = [('checking', 'Corriente'), ('savings', 'Ahorros')]
import re

class HrEmployeeUpdateRequest(models.Model):
    _name = 'hr.employee.update.request'
    _description = 'Solicitud de Actualización de Datos del Empleado'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, tracking=True)

    # Campos editables (copiados del empleado, no related)
    private_street = fields.Char(string="Calle privado", tracking=True, default=".")
    private_street2 = fields.Char(string="Calle 2 privado", tracking=True, default=".")
    private_email = fields.Char(string="Correo electrónico privado", tracking=True)
    phone = fields.Char(string="Teléfono privado", tracking=True, default=".")

    send_date = fields.Date(string="Fecha de Envío", tracking=True, readonly=True)
    deadline_date = fields.Date(string="Fecha Máxima de Actualización", tracking=True, readonly=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sended', 'Enviado'),
        ('updated', 'Actualizado'),
        ('annulled', 'Anulado'),
    ], string="Estado", default='draft', tracking=True)

    certificado_bancario_attch_ids = fields.Many2many(
        'ir.attachment', 'hr_employee_req_certificado_bancario_attchs', 'employee_id', 'attachment_id',
        string="Certificado Bancario",
        help="Adjunto del certificado bancario"
    )

    family_burden_ids = fields.One2many('hr.employee.update.request.burden', 'employee_id', 'Cargas Familiares')
    education_ids = fields.One2many('hr.employee.update.request.level', 'employee_id', 'Educación')
    contact_ids = fields.One2many('hr.employee.update.request.contact', 'employee_id', 'Contactos', required=True)

    full_name = fields.Char(string="Nombre Completo Formateado", compute="_compute_full_name", store=True)

    bank_id=fields.Many2one('res.bank',"Banco", required=False)
    bank_type = fields.Selection(BANK_TYPE, 'Tipo de Cuenta', required=False)
    account_number = fields.Char('Numero de Cuenta', size=20, required=False)
    tercero = fields.Boolean("Tercero", default=False, tracking=True, required=False)
    identificacion_tercero = fields.Char("# Identificacion Tercero", tracking=True, required=False)
    nombre_tercero = fields.Char("Nombre de Cuenta Tercero", tracking=True, required=False)
    # l10n_latam_identification_type_id = fields.Many2one("l10n_latam.identification.type", "Tipo de Identificacion",
    #                                                     tracking=True)
    l10n_latam_identification_tercero_id = fields.Many2one("l10n_latam.identification.type",
                                                           "Tipo de Identificacion Tercero", tracking=True)

    _rec_name="full_name"

    enable_bank_account = fields.Boolean("Habilitar Cuenta Bancaria", default=False)
    full_account_name=fields.Char('# Cuenta')

    country_id=fields.Many2one(related='employee_id.country_id',store=False,readonly=True)
    l10n_latam_identification_type_id=fields.Many2one(related='employee_id.l10n_latam_identification_type_id',store=False,readonly=True)
    identification_id=fields.Char(related="employee_id.identification_id",store=False,readonly=True)
    gender=fields.Selection(related="employee_id.gender",store=False,readonly=True)
    birthday=fields.Date(related="employee_id.birthday",store=False,readonly=True)

    @api.constrains('private_email')
    def _check_private_email_format(self):
        email_regex = r'^[^@]+@[^@]+\.[^@]+$'
        for user in self:
            email = user.private_email or ''
            if email and not re.match(email_regex, email):
                raise ValidationError(_("El correo privado ingresado no es válido."))

    @api.constrains('private_email')
    def _check_private_email_format_and_uniqueness(self):
        email_regex = r'^[^@]+@[^@]+\.[^@]+$'
        for emp in self:
            email = emp.private_email or ''
            if email:
                # Validar formato
                if not re.match(email_regex, email):
                    raise ValidationError(_("El correo privado ingresado no es válido."))

    @api.depends('employee_id.name', 'send_date', 'deadline_date')
    def _compute_full_name(self):
        for rec in self:
            if rec.employee_id and rec.send_date and rec.deadline_date:
                fecha_ini = rec.send_date.strftime('%d/%m/%Y')
                fecha_fin = rec.deadline_date.strftime('%d/%m/%Y')
                nombre = rec.employee_id.name.upper()
                rec.full_name = f"SOL. {nombre} DEL {fecha_ini} AL {fecha_fin}"
            else:
                rec.full_name = ""

    # Método onchange para prellenar con datos actuales
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.private_street = self.employee_id.address_home_id.street or "."
            self.private_street2 = self.employee_id.address_home_id.street2 or "."
            self.private_email = self.employee_id.private_email or ""
            self.phone = self.employee_id.address_home_id.phone or "."

    def action_send(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.state = 'sended'
            rec.message_post(body=_("La solicitud ha sido enviada para revisión."))

    def action_draft(self):
        for rec in self:
            if rec.state != 'sended':
                continue
            rec.state = 'draft'
            rec.message_post(body=_("La solicitud ha regresado a borrador para que realice las modificaciones necesarias"))


    def action_update(self):
        for rec in self:
            if rec.state != 'sended':
                raise ValidationError(_("Solo se pueden aplicar solicitudes en estado 'Enviado'."))

            employee = rec.employee_id.with_context(bypass_from_action=True)

            # Actualizar datos simples
            if employee.address_home_id:
                employee.address_home_id.with_context(bypass_from_action=True).write({
                    'street': rec.private_street,
                    'street2': rec.private_street2,
                    'phone': rec.phone,
                })
            employee_vals={
                'private_email': rec.private_email,
                'certificado_bancario_attch_ids': [(6, 0, rec.certificado_bancario_attch_ids.ids)],
            }
            if rec.enable_bank_account:
                employee_vals.update({
                'bank_id': rec.bank_id.id if rec.bank_id else False,
                'bank_type': rec.bank_type,
                'account_number': rec.account_number,
                'tercero': rec.tercero,
                'identificacion_tercero': rec.identificacion_tercero,
                'nombre_tercero': rec.nombre_tercero,
                'l10n_latam_identification_tercero_id': rec.l10n_latam_identification_tercero_id.id if rec.l10n_latam_identification_tercero_id else False

            })
            employee.with_context(bypass_from_action=True).write(employee_vals)

            # Cargas familiares (reemplazo total)
            burden_lines = [(5, 0, 0)]
            for burden in rec.family_burden_ids:
                burden_lines.append((0, 0, {
                    'name': burden.name,
                    'relationship': burden.relationship,
                    'other_relationship': burden.other_relationship,
                    'type_disability': burden.type_disability.id if burden.type_disability else False,
                    'percent_disability': burden.percent_disability,
                    'working': burden.working,
                    'email_personal': burden.email_personal,
                    'work_place': burden.work_place,
                    'work_phone': burden.work_phone,
                    'cell_phone': burden.cell_phone,
                    'bonus': burden.bonus,
                    'discapacidad': burden.discapacidad,
                    'genero': burden.genero,
                    'para_deduccion_gastos': burden.para_deduccion_gastos,
                    'birth_date': burden.birth_date,
                }))
            employee.with_context(bypass_from_action=True).family_burden_ids = burden_lines

            # Educación (reemplazo total)
            education_lines = [(5, 0, 0)]
            for edu in rec.education_ids:
                education_lines.append((0, 0, {
                    'title': edu.title,
                    'country_id': edu.country_id.id if edu.country_id else False,
                    'institution': edu.institution,
                    'start_date': edu.start_date,
                    'end_date': edu.end_date,
                    'level': edu.level,
                    'status': edu.status,
                    'education_area_id': edu.education_area_id.id if edu.education_area_id else False,
                }))
            employee.with_context(bypass_from_action=True).education_ids = education_lines

            # Contactos (reemplazo total)
            contact_lines = [(5, 0, 0)]
            for contact in rec.contact_ids:
                contact_lines.append((0, 0, {
                    'name_contact': contact.name_contact,
                    'parentesco': contact.parentesco,
                    'direccion': contact.direccion,
                    'personal_email': contact.personal_email,
                    'home_phone': contact.home_phone,
                    'home_mobile': contact.home_mobile,
                    'emergency_home_phone': contact.emergency_home_phone,
                    'emergency_home_mobile': contact.emergency_home_mobile,
                }))
            employee.with_context(bypass_from_action=True).contact_ids = contact_lines

            # Marcar solicitud como actualizada
            rec.with_context(bypass_from_action=True).state = 'updated'
            rec.with_context(bypass_from_action=True).message_post(body=_("Los datos del empleado han sido actualizados correctamente."))

    def action_annul(self):
        for rec in self:
            if rec.state in ['updated', 'annulled']:
                continue
            rec.state = 'annulled'
            rec.message_post(body=_("La solicitud ha sido anulada."))

    @api.model
    def _where_calc(self, domain, active_test=True):
        # Si no se proporciona un dominio, inicializamos como vacío
        domain = domain or []

        # Si el contexto tiene "only_user", no modificamos el dominio
        if not self._context.get("only_user", False):
            return super(HrEmployeeUpdateRequest, self)._where_calc(domain, active_test)

        # Obtener el usuario actual
        user = self.env["res.users"].sudo().browse(self._uid)

        # Comprobar si el usuario tiene permisos de grupo 'group_empleados_usuarios'
        if user.has_group("gps_hr.group_empleados_usuarios"):
            # Buscar el empleado relacionado con el usuario
            employee = self.env["hr.employee"].sudo().search([('user_id', '=', user.id)], limit=1)

            # Si encontramos un empleado, modificamos el dominio para filtrar por su ID
            if employee:
                domain.append(("employee_id", "in", tuple(employee.ids + [-1, -1])))
            else:
                domain.append(("employee_id", "=", -1))
        # Llamar a la función original con el dominio modificado
        return super(HrEmployeeUpdateRequest, self)._where_calc(domain, active_test)

class HrEmployeeUpdateRequestContact(models.Model):
    _name = 'hr.employee.update.request.contact'

    employee_id = fields.Many2one('hr.employee.update.request', 'Solicitud', ondelete="cascade")
    name_contact = fields.Char('Nombre', size=64)
    parentesco = fields.Char('Parentesco', size=240)
    direccion = fields.Char('Direccion', size=64)
    personal_email = fields.Char('E-mail Personal', size=240)
    home_phone = fields.Char('Telefono Domicilio', size=10)
    home_mobile = fields.Char('Telefono Celular', size=10)
    emergency_home_phone = fields.Char('Telefono de Emergencia', size=10)
    emergency_home_mobile = fields.Char('Celular de Emergencia', size=10)


class HrEmployeeUpdateRequestBurden(models.Model):
    _inherit = "th.family"
    _name = "hr.employee.update.request.burden"

    @api.model
    def _get_selection_relationship(self):
        return [('child', 'Hijo/Hija'),
                ('wife_husband', 'Conyugue'),
                ('father_mother', 'Padre/Madre')]

    relationship = fields.Selection(selection=_get_selection_relationship,string= 'Parentesco', default='child')
    other_relationship = fields.Char('Otra Relacion', size=256)
    type_disability = fields.Many2one('hr.disability.type', 'Tipo de Discapacidad')
    percent_disability = fields.Float('% Discapacidad')
    working = fields.Boolean('Trabaja?')
    email_personal = fields.Char('EmailPersonal', size=256)
    work_place = fields.Char('Lugar de Trabajo', size=200)
    work_phone = fields.Char('Telefono de Trabajo', size=32)
    cell_phone = fields.Char('Celular', size=32)
    bonus = fields.Boolean('Bonos?')
    discapacidad = fields.Boolean('Discapacidad?')
    genero = fields.Selection([
        ('Hombre', 'Hombre'),
        ('Mujer', 'Mujer'),
    ], 'Sexo', default='Hombre')
    para_deduccion_gastos = fields.Boolean('Para Deduccion de G. Personales?', default='True')
    employee_id = fields.Many2one('hr.employee.update.request', 'Solicitud', ondelete="cascade")



    @api.depends('birth_date')
    def _get_work_datas(self):
        for brw_each in self:
            age = 0
            if brw_each.birth_date:
                age = dtObj.years(fields.Date.context_today(self), brw_each.birth_date)
            brw_each.age = age

    age = fields.Integer(string='Edad', compute="_get_work_datas")
    birth_date = fields.Date(groups=None,string="Fecha de Nacimiento")

    @api.onchange('birth_date')
    def onchange_birth_date(self):
        age = 0
        warning = {}
        if self.birth_date is not None and self.birth_date:
            if self.birth_date > fields.Date.context_today(self):
                warning = {"title": _("Error"), "message": _(
                    "Fecha de Nacimiento no puede ser mayor  a la fecha actual")}
            age = dtObj.years(fields.Date.context_today(self), self.birth_date)
        self.age = age
        if warning:
            return {"warning": warning}

    @api.onchange('name')
    def onchange_name(self):
        self.name = self.name and self.name.upper() or None

class HrEmployeeUpdateRequestLevel(models.Model):
    _name = "hr.employee.update.request.level"

    title = fields.Char('Titulo', size=255)
    country_id = fields.Many2one('res.country', 'Country')
    institution = fields.Char('Institucion', size=255, )
    start_date = fields.Date('Fecha Inicio')
    end_date = fields.Date('Fecha Fin')
    level = fields.Selection([
        ('primary', 'Educación primaria'),
        ('secondary', 'Educación secundaria'),
        ('higher', 'Educación superior'),
        ('bachelor', 'Licenciatura'),
        ('master', 'Maestría'),
        ('phd', 'Doctorado'),
    ], string='Nivel de Educación', default='primary')
    status = fields.Selection([
        ('graduated', 'Graduado'),
        ('ongoing', 'En curso'),
        ('abandoned', 'Abandonado'),
    ], 'Estado', default='ongoing')
    education_area_id = fields.Many2one('th.education.area', 'Area de Educacion', )
    employee_id = fields.Many2one('hr.employee.update.request', 'Solicitud', ondelete="cascade")