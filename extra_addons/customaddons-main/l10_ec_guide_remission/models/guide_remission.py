from odoo import fields, models, _,api
from odoo.exceptions import UserError,ValidationError
from odoo.tools.xml_utils import cleanup_xml_node, validate_xml_from_attachment
from lxml import etree
from functools import partial
from datetime import datetime
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import float_repr, float_round, html_escape
from odoo.tools.xml_utils import cleanup_xml_node, validate_xml_from_attachment
from pytz import timezone
from requests.exceptions import ConnectionError as RConnectionError
from zeep import Client
from zeep.exceptions import Error as ZeepError
from zeep.transports import Transport
from markupsafe import Markup
import base64
L10N_EC_XSD_URLS = {
    'guia': ('GuiaRemision_V1.1.0.xsd', r"https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/642ba34d-82d0-49d8-9622-5946f8eda268/XML%20y%20XSD%20Gu%c3%ada%20de%20Remisi%c3%b3n.zip"),
}

TEST_URL = {
    'reception': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
    'authorization': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
}

PRODUCTION_URL = {
    'reception': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
    'authorization': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
}

DEFAULT_TIMEOUT_WS = 20

class std_reason_document(models.Model):
    _name = "std.reason.document"

    name = fields.Char(string='Name', index=True)

class L10nLatamDocumentType(models.Model):
    _inherit = "l10n_latam.document.type"

    internal_type = fields.Selection(
        selection_add=[
            ("remission", "Guia de Remisión"),
        ]
    )

class GuideRemission(models.Model):
    _name = 'l10n_ec.guide.remission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc"
    _description = 'Guide Remission for Ecuador'

    @api.model
    def get_retention_number(self):
        """
        Obtiene el número de retención (#).
        """
        return self.name or 'Sin Número'

    def get_withhold_agent_number(self):
        """
        Obtiene el número de agente de retención.
        """
        return self.company_id.l10n_ec_withhold_agent_number or "No definido"

    def get_special_taxpayer_number(self):
        """
        Obtiene el número de contribuyente especial.
        """
        return self.company_id.l10n_ec_special_taxpayer_number or "No definido"

    def get_forced_accounting_status(self):
        """
        Verifica si la compañía está obligada a llevar libros de contabilidad.
        """
        return "Sí" if self.company_id.l10n_ec_forced_accounting else "No"

    def get_production_environment(self):
        """
        Determina el ambiente de operación (PRUEBA o PRODUCCIÓN).
        """
        return "PRODUCCIÓN" if self.company_id.l10n_ec_production_env else "PRUEBA"

    def get_driver_name(self):
        """
        Obtiene el nombre del conductor.
        """
        return self.partner_carrier_id.name or "No definido"

    def get_driver_identification(self):
        """
        Obtiene la identificación del conductor.
        """
        return self.partner_carrier_id.vat or "No definido"

    def get_vehicle_plate(self):
        """
        Obtiene la placa del vehículo asociado al conductor.
        """
        return self.vehicle_id.license_plate or "No definido"

    def get_company_name(self):
        """
        Obtiene el nombre de la compañía.
        """
        return self.company_id.partner_id.name or "No definido"

    def get_company_identification(self):
        """
        Obtiene la identificación de la compañía.
        """
        return self.company_id.partner_id.vat or "No definido"

    def get_emission_date(self):
        """Obtiene la fecha de emisión de la guía de remisión."""
        return self.l10n_ec_authorization_date or 'No definida'

    def get_company_street(self):
        """Obtiene la calle principal de la empresa."""
        if self.company_id and self.company_id.partner_id:
            return self.company_id.partner_id.street or "No definida"
        return "No definida"

    def get_authorization_number(self):
        """Obtiene el número de autorización del SRI."""
        return self.l10n_ec_authorization_number or 'No autorizado'

    def get_associated_invoice(self):
        """Obtiene el nombre de la factura asociada."""
        if self.invoice_id:
            return self.invoice_id.name or "Sin nombre de factura"
        return "No hay factura asociada"

    def get_recipient_identification(self):
        """Obtiene la identificación del destinatario (Para)."""
        if self.partner_id:
            return self.partner_id.vat or "Identificación no definida"
        return "No definida"

    def get_recipient_name(self):
        """Obtiene el nombre del destinatario (Para)."""
        if self.partner_id:
            return self.partner_id.name or "Nombre no definido"
        return "No definido"

    @api.model
    def ger_default_partner_id(self):
        brw_partner=self.env["res.users"].sudo().browse(self._uid).company_id.partner_id
        return brw_partner.id 
    
    
    def _get_journal_doc_id_domain(self):
        return self.__get_journal_doc_id_domain(self.journal_id and self.journal_id.id or 0)
    
    def __get_journal_doc_id_domain(self,journal_id):
        return [('journal_id.type','=','sale'),('journal_id.l10n_latam_use_documents','=',True),('journal_id','=',journal_id),('document_id.internal_type','=','guia')]

    @api.model
    def _get_default_company_id(self):
        brw_user=self.env["res.users"].sudo().browse(self._uid)
        return brw_user.company_id and brw_user.company_id.id or False

    name = fields.Char(string='#', index=True,
                       readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always')
    sequence=fields.Integer("Secuencia",default=1)
    number = fields.Char(string='Número', index=True,
                         readonly=True, states={'draft': [('readonly', False)]})
    number_temporal = fields.Char(string='Número Temporal',
                                  readonly=True, states={'draft': [('readonly', False)]}, default='/')
    reference = fields.Char(string='Referencia', index=True,
                            readonly=True, states={'draft': [('readonly', False)]})
    address_origin = fields.Char(string='Origen', index=True,
                                 readonly=True, states={'draft': [('readonly', False)]})
    address_destination = fields.Char(string='Destino', index=True,
                                      readonly=True, states={'draft': [('readonly', False)]})
    comment = fields.Char(string='Comentario', index=True,
                          readonly=True, states={'draft': [('readonly', False)]})
    access_key = fields.Char(string='Clave de Acceso',
                             readonly=True, states={'draft': [('readonly', False)]})   
    authorization = fields.Char(string='Autorización',
                                readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Preliminar'), ('done', 'Realizado'), ('cancel', 'Anulado')], string='Estado', readonly=True, index=True, change_default='draft',
                             default=lambda self: self._context.get('state', 'draft'), track_visibility='always')
    type = fields.Selection([('sale_referral_guide', 'Venta')], string='Tipo', readonly=False, index=True, change_default='sale_referral_guide',
                            default=lambda self: self._context.get('type', 'sale_referral_guide'), track_visibility='always')#, ('purchase_referral_guide', 'Compra')
    date = fields.Date(string='Fecha', readonly=True, states={'draft': [('readonly', False)]}, index=True, help="", copy=False,
                       default=lambda self: self._context.get('date', fields.Date.context_today(self)), track_visibility='always')
    date_initial = fields.Date(string='Fecha Inicial', readonly=True, states={'draft': [('readonly', False)]}, index=True, help="", copy=False,
                               default=lambda self: self._context.get('date', fields.Date.context_today(self)), track_visibility='always')
    date_end = fields.Date(string='Fecha Final', readonly=True, states={'draft': [('readonly', False)]}, index=True, help="", copy=False,
                           default=lambda self: self._context.get('date', fields.Date.context_today(self)), track_visibility='always')
    company_id = fields.Many2one('res.company', string='Empresa', change_default=True,
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=lambda self: self.env['res.company']._company_default_get('l10n_ec.guide.remission'))
    partner_id = fields.Many2one('res.partner', string='Para',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]}, track_visibility='always',
                                 default=ger_default_partner_id
                                 )
    partner_carrier_id = fields.Many2one('res.partner', string='Conductor',
                                         required=False, readonly=True, states={'draft': [('readonly', False)]},
                                         domain=[('country_id.code','!=',None)]
                                         )
    # type_document_id = fields.Many2one('std.type.document', string='Model Document',
    #                                    readonly=True, states={'draft': [('readonly', False)]}, default=_default_document_type)
    reason_document_id = fields.Many2one('std.reason.document', string='Mótivo',
                                         readonly=True, states={'draft': [('readonly', False)]})#,default=get_default_reason_document_id)
    # vehicle_id = fields.Many2one('std.vehicle.information', string='Vehicle',
    #                              readonly=True, states={'draft': [('readonly', False)]})
    invoice_id = fields.Many2one('account.move', string='Factura',
                                 readonly=True, states={'draft': [('readonly', False)]})
    line_guide_ids = fields.One2many('l10n_ec.guide.remission.line', 'guide_id', string='Detalles',
                                         readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    electronic = fields.Boolean(string='Electronico', readonly=True, states={'draft': [('readonly', False)]})
    electronic_details = fields.Text(string='Comentarioss', readonly=True)
    electronic_migrate = fields.Boolean(string='Migrar documento electrónico', readonly=True,
                                        states={'done': [('readonly', False)]}, default=False, copy=False)
    invoice_reference = fields.Boolean(string='Referencia de Factura.', default=False)
    environment = fields.Selection([('1', 'Test'), ('2', 'Producción')], string='environment', required=True, readonly=False, default='1')
    sent = fields.Boolean(string='Enviado', readonly=True, default=False, copy=False, help=u"Envio de correo", track_visibility='always')
    user_id = fields.Many2one('res.users', string=u'Responsable', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env.user)
    # key_history_ids = fields.One2many('std.history.key.document', 'referral_guide_id', string='Keys', readonly=True, copy=False)
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string="Vehiculo",
        tracking=True,
        required=False, help=u"Registro de vehiculo")
    journal_id = fields.Many2one("account.journal", "Diario",required=True)#,domain=_get_journal_id_domain,default=get_default_journal_id)
    #journal_doc_id = fields.Many2one("account.journal.document", "Secuencia Inicial para Diario",required=True,domain=_get_journal_doc_id_domain)
    # ===== EDI fields =====
    l10n_ec_authorization_number = fields.Char(
        string="Authorization number",
        size=49,
        copy=False, index=True, readonly=True,
        tracking=True,
        help="EDI authorization number (same as access key), set upon posting",
    )
    l10n_ec_authorization_date = fields.Datetime(
        string="Authorization date",
        copy=False, readonly=True, tracking=True,
        help="Set once the government authorizes the document, unset if document is cancelled.",
    )
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Tipo de Documento', ondelete='cascade', required=True)
    l10n_latam_internal_type = fields.Selection(related='l10n_latam_document_type_id.internal_type',store=False,readonly=True)
    edi_state = fields.Selection(
        selection=[('to_send', 'Por Enviar'), ('sent', 'Enviado'), ('to_cancel', 'Por Cancelar'), ('cancelled', 'Cancelado')],
        string="Electronic invoicing")
    documento_requisicion = fields.Many2one('purchase.request','Requisicion')
    cuenta_analitica_id = fields.Many2one('account.analytic.account','Cuenta Analitica')
    
    def compute_to_send_state(self):
        for brw_each in self:
            to_send_state=False
            if(brw_each.state=="done"):
                to_send_state=True
                if(brw_each.l10n_ec_authorization_date and not brw_each.l10n_ec_authorization_date is None):
                    to_send_state=False
            brw_each.to_send_state=to_send_state
        
    to_send_state=fields.Boolean("Por enviar",compute="compute_to_send_state",default=False)
    transporte_externo = fields.Boolean('Transp. Externo?')
    razon_social_transportista = fields.Char('Razon Social Transportista')
    tipo_identificacion_transportista = fields.Selection([('04', 'RUC'), ('05', 'CEDULA'), ('06', 'PASAPORTE'), ('07', 'CONSUMIDOR FINAL'), ('08', 'EXTRANJERO')],
        string="Tipo Id Transportista", default='04')
    ruc_transportista = fields.Char('Ruc Transportista', size=13)
    placa_externo = fields.Char('Placa', size=13)

    @api.constrains('ruc_transportista', 'tipo_identificacion_transportista','transporte_externo')
    def _check_ruc_transportista(self):
        for record in self:
            ruc = record.ruc_transportista
            tipo_id = record.tipo_identificacion_transportista

            if record.transporte_externo:
                if not ruc:
                    raise ValidationError("El RUC del transportista es obligatorio para transporte externo.")

                if tipo_id in ['04', '05']:  # RUC o CÉDULA
                    if not ruc.isdigit():
                        raise ValidationError("El RUC del transportista debe contener solo números para RUC o Cédula.")
                    if len(ruc) != 13:
                        raise ValidationError("La Identificacion del transportista debe tener 13 dígitos cuando es Cédula o RUC.")
                elif tipo_id == '06':  # PASAPORTE
                    if len(ruc) > 20:
                        raise ValidationError("El número de pasaporte no puede tener más de 20 caracteres.")
    
    @api.model
    def format_number(self,num):
        num="000000000%s" % (num,)
        return num[-8:]
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.invoice_id=False
        
    @api.onchange('journal_id')
    def onchange_journal_id(self):
    #     journal_doc_srch=self.env["account.journal.document"].search(self.__get_journal_doc_id_domain(self.journal_id and self.journal_id.id or 0))
    #     self.journal_doc_id=False
    #     self.l10n_latam_document_type_id=False
    #     if journal_doc_srch:
    #         self.journal_doc_id=journal_doc_srch[0].id
    #         self.l10n_latam_document_type_id=journal_doc_srch[0].document_id.id
    #     if not self.journal_id:
    #         self.sequence=0 
    #         self.number="000000000"
    #         self.number_temporal="000000000"
    #         self.reference="000-000-000000000"
    #     else:
        self.sequence=self.get_number(self.journal_id.id)
        self.number=self.format_number(self.sequence)
        self.number_temporal=self.number
        self.reference="%s-%s-%s" % (self.journal_id.l10n_ec_entity,self.journal_id.l10n_ec_emission,self.number_temporal)
        self.name=self.reference
    
    @api.onchange('invoice_id')
    def onchange_invoice_id(self):
        line_guide_ids=[(5,)]
        if self.invoice_id:
            for brw_line in self.invoice_id.invoice_line_ids:
                if brw_line.product_id.detailed_type!="service":
                    line_guide_ids.append((0,0,{
                        "product_id":brw_line.product_id.id,
                         "name":brw_line.product_id.name,
                           "code":brw_line.product_id.default_code,
                           "qty":brw_line.quantity,
                           "details":brw_line.product_id.name
                        }))                
        self.line_guide_ids=line_guide_ids
    
    @api.onchange('address_origin','address_destination')
    def onchange_address(self):
        self.address_origin=self.address_origin and self.address_origin.upper() or None
        self.address_destination=self.address_destination and self.address_destination.upper() or None
    
      
    def action_confirm(self):
        if not self.line_guide_ids:
            raise ValidationError(_("Debes definir al menos una linea"))
        for brw_line in self.line_guide_ids:
            if(brw_line.qty<=0):
                raise ValidationError(_("Las cantidades deben ser mayor a 0"))
        self.write({'state': 'done'})
        self.send_sri()
        
    def action_draft(self):
        # if(self.state=="done"):
        #     # if(self.edi_state=="autorized"):
        #     #     raise ValidationError(_("No puedes reversar un documento ya autorizado"))
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})
        
    def get_number(self,journal_id):
        number=1
        if journal_id:
            self._cr.execute("""select journal_id,coalesce(max(sequence),0)+1 from l10n_ec_guide_remission where journal_id=%s group by journal_id """,(journal_id,))
            result=self._cr.fetchone()
            number=result and result[-1] or 1
        return number
    
    def write(self,vals):     
        value= super(GuideRemission,self).write(vals)
        for brw_each in self:
            if(brw_each.state!='done'):
                new_vals=self.update_values({},brw_each.id,brw_each.journal_id.id,brw_each.sequence)
                brw_each._write(new_vals)
        return value
    
    @api.model
    def create(self, vals):
        vals=self.update_values(vals,0,vals["journal_id"],vals["sequence"])
        brw_new= super(GuideRemission,self).create(vals)
        return brw_new
    
    @api.model
    def update_values(self,vals,id,journal_id,sequence):
        if journal_id and sequence:
            brw_journal=self.env["account.journal"].sudo().browse(journal_id )
            domain=[('journal_id','=',journal_id),('sequence','=',sequence)]
            srch=self.search(domain)
            if (srch and (id!=srch[0].id)) or (id<=0):
                vals["sequence"]=self.get_number(journal_id)
                vals["number"]=self.format_number(sequence)
                vals["number_temporal"]=vals["number"]
                vals["reference"]="%s-%s-%s" % (brw_journal.l10n_ec_entity,brw_journal.l10n_ec_emission,vals["number_temporal"])
                vals["name"]=vals["reference"]
        return vals
    
    _sql_constraints = [
        ('journal_number_uniq', 'unique (journal_id,sequence)', 'El codigo debe ser unico por diario')
    ]
    
    error = fields.Html(help='The text of the last error that happened during Electronic Invoice operation.')
    blocking_level = fields.Selection(
        selection=[('info', 'Info'), ('warning', 'Warning'), ('error', 'Error')],
        help="Blocks the current operation of the document depending on the error severity:\n"
        "  * Info: the document is not blocked and everything is working as it should.\n"
        "  * Warning: there is an error that doesn't prevent the current Electronic Invoicing operation to succeed.\n"
        "  * Error: there is an error that blocks the current Electronic Invoicing operation.")
    
    def get_infoadicional(self):
        values=[]
        return values
    
    def  send_sri(self):
        for brw_each in self:
            if brw_each.vehicle_id:
                if not brw_each.vehicle_id.license_plate:
                    raise ValidationError(_("debes definir una placa para el vehiculo"))
            res={}
            brw_each._l10n_ec_set_authorization_number()
            xml_signed, errors=self._l10n_ec_generate_xml(brw_each)
            print(xml_signed)
            # Error management
            
            if errors:
                blocking_level = 'error'
                attachment = None
            else:
                errors, blocking_level, attachment = self._l10n_ec_send_xml_to_authorize(brw_each, xml_signed)

            res.update({
                brw_each: {
                    'success': not errors,
                    'error': '<br/>'.join([html_escape(e) for e in errors]),
                    'attachment': attachment,
                    'blocking_level': blocking_level,
                }}
            )
            brw_each.write({"edi_state": not errors and "sent" or "to_send"})
                       
            
    def _l10n_ec_set_authorization_number(self):
        OBJ_PARAMETER=self.env["ir.config_parameter"].sudo()
        self.ensure_one()
        company = self.company_id
        # NOTE: withholds don't have l10n_latam_document_type_id (WTH journals use separate sequence)
        document_code_sri = "06"
        environment = company.l10n_ec_production_env and '2' or '1'
        serie = self.journal_id.l10n_ec_entity + self.journal_id.l10n_ec_emission
        sequential = self.name.split('-')[2].rjust(9, '0')
        num_filler = OBJ_PARAMETER.get_param('code.num.filler', default='98765432')  
        emission = '1'  # corresponds to "normal" emission, "contingencia" no longer supported

        if not (document_code_sri and company.partner_id.vat and environment
                and serie and sequential and num_filler and emission):
            return ''

        now_date = self.date.strftime('%d%m%Y')
        key_value = now_date + document_code_sri + company.partner_id.vat + environment + serie + sequential + num_filler + emission
        self.l10n_ec_authorization_number = key_value + str(self._l10n_ec_get_check_digit(key_value))

    @api.model
    def _l10n_ec_get_check_digit(self, key):
        sum_total = sum([int(key[-i - 1]) * (i % 6 + 2) for i in range(len(key))])
        sum_check = 11 - (sum_total % 11)
        if sum_check >= 10:
            sum_check = 11 - sum_check
        return sum_check
    
    def xmlGen(self, str_field):
        try:
            str_field = str_field.lower()
        except:
            str_field = str_field
        if isinstance(str_field, str):
            str_field = str_field.replace("&", "&amp;")
            str_field = str_field.replace("&", "&amp;")
            str_field = str_field.replace("<", "&lt;")
            str_field = str_field.replace(">", "&gt;")
            str_field = str_field.replace("\"", "&quot;")
            str_field = str_field.replace("'", "&apos;")
            str_field = str_field.replace("á", "a")
            str_field = str_field.replace("é", "e")
            str_field = str_field.replace("í", "i")
            str_field = str_field.replace("ó", "o")
            str_field = str_field.replace("ú", "u")
            str_field = str_field.replace("ñ", "n")
            str_field = str_field.replace('\n', '')
            str_field = str_field.replace('\r', '')

        return str_field 
    
    @api.model
    def _l10n_ec_get_xml_common_values(self,move):
        internal_type = move.l10n_latam_document_type_id.internal_type
        return {
            'move': move,
            'sequential': move.name.split('-')[2].rjust(9, '0'),
            'company': move.company_id,
            'journal': move.journal_id,
            'partner': move.partner_id,
            #'partner_sri_code': move.partner_id._get_sri_code_for_partner().value,
            'partner_sri_code': move.partner_carrier_id._get_sri_code_for_partner().value if not self.transporte_externo else '04',
            'clean_str': self._l10n_ec_remove_newlines,
            'strftime': partial(datetime.strftime, format='%d/%m/%Y'),
            "line_guide_ids":move.line_guide_ids,
        }
    
    def _l10n_ec_get_invoice_edi_data(self):
        return {}
    
    @api.model
    def _l10n_ec_generate_xml(self, move):
        # Gather XML values
        template = 'l10_ec_guide_remission.guia_template'
        doc_type = 'guia'
        move_info = self._l10n_ec_get_xml_common_values(move)        
        move_info.update(move._l10n_ec_get_invoice_edi_data())

        # Generate XML document
        xml_content = self.env['ir.qweb']._render(template, move_info)
        xml_content = cleanup_xml_node(xml_content)
        errors = self._l10n_ec_validate_with_xsd(xml_content, doc_type)
        
        # Sign the document
        if move.company_id._l10n_ec_is_demo_environment():  # unless we're in a test environment without certificate
            xml_signed = etree.tostring(xml_content, encoding='unicode')
        else:
            xml_signed = move.company_id.sudo().l10n_ec_edi_certificate_id._action_sign(xml_content)

        xml_signed = '<?xml version="1.0" encoding="utf-8" standalone="no"?>' + xml_signed
        return xml_signed, errors
    
    def _l10n_ec_remove_newlines(self, s, max_len=300):
        if not s:
            return ""
        return s.replace('\n', '')[:max_len]
    
    def _l10n_ec_validate_with_xsd(self, xml_doc, doc_type):
        try:
            xsd = L10N_EC_XSD_URLS[doc_type][0]
            validate_xml_from_attachment(self.env, xml_doc, xsd, prefix='pas_electronic_documents')
            return []
        except UserError as e:
            return [str(e)]
        
    def _l10n_ec_generate_demo_xml_attachment(self, move, xml_string):
        """
        Generates an xml attachment to simulate a response from the SRI without the need for a digital signature.
        """
        move.l10n_ec_authorization_date = datetime.now(tz=timezone('America/Guayaquil')).date()
        attachment = self.env['ir.attachment'].create({
            'name': move.display_name + '_demo.xml',
            'res_id': move.id,
            'res_model': move._name,
            'type': 'binary',
            'raw': self._l10n_ec_create_authorization_file(
                move, xml_string,
                move.l10n_ec_authorization_number, move.l10n_ec_authorization_date),
            'mimetype': 'application/xml',
            'description': f"Ecuadorian electronic document generated for document {move.display_name}."
        })
        move.with_context(no_new_invoice=True).message_post(
            body=_(
                "<strong>This is a DEMO response, which means this document was not sent to the SRI.</strong><br/>If you want your document to be processed by the SRI, please set an <strong>Electronic Certificate File</strong> in the settings.<br/><br/>Demo electronic document.<br/><strong>Authorization num:</strong><br/>%s<br/><strong>Authorization date:</strong><br/>%s",
                move.l10n_ec_authorization_number, move.l10n_ec_authorization_date
            ),
            attachment_ids=attachment.ids,
        )
        return [], "", attachment

    def _l10n_ec_send_xml_to_authorize(self, move, xml_string):
        # === DEMO ENVIRONMENT REPONSE ===
        if move.company_id._l10n_ec_is_demo_environment():
            return self._l10n_ec_generate_demo_xml_attachment(move, xml_string)

        # === STEP 1 ===
        errors, warnings = [], []
        if not move.l10n_ec_authorization_date:
            # Submit the generated XML
            response, zeep_errors, warnings = self._l10n_ec_get_client_service_response(move, 'reception', xml=xml_string.encode())
            if zeep_errors:
                return zeep_errors, 'error', None
            try:
                response_state = response.estado
                response_checks = response.comprobantes and response.comprobantes.comprobante or []
            except AttributeError as err:
                return warnings or [_("SRI response unexpected: %s", err)], 'warning' if warnings else 'error', None

            # Parse govt's response for errors or response state
            if response_state == 'DEVUELTA':
                for check in response_checks:
                    for msg in check.mensajes.mensaje:
                        if msg.identificador != '43':  # 43 means Authorization number already registered
                            errors.append(' - '.join(
                                filter(None, [msg.identificador, msg.informacionAdicional, msg.mensaje, msg.tipo])
                            ))
            elif response_state != 'RECIBIDA':
                errors.append(_("SRI response state: %s", response_state))

            # If any errors have been found (other than those indicating already-authorized document)
            if errors:
                return errors, 'error', None

        # === STEP 2 ===
        # Get authorization status, store response & raise any errors
        attachment = False
        auth_num, auth_date, auth_errors, auth_warnings = self._l10n_ec_get_authorization_status(move)
        errors.extend(auth_errors)
        warnings.extend(auth_warnings)
        if auth_num and auth_date:
            if move.l10n_ec_authorization_number != auth_num:
                warnings.append(_("Authorization number %s does not match document's %s", auth_num, move.l10n_ec_authorization_number))
            move.l10n_ec_authorization_date = auth_date.replace(tzinfo=None)
            attachment = self.env['ir.attachment'].create({
                'name': ("Guia "+ move.display_name) + '.xml',
                'res_id': move.id,
                'res_model': move._name,
                'type': 'binary',
                'raw': self._l10n_ec_create_authorization_file(move, xml_string, auth_num, auth_date),
                'mimetype': 'application/xml',
                'description': f"Ecuadorian electronic document generated for document {move.display_name}."
            })
            move.with_context(no_new_invoice=True).message_post(
                body=_(
                    "Electronic document authorized.<br/><strong>Authorization num:</strong><br/>%s<br/><strong>Authorization date:</strong><br/>%s",
                    move.l10n_ec_authorization_number, move.l10n_ec_authorization_date
                ),
                attachment_ids=attachment.ids,
            )
        elif not auth_num or (move.edi_state == 'to_cancel' and not move.company_id.l10n_ec_production_env):
            # No authorization number means the invoice was cancelled
            # In test environment, we act as if invoice had already been cancelled for the govt
            warnings.append(_("Document with access key %s has been cancelled", move.l10n_ec_authorization_number))
        else:
            warnings.append(_("Document with access key %s received by government and pending authorization",
                              move.l10n_ec_authorization_number))

        return errors or warnings, 'error' if errors else 'warning', attachment

    def _l10n_ec_get_authorization_status(self, move):
        """
        Government interaction: retrieves status of previously sent document.
        """
        auth_num, auth_date = None, None

        response, zeep_errors, zeep_warnings = self._l10n_ec_get_client_service_response(
            move, "authorization",
            claveAccesoComprobante=move.l10n_ec_authorization_number
        )
        if zeep_errors:
            return auth_num, auth_date, zeep_errors, zeep_warnings
        try:
            response_auth_list = response.autorizaciones and response.autorizaciones.autorizacion or []
        except AttributeError as err:
            return auth_num, auth_date, [_("SRI response unexpected: %s", err)], zeep_warnings

        errors = []
        if not response_auth_list:
            errors.append(_("Document not authorized by SRI, please try again later"))
        elif not isinstance(response_auth_list, list):
            response_auth_list = [response_auth_list]

        for doc in response_auth_list:
            if doc.estado == "AUTORIZADO":
                auth_num = doc.numeroAutorizacion
                auth_date = doc.fechaAutorizacion
            else:
                messages = doc.mensajes
                if messages:
                    messages_list = messages.mensaje
                    if not isinstance(messages_list, list):
                        messages_list = messages
                    for msg in messages_list:
                        errors.append(' - '.join(
                            filter(None, [msg.identificador, msg.informacionAdicional, msg.mensaje, msg.tipo])
                        ))
        return auth_num, auth_date, errors, zeep_warnings

    def _l10n_ec_get_client_service_response(self, move, mode, **kwargs):
        """
        Government interaction: SOAP Transport and Client management.
        """
        if move.company_id.l10n_ec_production_env:
            wsdl_url = PRODUCTION_URL.get(mode)
        else:
            wsdl_url = TEST_URL.get(mode)

        errors, warnings = [], []
        response = None
        try:
            transport = Transport(timeout=DEFAULT_TIMEOUT_WS)
            client = Client(wsdl=wsdl_url, transport=transport)
            if mode == "reception":
                response = client.service.validarComprobante(**kwargs)
            elif mode == "authorization":
                response = client.service.autorizacionComprobante(**kwargs)
            if not response:
                errors.append(_("No response received."))
        except ZeepError as e:
            errors.append(_("The SRI service failed with the following error: %s", e))
        except RConnectionError as e:
            warnings.append(_("The SRI service failed with the following message: %s", e))
        return response, errors, warnings

    # ===== Helper methods =====

    def _l10n_ec_create_authorization_file(self, move, xml_string, authorization_number, authorization_date):
        xml_values = {
            'xml_file_content': Markup(xml_string[xml_string.find('?>') + 2:]),  # remove header to embed sent xml
            'mode': 'PRODUCCION' if move.company_id.l10n_ec_production_env else 'PRUEBAS',
            'authorization_number': authorization_number,
            'authorization_date': authorization_date.strftime(DTF),
        }
        xml_response = self.env['ir.qweb']._render('l10_ec_guide_remission.authorization_template', xml_values)
        xml_response = cleanup_xml_node(xml_response)
        return etree.tostring(xml_response, encoding='unicode')
    
    _order="id desc"
    
    def unlink(self):
        for brw_each in self:
            if(brw_each.state!="draft"):
                raise ValidationError(_("Documento no puede ser eliminado en este estado"))
        return super().unlink()

    @api.constrains('reason_document_id', 'invoice_id')
    def _check_invoice_required(self):
        """ Hace obligatorio invoice_id cuando reason_document_id es 'VENTA' """
        for record in self:
            if record.reason_document_id == 'VENTA' and not record.invoice_id:
                raise models.ValidationError("El campo 'Factura' es obligatorio cuando el motivo es 'VENTA'.")


class GuideRemissionLine(models.Model):
    _name = 'l10n_ec.guide.remission.line'
    _description = 'Guide Remission Line'

    guide_id = fields.Many2one('l10n_ec.guide.remission', string=u'Guide')
    product_id = fields.Many2one('product.product', string=u'Productos')#,domain="[('detailed_type,'!=','service')]")
    name = fields.Char(string=u'Descripción', required=True)
    code = fields.Char(string=u'Codigo', required=True)
    details = fields.Char(string='Notas', required=False)
    qty = fields.Float(string='Cantidad', required=True,default=1)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            self.code = self.product_id.default_code or ''