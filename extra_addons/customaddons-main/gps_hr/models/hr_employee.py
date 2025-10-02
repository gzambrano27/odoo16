# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError,UserError
import re
from datetime import timedelta

BANK_TYPE = [('checking', 'Corriente'), ('savings', 'Ahorros')]

class HrEmployee(models.Model):
    _inherit="hr.employee"

    @api.model
    def _get_selection_marital(self):
        return [
            ('single', 'Soltero(a)'),
            ('married', 'Casado (a)'),
            ('widower', 'Viudo(a)'),
            ('divorced', 'Divorciado(a)'),
            ('free_union', 'Unión libre'),
            ('union_hecho', 'Unión de Hecho')
        ]

    @api.model
    def _get_selection_gender(self):
        return [
            ('male', 'Masculino'),
            ('female', 'Femenino')
        ]

    @api.model
    def _get_default_country_id(self):
        brw_user=self.env["res.users"].sudo().browse(self._uid)
        return brw_user.company_id.country_id and brw_user.company_id.country_id.id or False

    previous_day_contract=fields.Integer("Dias Previos Contrato",default=0,tracking=True )
    tipo_rol = fields.Many2one('tipo.roles', required=False)
    unidad_administrativa = fields.Many2one('establecimientos', required=False)

    marital = fields.Selection(selection=_get_selection_marital, string='Estado civil', groups=None, default="single",tracking=True)
    gender = fields.Selection(selection=_get_selection_gender, string='Género', groups=None, default="male",tracking=True)

    private_street= fields.Char(related='address_home_id.street', string="Calle privado", groups=None,store=True,readonly=False ,tracking=True,default=".")
    private_street2 = fields.Char(related='address_home_id.street2', string="Calle 2 privado", groups=None,store=True,readonly=False,tracking=True,default=".")

    private_email = fields.Char(related=None, string="Correo electronico privado", groups=None,store=True,readonly=False,tracking=True)
    phone = fields.Char(related='address_home_id.phone',string="Teléfono privado", groups=None,store=True,readonly=False,tracking=True,default=".")

    partner_id = fields.Many2one("res.partner", string="Proveedor", groups=None,tracking=True)
    ruc_partner_id = fields.Many2one("res.partner", string="Proveedor con RUC", groups=None, tracking=True)

    address_home_id=fields.Many2one("res.partner",compute="_get_compute_address",store=True,readonly=True,groups=None)

    country_id = fields.Many2one("res.country", groups=None,default=_get_default_country_id,tracking=True)
    country_of_birth = fields.Many2one("res.country",  groups=None,default=_get_default_country_id,tracking=True)

    job_id = fields.Many2one("hr.job",  string="Cargo",groups=None, domain=[])
    bank_id = fields.Many2one("res.bank",required=False, string="Banco", groups=None, domain=[])

    ciudad_inicio = fields.Char('Ciudad', required=False)

    tiene_ruc=fields.Boolean(string="Tiene RUC",default=False,tracking=True)

    tercero = fields.Boolean("Tercero", default=False,tracking=True)
    identificacion_tercero = fields.Char("# Identificacion Tercero",tracking=True)
    nombre_tercero = fields.Char("Nombre de Cuenta Tercero",tracking=True)
    l10n_latam_identification_type_id=fields.Many2one("l10n_latam.identification.type","Tipo de Identificacion",tracking=True)
    l10n_latam_identification_tercero_id = fields.Many2one("l10n_latam.identification.type", "Tipo de Identificacion Tercero",tracking=True)
    contract_history_ids = fields.One2many("hr.contract.history", "employee_id", "Historial de Contratos")

    allowed_company_ids = fields.Many2many("res.company", "hr_employee_contract_company_rel", "contract_id", "company_id",
                                           store=True, compute="_get_compute_allowed_company_ids", string="Empresas")

    department_id=fields.Many2one('hr.department',string="Departamento",domain=[])
    parent_id = fields.Many2one('hr.employee',   domain=[])
    coach_id = fields.Many2one('hr.employee',   domain=[])

    pay_with_transfer=fields.Boolean("Pagar con Transferencia",default=True)

    profile_ids = fields.Many2many(
        'res.groups',
        string='Perfiles',
        domain="[('is_profile', '=', True)]",
        help='Grupos marcados como perfil'
    )

    bank_type = fields.Selection(BANK_TYPE, 'Tipo de Cuenta', required=False)
    account_number = fields.Char('Numero de Cuenta', size=20, required=False)

    certificado_bancario_attch_ids= fields.Many2many(
        'ir.attachment','hr_employee_certificado_bancario_attchs','employee_id','attachment_id',
        string="Certificado Bancario",
        help="Adjunto del certificado bancario"
    )

    resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Horario de Trabajo',
        default=lambda self: self._default_resource_calendar()
    )

    @api.model
    def _default_resource_calendar(self):
        return self.env['resource.calendar'].search([
            ('default', '=', True),
            ('active', '=', True),
            ('company_id', '=', False)
        ], limit=1)

    def create_update_request(self):
        created_requests = self.env['hr.employee.update.request']

        for employee in self:
            existing_request = self.env['hr.employee.update.request'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['draft', 'sended']),
            ], limit=1)

            if existing_request:
                raise ValidationError(_(
                    "Ya existe una solicitud pendiente (borrador o enviada) para el empleado: %s."
                ) % employee.name)

            today = fields.Date.context_today(employee)
            deadline_date = self._context.get("deadline_date", today + timedelta(days=7))
            enable_bank_account= self._context.get("enable_bank_account", True)

            update_request_vals = {
                'employee_id': employee.id,
                'private_street': employee.address_home_id.street or ".",
                'private_street2': employee.address_home_id.street2 or ".",
                'phone': employee.address_home_id.phone or ".",
                'private_email': employee.private_email or "",
                'send_date': today,
                'deadline_date': deadline_date,
                'certificado_bancario_attch_ids':[(6,0,employee.certificado_bancario_attch_ids.ids)],
                "enable_bank_account":enable_bank_account,
                ###################################################
                'bank_id': employee.bank_id.id if employee.bank_id else False,
                'bank_type': employee.bank_type,
                'account_number': employee.account_number,
                'tercero': employee.tercero,
                'identificacion_tercero': employee.identificacion_tercero,
                'nombre_tercero': employee.nombre_tercero,
                'l10n_latam_identification_tercero_id': employee.l10n_latam_identification_tercero_id.id if employee.l10n_latam_identification_tercero_id else False,

            }

            # Cargas familiares
            burden_vals = []
            for burden in employee.family_burden_ids:
                burden_vals.append((0, 0, {
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
            update_request_vals['family_burden_ids'] = burden_vals

            # Educación
            education_vals = []
            for edu in employee.education_ids:
                education_vals.append((0, 0, {
                    'title': edu.title,
                    'country_id': edu.country_id.id if edu.country_id else False,
                    'institution': edu.institution,
                    'start_date': edu.start_date,
                    'end_date': edu.end_date,
                    'level': edu.level,
                    'status': edu.status,
                    'education_area_id': edu.education_area_id.id if edu.education_area_id else False,
                }))
            update_request_vals['education_ids'] = education_vals

            # Contactos
            contact_vals = []
            for contact in employee.contact_ids:
                contact_vals.append((0, 0, {
                    'name_contact': contact.name_contact,
                    'parentesco': contact.parentesco,
                    'direccion': contact.direccion,
                    'personal_email': contact.personal_email,
                    'home_phone': contact.home_phone,
                    'home_mobile': contact.home_mobile,
                    'emergency_home_phone': contact.emergency_home_phone,
                    'emergency_home_mobile': contact.emergency_home_mobile,
                }))
            update_request_vals['contact_ids'] = contact_vals

            # Crear la solicitud
            req = self.env['hr.employee.update.request'].create(update_request_vals)
            #req.action_send()
            created_requests |= req

        # Devolver vista con filtro de todas las solicitudes creadas
        return {
            'name': _("Solicitudes de Actualización Creadas"),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.update.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_requests.ids)],
            'context': self.env.context,
        }

    @api.depends('contract_history_ids')
    @api.onchange('contract_history_ids')
    def _get_compute_allowed_company_ids(self):
        for brw_each in self:
            allowed_company_ids = brw_each.contract_history_ids.filtered(lambda x: x.state == 'open')
            if not allowed_company_ids:
                allowed_company_ids = brw_each.company_id
            else:
                allowed_company_ids = allowed_company_ids.mapped('company_id')
            brw_each.allowed_company_ids = allowed_company_ids

    @api.onchange('first_name','last_name','second_name','mother_last_name')
    def onchange_names(self):
        self.first_name=self.first_name and self.first_name.upper() or ""
        self.last_name = self.last_name and self.last_name.upper() or ""
        self.second_name = self.second_name and self.second_name.upper() or ""
        self.mother_last_name = self.mother_last_name and self.mother_last_name.upper() or ""
        self.name="%s %s %s %s" % ( self.last_name ,self.mother_last_name,self.first_name,self.second_name)

    @api.onchange('partner_id')
    @api.depends('partner_id')
    def _get_compute_address(self):
        for brw_each in self:
            brw_each.address_home_id=brw_each.partner_id

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args=[]
        if "filter_rule_id" in self._context:
            args = self.filter_by_rule_id(args, self._context.get("filter_date_process", None),
                                            self._context.get("model_name", None),
                                            self._context.get("document_id", False),
                                            self._context.get("filter_rule_id", False),
                                            self._context.get("filter_company_id", False),
                                            self._context.get("filter_legal_iess", False))
        if "filter_type_struct_id" in self._context:
            #structs_by_type=self.env["hr.payroll.structure"].sudo().search([('type_id','=',self._context["filter_type_struct_id"])])
            #structs_ids=structs_by_type.ids+[-1,-1]
            filter_legal_iess = self._context.get("filter_legal_iess", False)

            srch_contract=self.env["hr.contract"].sudo().search([('state', 'in', ('open', )),
             ('company_id', '=', self.env.company.id),
             #('contract_type_id','in',structs_ids),
             ('contract_type_id.legal_iess', '=', filter_legal_iess),
             ])
            employees=srch_contract.mapped('employee_id').ids
            employees+=[-1]
            args+= [('id','in',employees)]
        result = super(HrEmployee, self).name_search(name=name, args=args, operator=operator, limit=limit)
        return result

    @api.model
    def update_data_contracts_employees(self, update_vals):
        update_vals=super(HrEmployee,self).update_data_contracts_employees(update_vals)
        return update_vals

    @api.model
    def _where_calc(self, domain, active_test=True):
        if not domain:
            domain = []
        if "filter_rule_id" in self._context:
            domain = self.filter_by_rule_id(domain, self._context.get("filter_date_process",None),
                                            self._context.get("model_name",None),
                                            self._context.get("document_id",False),
                                            self._context.get("filter_rule_id",False),
                                            self._context.get("filter_company_id",False),
                                            self._context.get("filter_legal_iess", False))
        if "filter_type_struct_id" in self._context:
            filter_legal_iess = self._context.get("filter_legal_iess", False)
            inactive = self._context.get('inactive', False)
            state = 'open'
            domain_contract = [
                ('company_id', '=', self.env.company.id),
                ('contract_type_id.legal_iess', '=',
                 filter_legal_iess),
            ]
            if inactive:
                state = 'close'
                domain_contract += [('date_end', '<=', self._context.get("filter_date_process", False))]
                domain_contract += [('date_end', '>=', self._context.get("filter_date_start", False))]
            domain_contract += [('state', 'in', (state,)), ]
            srch_contract = self.env["hr.contract"].sudo().search(domain_contract)
            employees = srch_contract.mapped('employee_id').ids
            employees += [-1]
            domain+= [('id','in',employees)]
        if "inactive" in self._context:
            # Mostrar solo empleados inactivos
            active_test = False
            #domain += [('active', '=', False)]
        return super(HrEmployee, self)._where_calc(domain, active_test)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if domain is None:
            domain = []
        if "filter_rule_id" in self._context:
            domain = self.filter_by_rule_id(domain, self._context.get("filter_date_process",None),
                                            self._context.get("model_name",None),
                                            self._context.get("document_id",False),
                                            self._context.get("filter_rule_id",False),
                                            self._context.get("filter_company_id",False),
                                            self._context.get("filter_legal_iess", False))
        if "filter_type_struct_id" in self._context:
            # structs_by_type=self.env["hr.payroll.structure"].sudo().search([('type_id','=',self._context["filter_type_struct_id"])])
            # structs_ids=structs_by_type.ids+[-1,-1]
            filter_legal_iess = self._context.get("filter_legal_iess", False)
            inactive = self._context.get('inactive', False)
            state = 'open'
            domain_contract = [
                ('company_id', '=', self.env.company.id),
                # ('contract_type_id','in',structs_ids),
                ('contract_type_id.legal_iess', '=',
                 filter_legal_iess),
            ]
            if inactive:
                state = 'close'
                domain_contract += [('date_end', '<=', self._context.get("filter_date_process", False))]
                domain_contract += [('date_end', '>=', self._context.get("filter_date_start", False))]
            domain_contract += [('state', 'in', (state,)), ]
            srch_contract = self.env["hr.contract"].sudo().search(domain_contract)
            employees = srch_contract.mapped('employee_id').ids
            employees += [-1]
            domain+= [('id','in',employees)]
        return super(HrEmployee, self).search_read(
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order=order,
        )

    @api.model
    def filter_by_rule_id(self,domain,filter_date_process,model_name,document_id, filter_rule_id,filter_company_id,filter_legal_iess):
        if domain is None:
            domain=[]
        filter_legal_iess = self._context.get("filter_legal_iess", False)

        srch_contract = self.env["hr.contract"].sudo().search([('state', 'in', ('open',)),
                                                               ('company_id', '=', filter_company_id),
                                                               ('contract_type_id.legal_iess', '=', filter_legal_iess),
                                                               ('date_start', '<=',filter_date_process),
                                                               ])
        contract_ids=srch_contract.ids
        contract_ids+=[-1,-1]
        self._cr.execute(f"""select employee_id,employee_id from hr_contract where id in %s order by employee_id asc """,(tuple(contract_ids),))
        result=self._cr.fetchall()
        employees=[*dict(result)]
        employees += [-1,-1]
        domain += [('id', 'in', tuple(employees))]
        return domain

    def action_contact_create_validate(self):
        Partner = self.env['res.partner'].with_context(bypass_partner_restriction=True)
        Bank = self.env['res.partner.bank']
        Movement = self.env['hr.employee.movement']

        for employee in self:
            if not employee.identification_id:
                raise ValidationError(_("Debes definir el # de identificación"))

            # Construir datos del contacto
            partner_vals = {
                'name': employee.name,
                'email': employee.work_email or employee.private_email,
                'phone': employee.phone,
                'street': employee.private_street,
                'street2': employee.private_street2,
                'vat': employee.identification_id,
                'company_id': False,
                'l10n_latam_identification_type_id': employee.l10n_latam_identification_type_id.id if employee.l10n_latam_identification_type_id else False,
                'company_type': "person",
                'is_customer': True,
                'is_supplier': True,
                'country_id': employee.country_id.id if employee.country_id else False,
                'function': (employee.contract_id.job_id.name if employee.contract_id else employee.job_id.name)
            }

            # Validar número de cuenta y preparar datos bancarios
            bank_vals = {}
            if employee.pay_with_transfer:
                Movement.validate_acc_numbers(employee.account_number, employee)
                bank_vals = {
                    'bank_id': employee.bank_id.id,
                    'acc_number': employee.account_number,
                    'tipo_cuenta': 'Corriente' if employee.bank_type == 'checking' else 'Ahorro',
                    'currency_id': employee.company_id.currency_id.id,
                    'acc_holder_name': employee.name,
                    'tercero': employee.tercero,
                    'identificacion_tercero': employee.identificacion_tercero,
                    'nombre_tercero': employee.nombre_tercero,
                    'l10n_latam_identification_tercero_id': employee.l10n_latam_identification_tercero_id.id if employee.l10n_latam_identification_tercero_id else False,
                }

            # Buscar o crear contacto
            partner = employee.work_contact_id.with_context(bypass_partner_restriction=True)
            if not partner:
                partners = Partner.sudo().search([('vat', '=', employee.identification_id)])
                if not partners:
                    try:
                        partner = Partner.with_context(bypass_partner_restriction=True).create(partner_vals)
                        self.env.user.notify_info("Contacto creado correctamente")
                    except Exception as e:
                        raise ValidationError(f"Error al crear el contacto: {str(e)}")
                elif len(partners) == 1:
                    partner = partners[0].with_context(bypass_partner_restriction=True)
                    partner.write(partner_vals)
                    self.env.user.notify_info("Contacto actualizado correctamente")
                else:
                    raise ValidationError(
                        f"Existen más de un contacto con identificación {employee.identification_id}, nombre {employee.name}")
            else:
                partner.with_context(bypass_partner_restriction=True).write(partner_vals)
                self.env.user.notify_info("Contacto actualizado correctamente")

            # Crear o actualizar cuenta bancaria si aplica
            if bank_vals:
                bank_vals['partner_id'] = partner.id
                bank = Bank.search([
                    ('partner_id', '=', partner.id),
                    ('bank_id', '=', employee.bank_id.id),
                    ('acc_number', '=', employee.account_number)
                ])
                if not bank:
                    bank = Bank.create(bank_vals)
                elif len(bank) == 1:
                    bank.write(bank_vals)
                else:
                    raise ValidationError(
                        _("La siguiente combinación de cuentas bancarias %s , # %s") % (employee.bank_id.name,
                                                                                        employee.account_number))
            else:
                bank = False

            # Vincular contacto y cuenta al empleado
            update_vals = {
                'partner_id': partner.id,
            }
            if bank:
                update_vals['bank_account_id'] = bank.id
            employee._write(update_vals)

        return True

    def action_user_create(self):
        for employee in self:
            if not employee.user_id:
                user_vals = {
                    'name': employee.name,
                    'login':employee.identification_id,
                    'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
                }

                user = self.env['res.users'].with_context(bypass_partner_restriction=True).create(user_vals)
                employee.with_context(bypass_partner_restriction=True).user_id = user
                #self.env.user.notify_info(message='Usuario creado correctamente')
                # except Exception as e:
                #     self.env.user.notify_warning(message=f'Error al crear el usuario: {str(e)}')
        return True

    def action_user_create_validate(self):
        for employee in self:
            if not employee.user_id:
                user_vals = {
                    'name': employee.name,
                    'login':employee.identification_id,
                    'groups_id': [(6, 0, [self.env.ref('gps_hr.group_empleados_usuarios').id,
                                          self.env.ref('base.group_user').id])],
                }
                user = self.env['res.users'].with_context(bypass_partner_restriction=True).create(user_vals)
                employee.with_context(bypass_partner_restriction=True).write({
                    "user_id":user.id,
                    "work_contact_id":user.partner_id.id,
                    "partner_id": user.partner_id.id,
                })
                #employee.user_id = user
                #employee.partner_id=employee.user_id.partner_id
                self.env.user.notify_info(message='Usuario creado correctamente')
        return True

    @api.onchange('place_of_birth')
    def onchange_place_of_birth(self):
        self.place_of_birth=self.place_of_birth and self.place_of_birth.upper() or None

    @api.onchange('private_street')
    def onchange_private_street(self):
        self.private_street = self.private_street and self.private_street.upper() or None

    @api.onchange('private_street2')
    def onchange_private_street2(self):
        self.private_street2 = self.private_street2 and self.private_street2.upper() or None

    @api.model
    def create(self, vals):
        self = self.with_context(bypass_partner_restriction=True)
        def get_login(vls,lst):
            for each in lst:
                if vls[each] and len(vls[each])>0:
                    return vls[each]
            return ""
        user_vals = {
            'name': vals.get('name',''),
            'login': get_login(vals,['identification_id',]),#'work_email','private_email',
            'groups_id': [
                (6, 0, [self.env.ref('gps_hr.group_empleados_usuarios').id,
                        self.env.ref('base.group_user').id,
                        self.env.ref('base.group_private_addresses').id,
                        self.env.ref('base.group_no_one').id,
                        self.env.ref('hr_attendance.group_hr_attendance_kiosk').id,
                        self.env.ref('gps_users.group_can_login').id,
                        ])],
            'menu_ids':self.get_menu_automatic_hidden(),
            "lang":self.env["res.users"].sudo().browse(self._uid).lang
        }
        if not user_vals["login"] or len(user_vals["login"])<=0:
            raise ValidationError(_("Debes definir el correo para la creacion del usuario"))
        user = self.env['res.users'].with_context(bypass_partner_restriction=True).create(user_vals)
        vals["user_id"]=user.id
        vals["work_contact_id"] = user.partner_id.id
        vals["partner_id"] = user.partner_id.id
        vals["address_home_id"] = user.partner_id.id
        brw_new = super(HrEmployee, self).create(vals)
        brw_new.action_contact_create_validate()
        if vals.get('certificado_bancario_attch_ids'):
            brw_new.adjuntar_adjunto_bancario()
        return brw_new

    def write(self, vals):
        self=self.with_context(bypass_partner_restriction=True)
        values= super(HrEmployee, self).write(vals)
        for brw_each in self:
            brw_each.action_contact_create_validate()
            if 'certificado_bancario_attch_ids' in vals and vals['certificado_bancario_attch_ids']:
                brw_each.adjuntar_adjunto_bancario()
        return values

    @api.constrains('identification_id')
    def validate_identification(self):
        for brw_each in self:
            if brw_each.identification_id:
                srch_identification = self.search(
                    [('id', '!=', brw_each.id), ('identification_id', '=', brw_each.identification_id)])
                if len(srch_identification) > 0:
                    raise ValidationError(
                        _("Existe un empleado con la identificación %s ya registrada") % (brw_each.identification_id,))

    def _inverse_work_contact_details(self):
        for employee in self:
            if not employee.work_contact_id:
                srch=self.env['res.partner'].sudo().search([('vat','=',employee.identification_id)])
                if srch:
                    employee.work_contact_id=srch and srch[0].id or False
                else:
                    super(HrEmployee,employee)._inverse_work_contact_details()

    def get_menu_automatic_hidden(self):
        l=['base.menu_management',
'spreadsheet_dashboard.spreadsheet_dashboard_menu_root',
'contacts.menu_contacts',
'utm.menu_link_tracker_root',
'sale.sale_menu_root',
'hr.menu_hr_root',
'hr_holidays.menu_hr_holidays_root',
'material_purchase_requisitions.menu_purchase_requisition',
'planning.planning_menu_root',
'appsfolio_generic_import.generic_import_main_menu',
'maintenance.menu_maintenance_title',
'historical_master_gps.historical_gps_menu',
'gps_einvoice_received.gps_einvoice_received_menu_root',
           'construccion_gps.menu_budget_apu_root'
        ]
        lst_ids=[]
        for each_menu in l:
            lst_ids.append(self.env.ref(each_menu).id)
        return [(6,0,lst_ids)]

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

                # Validar unicidad
                duplicate = self.search([
                    ('id', '!=', emp.id),
                    ('private_email', '=', email)
                ], limit=1)
                if duplicate:
                    raise ValidationError(_("El correo privado ingresado no es válido."))

    @api.onchange('profile_ids')
    def _onchange_profile_ids_limit_selection(self):
        """Limitar a solo 1 perfil si el parámetro no permite múltiples"""
        config = self.env['ir.config_parameter'].sudo()
        allow_multiple = config.get_param('allow_multiple_profiles', '0') == '1'

        if not allow_multiple and len(self.profile_ids) > 1:
            raise ValidationError(_("Solo se permite un perfil asignado."))

    def action_copy_profile(self):
        for brw_each in self:
            if not brw_each.profile_ids:
                raise ValidationError(_("No se ha elegido un perfil"))
            if not brw_each.user_id:
                raise ValidationError(_("Debes designar un usuario"))
            for brw_profile in brw_each.profile_ids:
                brw_profile.copy_from_group([brw_each.user_id.id])
        return True

    def adjuntar_adjunto_bancario(self):
        self.ensure_one()
        if self.certificado_bancario_attch_ids:
            note_subtype = self.env.ref('mail.mt_note')

            # Publicar el mensaje en el chatter
            self.message_post(
                body="Se adjunta certificado bancario.",
                attachment_ids=self.certificado_bancario_attch_ids.ids,
                subtype_id=note_subtype.id,
            )

    control_marcaciones = fields.Boolean("Control Marcaciones", default=True)

