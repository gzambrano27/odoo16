# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import date
from email.policy import default
from json import dumps

#from pkg_resources import require

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import pytz

from odoo.netsvc import DEFAULT


#from lib2to3.fixes.fix_input import context
#from datetime import date
#context = dict(self.env.context) if isinstance(self.env.context, dict) else {}
#context['current_year'] = str(date.today().year)

class CrmLead(models.Model):
    _order = "create_year asc,company_id asc, priority desc, sequence asc"
    _inherit = "crm.lead"

    def button_approve(self):
        # Enviar el correo
        obj_correo = self.env['crm.correo']
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        current_datetime = fields.Datetime.now()
        current_datetime_local = pytz.utc.localize(current_datetime).astimezone(local_tz)
        if self.financiamiento:
            obj_correo = obj_correo.search([('tipo','=','Financiamiento'),('estado','=','Activo')])
            mensaje = obj_correo.description
            mensaje1 = ("""
            %s
            </br>           
            <div class="pos-customer_facing_display">
                <p>Nombre del Proyecto: %s</p>
                </br>
                <p>Descripcion del Proyecto: %s</p></br> 
                <p>Nombre del Contacto: %s</p></br>
                <p>Correo del Contacto: %s</p> 
            </div> 
            
            """)%(mensaje, self.name, self.description, self.contacto_financiamiento, self.correo_contacto_financiamiento)
            mail_values = {
                'subject': f'Financiamiento {current_datetime_local}',
                'body_html': mensaje1,#'<p>Estimado la siguiente oportunidad fue aprobada.</p>',
                'email_to': obj_correo.correo,
                'attachment_ids': [],#(6, 0, [attachment.id])],
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

        if self.visita_tecnica:
            obj_correo = obj_correo.search([('tipo','=','Visita'),('estado','=','Activo')])
            #if self.contactos_ids:
            mensaje = obj_correo.description
            mensaje1 = ("""
            %s
            </br>           
            <div class="pos-customer_facing_display">
                <p>Nombre del Proyecto: %s</p>
                </br>
                <p>Fecha de Entrega de Oferta: %s</p>
                </br>
                <p>Contacto: %s</p></br>
                <p>Descripcion del Proyecto: %s</p></br>       
            </div> 
            
            """)%(mensaje, self.name, self.fecha_entrega,self.contacto_principal,self.description)
            mail_values = {
                'subject': f'Visita Tecnica {current_datetime_local}',
                'body_html': mensaje1,#'<p>Estimado la siguiente oportunidad fue aprobada.</p>',
                'email_to': obj_correo.correo,
                'attachment_ids': [],#(6, 0, [attachment.id])],
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Correo Enviado',
                'message': 'El correo fue enviado correctamente a los destinatarios!!.',
                'type': 'success',
                'sticky': False,
            }
        }
        return True
    
    fecha_inicio = fields.Date('Fecha de Inicio', default=fields.Date.context_today)
    compania_cliente = fields.Char('Compañía Cliente')
    contacto_principal = fields.Char('Contacto Principal', required=True )
    solicitante = fields.Many2one('res.users', string='Solicitante')
    contactos_ids=fields.One2many("crm.lead.contactos","lead_id","Contactos")
    lead_project_id=fields.Many2one("crm.lead.project","Proyecto de Venta")
    lead_project_sequence=fields.Char("# Secuencial", default=1)
    prioridad = fields.Selection([
        ('0', 'Baja'),
        ('1', 'Media'),
        ('2', 'Alta'),
    ], string='Prioridad', default='1') 
    tipo_industria = fields.Selection([
        ('1' ,'AQUICOLA'),
        ('2' ,'INDUSTRIAL')
    ], string='Tipo Industria', default='1')
    tipo_proyecto = fields.Selection([
        ('1' ,'CONSULTORIA'),
        ('2' ,'CALIFICACION DE GENERACION'),
        ('3' ,'ACUICOLA'),
        ('4','POSTVENTA'),
        ('5' ,'SOLAR'),
        ('6' ,'DIESEL'),
        ('7' ,'GAS'),
        ('8' ,'OTROS')
        ], string='Tipo Proyecto', required=True, default='1' )
    fecha_entrega = fields.Date('Fecha de Entrega de Oferta')
    codigo_presupuesto = fields.Char('Código de Presupuesto', unique = True)
    novedades_varias = fields.Char('Novedades Varias')
    licitacion = fields.Boolean('Licitación')
    requiere_visita_tecnica = fields.Boolean('Requiere Visita Técnica') 
    tdr = fields.Boolean('TDR')
    financiamiento = fields.Boolean('Financiamiento')
    contacto_financiamiento = fields.Char('Contacto Financiamiento')
    correo_contacto_financiamiento = fields.Char('Correo Financiamiento')
    visita_tecnica = fields.Boolean('Visita Técnica')
    sequence = fields.Integer('Prioridad', default=1)
    bitacora_ids = fields.One2many("crm.lead.bitacora", "lead_id", "Bitacora")
    tipo_lead = fields.Selection([
        ('1', 'Contratación Directa'),
        ('2', 'Concurso/Licitación'),
        ('3', 'Venta de Energía (PPA)'),
    ], string='Tipo de Oportunidad', required=True, default='1')
    anio_modificacion = fields.Integer('Año de modificación', compute='_compute_anio_modificacion', store=True)
    create_year = fields.Integer('Año de Creación', compute='_compute_create_year', store=True)
    current_year = fields.Integer(string="Año Actual", compute='_compute_current_year', store=False)

    _sql_constraints = models.Model._sql_constraints + [
        ('presupuesto_uniq', 'UNIQUE(codigo_presupuesto)', 'El codigo de Presupuesto debe de ser único!'),
        ('check_probability', 'check(probability >= 0 and probability <= 100)','The probability of closing the deal should be between 0% and 100%!')
    ]
    def onchange_lead_project_id(self):
        if self.lead_project_id:
            self.lead_project_sequence="%s%s" % (self.lead_project_id.code,self.lead_project_id.sequence_id.next_by_id())
    
    def action_sale_quotations_new(self):
        for brw_each in self:
            if not brw_each.lead_project_id:
                raise ValidationError(_("Debes definir un Proyecto de Venta"))
            if not brw_each.lead_project_sequence:
                brw_each.onchange_lead_project_id()
        return super(CrmLead,self).action_sale_quotations_new()
    
    def _prepare_opportunity_quotation_context(self):
        self.ensure_one()
        values=super(CrmLead,self)._prepare_opportunity_quotation_context()
        values["default_lead_project_id"]=self.lead_project_id and self.lead_project_id.id or False
        values["default_lead_project_sequence"]=self.lead_project_sequence
        return values

    @api.depends('write_date')
    def _compute_anio_modificacion(self):
        for record in self:
            if record.write_date:
                record.anio_modificacion = record.write_date.year
            else:
                record.anio_modificacion = False

    @api.depends('create_date')
    def _compute_create_year(self):
        for record in self:
            if record.create_date:
                record.create_year = record.create_date.year
            else:
                record.create_year = False

    def _compute_current_year(self):
        for record in self:
            record.current_year = date.today().year


class CrmLeadContactos(models.Model):
    _name = "crm.lead.contactos"
    _description = "Contactos del Proyecto de Venta"

    name = fields.Char("Nombre", required=True)
    email = fields.Char("Correo Electrónico")
    phone = fields.Char("Teléfono")
    cargo = fields.Char("Cargo")
    lead_id = fields.Many2one("crm.lead", "Proyecto de Venta")


class CrmLeadBitacora(models.Model):
    _name = "crm.lead.bitacora"
    _description = "Bitacora del Proyecto de Venta"

    fecha_hora_bitacora = fields.Datetime('Fecha/Hora',readonly=True, default=lambda self: fields.Datetime.now())
    contacto = fields.Char("contacto")
    detalles = fields.Char("detalles")
    lead_id = fields.Many2one("crm.lead", "Proyecto de Venta")

