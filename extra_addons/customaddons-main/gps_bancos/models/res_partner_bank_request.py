from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError
import re

class ResPartnerBankRequest(models.Model):
    _name = 'res.partner.bank.request'
    _description = 'Solicitud de Cuenta Bancaria'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    type=fields.Selection([('created','Creacion'),('inactive','Inactivacion')],string="Tipo",default="created")
    acc_holder_name = fields.Char("Nombre del titular de la cuenta", tracking=True)
    acc_number = fields.Char("Número de cuenta", tracking=True)
    acc_type = fields.Selection([('iban', 'IBAN'), ('other', 'Otro')], string="Tipo", tracking=True)
    active = fields.Boolean("Activo", default=True, tracking=True)
    allow_out_payment = fields.Boolean("Enviar dinero",default=True, tracking=True)
    bank_bic = fields.Char("Código BIC/SWIFT", tracking=True)
    bank_id = fields.Many2one('res.bank', "Banco", tracking=True)
    bank_name = fields.Char("Nombre", tracking=True)
    company_id = fields.Many2one('res.company', string="Compañía",  tracking=True)
    currency_id = fields.Many2one('res.currency', string="Moneda", tracking=True)
    display_name = fields.Char("Nombre a Mostrar", tracking=True)
    request_name=fields.Char("# Cuenta",compute="_get_compute_request_name",store=True,readonly=True,size=255)
    identificacion_tercero = fields.Char("# Identificación Tercero", tracking=True)
    is_default = fields.Boolean("Por defecto", tracking=True)
    l10n_latam_identification_tercero_id = fields.Many2one('l10n_latam.identification.type', "Tipo Identificación", tracking=True)
    nombre_tercero = fields.Char("Nombre de Cuenta Tercero", tracking=True)
    partner_email = fields.Char("Correo", tracking=True)
    partner_id = fields.Many2one('res.partner', string="Titular", tracking=True)
    sequence = fields.Integer("Secuencia", tracking=True)
    tercero = fields.Boolean("Tercero", tracking=True)
    tipo_cuenta = fields.Selection([
        ('Corriente', 'Cuenta de Corriente'),
        ('Ahorro', 'Cuenta de Ahorro'),
    ], string="Tipo de Cuenta", tracking=True)
    state = fields.Selection([
        ('draft', 'Preliminar'),
        ('sent', 'Enviado'),
        ('created', 'Creado'),
        ('updated', 'Actualizado'),
        ('cancelled', 'Anulado'),
    ], string='Estado', default='draft', required=True, tracking=True)

    partner_bank_id=fields.Many2one('res.partner.bank',"# Cuenta Bancaria Creada")
    employee_id=fields.Many2one('hr.employee','Empleado')

    origen = fields.Selection([
        ('talento_humano', 'Talento Humano'),
        ('manual', 'Financiero'),
        ('compras', 'Compras'),
    ], string="Origen", tracking=True)

    comments=fields.Text("Motivo")



    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.partner_bank_id=False

    @api.onchange('partner_bank_id')
    def _onchange_partner_bank_id(self):
        if self.partner_bank_id:
            field_names = [
                'bank_id',
                'tipo_cuenta',
                'acc_number',
                'tercero',
                'l10n_latam_identification_tercero_id',
                'identificacion_tercero',
                'nombre_tercero',
                'allow_out_payment',
                'partner_email',
                'active',
                'acc_holder_name',
            ]
            for field in field_names:
                if hasattr(self.partner_bank_id, field):
                    setattr(self, field, getattr(self.partner_bank_id, field))

    def action_reset_draft(self):
        for record in self:
            if record.state not in ['sent', 'cancelled']:
                raise UserError("Solo se puede volver a preliminar desde 'Enviado' o 'Anulado'.")
            record.state = 'draft'
            record.message_post(
                body=_("La solicitud ha sido devuelta a estado <strong>Preliminar</strong> por revisión."),
                partner_ids=[record.create_uid.partner_id.id],
            )
            self.env.user.notify_info("Solicitud restablecida como preliminar")

    def _notify_creator_if_needed(self):
        for rec in self:
            if rec.create_uid and rec.create_uid.partner_id:
                if rec.create_uid.partner_id.id not in rec.message_follower_ids.mapped('partner_id').ids:
                    rec.message_subscribe(partner_ids=[rec.create_uid.partner_id.id])

    def action_send(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("Solo se pueden enviar solicitudes en estado preliminar.")
            group_xml_ids = [
                'gps_bancos.group_creador_cuentas',
                #'gps_bancos.group_admin_documentos_bancarios',
            ]
            partner_ids_to_subscribe = []

            for group_xml in group_xml_ids:
                group = self.env.ref(group_xml, raise_if_not_found=False)
                if group:
                    partner_ids_to_subscribe += group.users.mapped('partner_id.id')

            # Quitar duplicados y suscribir
            if partner_ids_to_subscribe:
                partner_ids_to_subscribe=list(set(partner_ids_to_subscribe))

            # Cambiar estado y notificar
            record.state = 'sent'
            type_dscr="creación"
            if record.type=='inactive':
                type_dscr = "anulación"
            record.message_post(
                body=_(
                    "Estimados, por favor confirmar la solicitud de %s de cuenta bancaria.<br/><br/>"
                    "<strong>Datos de la cuenta:</strong><br/>"
                    "Titular: %s<br/>"
                    "Banco: %s<br/>"
                    "Número de cuenta: %s<br/>"
                    "Tipo de cuenta: %s"
                ) % (type_dscr,
                         record.partner_id.name or '',
                         record.bank_id.name or '',
                         record.acc_number or '',
                         dict(record._fields['tipo_cuenta'].selection).get(record.tipo_cuenta, '')
                     ),
                partner_ids=partner_ids_to_subscribe
            )
            self.env.user.notify_info("Solicitud enviada correctamente")

    def action_create_account(self):
        for record in self:
            if record.state != 'sent':
                raise UserError("Solo se pueden crear cuentas desde el estado 'Enviado'.")

                # Validación de existencia previa
            existing_account = self.env['res.partner.bank'].search([
                ('partner_id', '=', record.partner_id.id),
                ('bank_id', '=', record.bank_id.id),
                ('acc_number', '=', record.acc_number),
            ], limit=1)

            if existing_account:
                raise UserError(
                    _("Ya existe una cuenta bancaria registrada con el mismo Titular, Banco y Número de Cuenta."))

            # Crear cuenta si no existe
            vals = {
                'acc_holder_name': record.acc_holder_name,
                'acc_number': record.acc_number,
                'acc_type': record.acc_type,
                'active': record.active,
                'allow_out_payment': record.allow_out_payment,
                #'bank_bic': record.bank_bic,
                'bank_id': record.bank_id.id,
                'company_id': record.company_id and record.company_id.id or False,
                'currency_id': record.currency_id and record.currency_id.id or False,
                #'display_name': record.display_name,
                #'request_name': record.request_name,
                'identificacion_tercero': record.identificacion_tercero,
                'is_default': record.is_default,
                'l10n_latam_identification_tercero_id': record.l10n_latam_identification_tercero_id and record.l10n_latam_identification_tercero_id.id or False,
                'nombre_tercero': record.nombre_tercero,
                'partner_email': record.partner_email,
                'partner_id': record.partner_id.id,
                'sequence': record.sequence,
                'tercero': record.tercero,
                'tipo_cuenta': record.tipo_cuenta,
            }

            partner_bank_id=self.env['res.partner.bank'].create(vals)
            record.state = 'created'
            record.partner_bank_id=partner_bank_id.id
            if record.employee_id:
                record.employee_id.bank_account_id = partner_bank_id.id
            record.message_post(
                body=_("La cuenta ha sido <strong>creada</strong> exitosamente desde esta solicitud."),
                partner_ids=[record.create_uid.partner_id.id],
            )
            self.env.user.notify_info("Cuenta creada exitosamente")

    def action_cancel(self):
        for record in self:
            last_state=record.state
            record.state = 'cancelled'
            if last_state!='draft':
                type_dscr = "creación"
                if record.type == 'inactive':
                    type_dscr = "anulación"
                record.message_post(
                    body=_("La solicitud de %s ha sido <strong>anulada</strong>.") % (type_dscr,),
                    partner_ids=[record.create_uid.partner_id.id],
                )
                self.env.user.notify_info("Solicitud anulada")

    @api.depends('type','tipo_cuenta','acc_number','bank_id','partner_bank_id')
    @api.onchange('type','tipo_cuenta', 'acc_number', 'bank_id','partner_bank_id')
    def _get_compute_request_name(self):
        for brw_each in self:
            type_dscr = "Creación"
            if brw_each.type == 'inactive':
                type_dscr = "Anulación"
            request_name="Sol. de %s Cta %s # %s,%s" % (type_dscr,brw_each.tipo_cuenta,brw_each.acc_number or '',brw_each.bank_id and brw_each.bank_id.name or '')
            brw_each.request_name=request_name
            print(request_name)



    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.acc_holder_name=self.partner_id and self.partner_id.name or None

    @api.onchange('tercero')
    def onchange_tercero(self):
        def get_identification_tipo_id(brw_parent):
            if brw_parent.country_id and brw_parent.country_id.code == 'EC':  # Verifica si el país es Ecuador
                if brw_parent.l10n_latam_identification_type_id == self.env.ref('l10n_ec.ec_ruc'):
                    return self.env.ref('l10n_ec.ec_dni')
            return False
        if not self.tercero:
            self.l10n_latam_identification_tercero_id=False
            self.identificacion_tercero=None
            self.nombre_tercero=None
        else:
            brw_parent=self.partner_id._origin
            identification_tipo_id=get_identification_tipo_id(brw_parent)
            if identification_tipo_id:
                self.l10n_latam_identification_tercero_id = identification_tipo_id
                self.identificacion_tercero = brw_parent.vat and brw_parent.vat[:-3]
            else:
                self.identificacion_tercero = brw_parent.vat
            self.nombre_tercero = self.partner_id.name

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Solo se pueden eliminar solicitudes en estado borrador.'))
        return super(ResPartnerBankRequest, self).unlink()

    def validate_acc_numbers(self):
       for brw_each in self:
           if brw_each.partner_id.country_id==self.env.ref('base.ec'):
               acc_number=brw_each.acc_number
               if not re.fullmatch(r'[0-9]+', acc_number) or re.fullmatch(r'0+', acc_number):
                    raise ValidationError(
                        _("La cuenta bancaria asociada para %s debe contener solo números y no ser todo ceros.") % (
                                brw_each.partner_id.name,))

    @api.model
    def create(self, vals):
        record = super(ResPartnerBankRequest,self).create(vals)
        record.validate_acc_numbers()
        return record

    def write(self, vals):
        res = super(ResPartnerBankRequest,self).write(vals)
        self.validate_acc_numbers()
        return res

    @api.constrains('partner_email')
    def _check_partner_email(self):
        email_regex = r"[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+"
        for record in self:
            if record.partner_email:
                emails = [e.strip() for e in record.partner_email.split(',')]
                for email in emails:
                    if not re.fullmatch(email_regex, email):
                        raise ValidationError(_(f"El correo '{email}' no tiene un formato válido."))

    @api.onchange('tercero', 'partner_id', 'nombre_tercero')
    def onchange_nombre_tercero(self):
        if not self.tercero:
            self.acc_holder_name = self.partner_id.name
        else:
            self.acc_holder_name = self.nombre_tercero

    def action_update(self):
        for brw_each in self:
            brw_each.partner_bank_id._write({"active":False})
            brw_each.state="updated"
            brw_each.message_post(
                body=_("La cuenta ha sido <strong>inactivada</strong> exitosamente desde esta solicitud."),
                partner_ids=[brw_each.create_uid.partner_id.id],
            )
            self.env.user.notify_info("Cuenta inactivada exitosamente")

    _rec_name = "request_name"


