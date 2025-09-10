# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _,SUPERUSER_ID
from lxml import etree
import html   
from odoo.tools.safe_eval import safe_eval
import tempfile
import base64
from datetime import datetime,date
from dateutil.relativedelta import relativedelta

try:
    from suds.client import Client
    from suds.plugin import MessagePlugin
except ImportError:
    raise ValidationError(_('Need Install suds-jurko'))

import logging
_logger = logging.getLogger(__name__)

TEST_URL = {
    'reception': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
    'authorization': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
}

PRODUCTION_URL = {
    'reception': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
    'authorization': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
}

from ...calendar_days.tools import DateManager
from ...message_dialog.tools import FileManager
dtObj=DateManager()
fileO=FileManager()



NO_JOBS=0
ERROR=1
COMMIT=2
NO_HANDLED=3


IDENTIFICATION_DESCR={
    "04":"RUC",
    "05":"CEDULA",
    "06":"PASAPORTE",
    "07":"CONSUMIDOR FINAL",
    "08":"IDENTIFICACION DEL EXTERIOR"
}


class LoggingWebServicePlugin(MessagePlugin):

    def __init__(self):
        self.last_sent_message = None
        self.last_received_reply = None

    def sending(self, context):
        if context.envelope:
            self.last_sent_message = context.envelope

    def parsed(self, context):
        if context.reply:
            self.last_received_reply = context.reply

    def last_sent(self):
        return self.last_sent_message

    def last_received(self):
        return self.last_received_reply

logging_plugin = LoggingWebServicePlugin()





class ElectronicDocumentReceived(models.Model):
    _name="electronic.document.received"

    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    _check_company_auto = True

    _description="Documento recibido"

    def format_float(self,value, dec=2):
        if type(value) == str:
            value = float(value)
        FORMAT = "%%.%sf" % (dec,)
        return FORMAT % (value,)

    def limit_str_format(self,value, limit):
        if not value:
            return ""
        if value is None:
            return ""
        if limit > len(value):
            return value
        return value[:limit]

    def _control_datas(self):
        for brw_each in self:
            assigned=NO_HANDLED
            # if(brw_each.document_type_code!="07"):    
            #     if(brw_each.partner_id):            
            #         partner_list_ids=self.__get_partner_list_ids(self._uid)
            #         assigned=(brw_each.partner_id.id in partner_list_ids ) and COMMIT or NO_JOBS
            brw_each.assigned=assigned
            
    def _control_datas_search(self, operator, value):
        # if self._uid in (SUPERUSER_ID,):
        #     return []
        # if value==COMMIT:
        #     partner_list_ids=self.__get_partner_list_ids(self._uid)
        #     return [('partner_id','in',tuple(partner_list_ids))]
        return []
    
    assigned = fields.Integer(compute="_control_datas", search='_control_datas_search',string="Asignado")

    def compute_enable_change_state_sri(self):
        OBJ_PARAM=self.env['ir.config_parameter'].sudo() 
        months=int(OBJ_PARAM.get_param('time.enable.state.sri','1') )
        for brw_each in self:
            today=fields.Date.context_today(self)
            enable_change_state_sri=False
            process_document_id=False
            if brw_each.date:
                YEAR=brw_each.date.year
                MONTH=brw_each.date.month
                date_validated=date(YEAR, MONTH, today.day)
                date_min_validated=date_validated+ relativedelta(months=-months)
                date_min_validated=date(date_min_validated.year,date_min_validated.month,1)
                enable_change_state_sri=(date_validated>=date_min_validated)
            if brw_each.invoice_id:
                process_document_id=brw_each.invoice_id.id
            if brw_each.withhold_id:
                process_document_id=brw_each.withhold_id.id
            #if brw_each.process_order_id:
            #    process_document_id=brw_each.process_order_id.id
            brw_each.enable_change_state_sri=enable_change_state_sri
            brw_each.process_document_id=process_document_id

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    state=fields.Selection([('draft','Preliminar'),('updated','Actualizada'),('error','Error'),('annulled','Anulado')],"Estado",default="draft")
    
    confirmed_state=fields.Selection([('received','Recibido'),
                                      ('rejected','Rechazado'),
                                      ('verified','Verificado'),
                                      ('confirmed','Confirmado')],string="Recepción",required=False,default="received",tracking=True)
    
    name=fields.Char("Nombre de Emisor",size=255,required=False)
    
    identification=fields.Char("# Identificación",size=255,required=False)
    partner_name=fields.Char("Razón Social",size=255,required=False)
    
    date=fields.Date("Fecha de Documento",required=False)
    document=fields.Char("# Documento",required=False)
    document_related=fields.Char("# Documento Relacionado",required=False)
    
    document_date_auth=fields.Char("Fecha de Autorización",required=False)
    environment_type=fields.Selection([('1','Prueba'),
                                       ('2','Producción')],string="Ambiente",required=True,default="1")
    
    amount=fields.Float("Total",required=False,default=0.00)
    access_key=fields.Char("Clave de Acceso",size=55,required=True,tracking=True)
    xml=fields.Text("Documento")
    msg=fields.Text("Mensaje")
    last_msg = fields.Text("Ult. Mensaje",tracking=True)
    
    document_type_id=fields.Many2one("l10n_latam.document.type","Tipo de Documento")
    document_type_code=fields.Char(related="document_type_id.code",store=False,readonly=True)

    partner_id=fields.Many2one("res.partner","Emisor",tracking=True)
    
    variables=fields.Text("Variables",default="{}")
    
    #history_ids=fields.One2many("electronic.document.received.history","parent_id","historial")
    
    invoice_id=fields.Many2one("account.move","Factura/NC")
    withhold_id=fields.Many2one("account.move","Retención Recibida")
    out_withhold_id=fields.Many2one("account.move","Retención Emitida")
    
    invoice_ref=fields.Char("# Factura/NC",related="invoice_id.name",store=False,readonly=True)
    withhold_ref=fields.Char("# Retención",related="withhold_id.name",store=False,readonly=True)
    
    document_message=fields.Text("Descripción de Primer Linea de Doc.")
    
    base_withhold=fields.Float("Base Imponible",digits=(16,2),default=0.00)
    base_withhold_fte=fields.Float("Base Fuente",digits=(16,2),default=0.00)
    base_withhold_iva=fields.Float("Base IVA",digits=(16,2),default=0.00)
    base_withhold_invoice=fields.Float("Base Imp. Fact.",digits=(16,2),default=0.00)
    tax_total=fields.Float("Valor Retenido",digits=(16,2),default=0.00)
    tax_fte=fields.Float("Rte. Fuente",digits=(16,2),default=0.00)
    tax_iva=fields.Float("Rte. IVA",digits=(16,2),default=0.00)
    
    base_tax_invoice=fields.Float("Subtotal sin impuestos",digits=(16,2),default=0.00)
    tax_invoice=fields.Float("IVA",digits=(16,2),default=0.00)    
    state_number_error=fields.Selection([('error','Error'),('related','Relacionado')],string="# Doc. Rel.",default="related")
    base_witthold_error=fields.Float("Dif. Base",digits=(16,2),default=0.00)
    state_base_withhold_error=fields.Selection([('none','Ning.'),('error','Dif.'),('ok','Corr.')],string="Dif.",default="none")    
    taxes_codes=fields.Text("Impuestos")    
    state_sri=fields.Selection([('not_processed','No procesada'),
                                ('authorized','Autorizado'),
                                ('annulled','Anulado'),
                                ('not_found','Eliminada')],string="Estado SRI",default="not_processed",tracking=True)
    
    
    enable_change_state_sri=fields.Boolean(compute="compute_enable_change_state_sri",string="Permitir cambiar estado SRI",default=False)
    
    xml_file=fields.Binary(compute="get_xml_data_file",string="Archivo XML",store=False,readonly=True)
    process_document_id=fields.Integer(compute="compute_enable_change_state_sri",string="Doc. de Proceso")
    
    order_id=fields.Many2one("purchase.order","Orden de  Compra Ref.")
    process_order_id=fields.Many2one("purchase.order","Orden de  Compra")


    invoice_type=fields.Selection([('service','Servicio'), ],default="service",string="Tipo Fact/NC",tracking=True)
    service_id=fields.Many2one("product.product","Servicio por Defecto",tracking=True)
    
    _order="access_key desc"
    
    def update_workflow(self,comments,state,confirmed_state= None,order_id=False):
        self=self.with_context({})
        for brw_each in self:        
            new_confirmed_state=confirmed_state    
            vals={"state":state}
            if confirmed_state is None:
                new_confirmed_state=brw_each.confirmed_state
            # if brw_each.document_type_code=="01":
            #     if order_id:
            #         pass#vals["order_id"]=order_id
            vals["confirmed_state"]=new_confirmed_state
            vals["last_msg"] = comments
            brw_each.write(vals)#actualiza estado     
            #self.env["electronic.document.received.history"].register(brw_each.id,comments,state,confirmed_state=new_confirmed_state)
        return True
    
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        brw_new=super(ElectronicDocumentReceived,self).create(vals)
        #OBJ_HISTORY=self.env["electronic.document.received.history"]
        #OBJ_HISTORY.register(brw_new.id,_("REGISTRO CREADO" ),brw_new.state,confirmed_state=brw_new.confirmed_state)
        return brw_new
    
    @api.returns('self', lambda value:value.id)
    def copy(self, default=None):
        raise ValidationError(_("No puedes duplicar este documento"))
    
    def unlink(self):
        for brw_each in self:
            if brw_each.state!="draft":
                raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        value= super(ElectronicDocumentReceived,self).unlink()
        return value
    
    @api.model
    def __resolve_url(self,brw_each,authorization_url=None):        
        if authorization_url is None:
            # self._cr.execute(""" SELECT ID FROM ELECTRONIC_DOCUMENTS_CERTIFICATE WHERE COMPANY_ID=%s  AND ACTIVE=TRUE""",(brw_each.company_id.id,))
            # result_auth=self._cr.fetchone()
            # if not result_auth:
            #     raise ValidationError(_("Al menos un Certificado Digital debe estar configurado"))
            authorization_url=PRODUCTION_URL["authorization"]
        return authorization_url
    
    @api.model
    def __resolve_client(self,client,authorization_url):
        if not client:
            client = Client(authorization_url, location=authorization_url, plugins=[logging_plugin])
        return client

    @api.model
    def test_authorized(self, sri_data_response):
        if sri_data_response and sri_data_response.autorizaciones:
            for each_authorization in sri_data_response.autorizaciones.autorizacion:
                if each_authorization.estado != "AUTORIZADO":
                    return NO_JOBS
            return COMMIT  # Si todas las autorizaciones están autorizadas
        return NO_HANDLED

    def action_recover(self):
        DEC=2
        authorization_url=None
        client=False
        documents_values={}
        documents_dscr_values={}
        payments_dscr_values={}
        def to_string_format(dct):
            return ", ".join(dct.keys()) if dct else ""
        def get_text(element, xpath, default=""):
            found = element.find(xpath) if element is not None else None
            return found.text if found is not None else default
        def analyze_invoices(etree_info, amount, vals):
            subtotal = discount = amount_no0 = amount0 = amount_tax = 0.0
            line_ids = []
            payments_info = []
            # Procesar pagos
            pagos_list = etree_info.find(".//pagos")
            if pagos_list is not None:
                for pago in pagos_list:
                    forma_pago = get_text(pago, ".//formaPago")
                    total = get_text(pago, ".//total", "0.00")
                    payments_info.append({
                        "formaPago": forma_pago,
                        "total": total,
                        "dscrFormaPago": payments_dscr_values.get(forma_pago, ""),
                    })
            # Procesar detalles
            detalles_list = etree_info.find(".//detalles")
            document_message = None
            if detalles_list is not None:
                for i, detalle in enumerate(detalles_list):
                    line_values = {
                        "codigoPrincipal": get_text(detalle, ".//codigoPrincipal"),
                        "codigoInterno": get_text(detalle, ".//codigoInterno"),
                        "descripcion": get_text(detalle, ".//descripcion"),
                        "cantidad": get_text(detalle, ".//cantidad", "1"),
                        "precioUnitario": get_text(detalle, ".//precioUnitario", "0.00"),
                        "descuento": get_text(detalle, ".//descuento", "0.00"),
                        "precioTotalSinImpuesto": get_text(detalle, ".//precioTotalSinImpuesto", "0.00"),
                    }
                    descuento = float(line_values["descuento"])
                    discount += descuento
                    if i == 0:
                        document_message = line_values["descripcion"]
                    # Procesar impuestos
                    impuestos_list = detalle.find(".//impuestos")
                    if impuestos_list is not None:
                        for impuesto in impuestos_list:
                            base_imponible = float(get_text(impuesto, ".//baseImponible", "0.00"))
                            valor = float(get_text(impuesto, ".//valor", "0.00"))
                            tarifa = round(float(get_text(impuesto, ".//tarifa", "0.00")), DEC)
                            codigo_porcentaje = get_text(impuesto, ".//codigoPorcentaje", "")
                            line_values["codigoPorcentaje"] = codigo_porcentaje
                            amount_tax += valor
                            if tarifa != 0.0:
                                amount_no0 += base_imponible
                            else:
                                amount0 += base_imponible

                            subtotal += base_imponible
                    subtotal += descuento
                    line_ids.append(line_values)
            vals["document_message"] = document_message
            total_info = [
                {"dscr": "Subtotal:", "valor": round(subtotal, DEC)},
                {"dscr": "Descuento:", "valor": round(discount, DEC)},
                {"dscr": "Base Imponible diferente 0%:", "valor": round(amount_no0, DEC)},
                {"dscr": "Base Imponible 0%:", "valor": round(amount0, DEC)},
                {"dscr": "Impuesto:", "valor": round(amount_tax, DEC)},
                {"dscr": "Valor Total:", "valor": round(amount, DEC)},
            ]

            vals["base_tax_invoice"] = round(subtotal, DEC)
            vals["tax_invoice"] = round(amount_tax, DEC)

            return line_ids, total_info, payments_info
        def analyze_info(etree_info):
            line_ids = []
            detalles_list = etree_info.find(".//infoAdicional")
            if detalles_list is not None:
                for detalle in detalles_list:
                    campo_adicional = detalle.find(".//campoAdicional")
                    if campo_adicional is not None:
                        # Obtén el último atributo como clave
                        key_attr = list(campo_adicional.attrib.keys())[-1]
                        descr_info = campo_adicional.attrib.get(key_attr, "")
                        line_ids.append({
                            "campo": descr_info,
                            "valor": campo_adicional.text or ""
                        })

            return line_ids
        for brw_each in self:
            authorization_url=self.__resolve_url(brw_each, authorization_url=authorization_url)    
            client=self.__resolve_client(client, authorization_url)
            if not documents_values and not documents_dscr_values:
                self._cr.execute("""
                        SELECT D.CODE, D.NAME, D.ID AS DOC_ID
                        FROM L10N_LATAM_DOCUMENT_TYPE D
                        WHERE D.ACTIVE = TRUE AND D.CODE IS NOT NULL
                        ORDER BY D.CODE ASC
                    """)
                documents_result = self._cr.fetchall()
                documents_values.update({code: doc_id for code, _, doc_id in documents_result})
                documents_dscr_values.update({code: name for code, name, _ in documents_result})

            if not payments_dscr_values:
                self._cr.execute("""
                        SELECT D.CODE, D.NAME
                        FROM L10N_EC_SRI_PAYMENT D
                        WHERE D.CODE IS NOT NULL
                        ORDER BY D.CODE ASC
                    """)
                payments_result = self._cr.fetchall()
                payments_dscr_values.update({code: name for code, name in payments_result})
            if brw_each.state not in ("updated", "annulled"):
                sri_data_response = client.service.autorizacionComprobante(brw_each.access_key)
                vals={}
                variables={}
                test=self.test_authorized(sri_data_response)                
                if test==COMMIT:#sri_data_response.autorizaciones
                    if hasattr(sri_data_response.autorizaciones, "autorizacion"):
                        if sri_data_response.autorizaciones.autorizacion[0].estado != "AUTORIZADO":
                            vals={"state":"error",
                              "xml":None,
                              "msg":"DOCUMENTO NO AUTORIZADO","state_sri":"annulled"
                            }
                            if(not brw_each.invoice_id and not brw_each.witthold_id):
                                vals["confirmed_state"]="rejected"
                            _logger.warning("DOCUMENTO NO AUTORIZADO %s" % (brw_each.access_key,))
                        if hasattr(sri_data_response.autorizaciones.autorizacion[0], "comprobante"):
                            comprobante=sri_data_response.autorizaciones.autorizacion[0].comprobante
                            etree_info = etree.fromstring(comprobante.encode('utf-8'))
                            vals={"state":"error",
                                            "xml":None,
                                            "msg":"ERROR AL PROCESAR","state_sri":"not_processed"}
                            try:
                                document_related=None    
                                codDoc=etree_info.find(".//codDoc").text                        
                                estab = etree_info.find(".//estab").text
                                ptoEmi = etree_info.find(".//ptoEmi").text
                                secuencial = etree_info.find(".//secuencial").text
                                fechaEmision= etree_info.find(".//fechaEmision").text
                                ruc= etree_info.find(".//ruc").text
                                razonSocial= etree_info.find(".//razonSocial").text
                                vals["document"]="%s-%s-%s" % (estab,ptoEmi,secuencial)
                                vals["document_date_auth"]=sri_data_response.autorizaciones.autorizacion[0].fechaAutorizacion
                                vals["date"]= datetime.strptime(fechaEmision, "%d/%m/%Y").strftime("%Y-%m-%d")
                                vals["identification"]=ruc
                                vals["environment_type"]=etree_info.find(".//ambiente").text
                                vals["partner_name"]=razonSocial.encode('ASCII', 'ignore')
                                vals["document_type_id"]=documents_values.get(codDoc,False)
                                srch_partner=self.env["res.partner"].sudo().search([('vat','=',ruc),('parent_id','=',False)])
                                vals["partner_id"]=srch_partner and srch_partner[0].id or False                                
                                variables={
                                    "razonSocial":razonSocial.upper(),
                                    "ruc":ruc,
                                    "fechaEmision":fechaEmision,
                                    "claveAcceso":etree_info.find(".//claveAcceso").text,
                                    "documento":"%s-%s-%s" % (estab,ptoEmi,secuencial),
                                    "dirMatriz":etree_info.find(".//dirMatriz").text.upper(),
                                    "tipoDocumento":documents_dscr_values.get(codDoc,False).upper(),
                                    "tipoEmision":etree_info.find(".//tipoEmision").text ,
                                    "ambiente":vals["environment_type"] , 
                                    "obligadoContabilidad":(etree_info.find(".//obligadoContabilidad") is not None) and etree_info.find(".//obligadoContabilidad").text or "NO",
                                    "withhold_line_ids":[],
                                    "line_ids":[],
                                    "infoAdicional": [],
                                    "total_info":[]                                             
                                }
                                variables["tipoEmision"]=(variables["tipoEmision"]=="1") and "NORMAL" or "NORMAL"##solo hay normal
                                variables["ambiente"]=(variables["ambiente"]=="1") and "PRUEBA" or "PRODUCCION"
                                amount=0.00
                                if(etree_info.tag=="factura"):
                                    facturaTag=etree_info.find(".//infoFactura")
                                    amount=float(facturaTag.find(".//importeTotal").text) 
                                    line_ids,total_info,payments_info=analyze_invoices(etree_info,amount,vals)
                                    variables.update({
                                        "razonSocialDocumento":facturaTag.find(".//razonSocialComprador").text.upper(),
                                        "identificacionDocumento":facturaTag.find(".//identificacionComprador").text,
                                        "tipoIdentificacionDocumento":IDENTIFICATION_DESCR[facturaTag.find(".//tipoIdentificacionComprador").text], 
                                        "contribuyenteEspecial":(facturaTag.find(".//contribuyenteEspecial") is not  None)  and facturaTag.find(".//contribuyenteEspecial").text or "NO",
                                        "total":amount,
                                        "documentoRelacionado":"" ,
                                        "direccionSocioDocumento":(facturaTag.find(".//direccionComprador") is not None) and facturaTag.find(".//direccionComprador").text or "",
                                        "withhold_line_ids":[]  ,
                                        "line_ids":line_ids,
                                        "infoAdicional": analyze_info(etree_info)   ,
                                        "total_info":  total_info,
                                        "payments_info":payments_info                                         
                                    })  
                                if(etree_info.tag=="notaCredito"):
                                    notaCreditoTag=etree_info.find(".//infoNotaCredito")                                    
                                    amount=float(notaCreditoTag.find(".//valorModificacion").text)
                                    document_related=notaCreditoTag.find(".//numDocModificado").text
                                    fechaEmisionDocSustento=notaCreditoTag.find(".//fechaEmisionDocSustento").text
                                    line_ids,total_info,payments_info=analyze_invoices(etree_info,amount,vals)
                                    variables.update({
                                        "razonSocialDocumento":notaCreditoTag.find(".//razonSocialComprador").text.upper(),
                                        "identificacionDocumento":notaCreditoTag.find(".//identificacionComprador").text,
                                        "tipoIdentificacionDocumento":IDENTIFICATION_DESCR[notaCreditoTag.find(".//tipoIdentificacionComprador").text], 
                                        "contribuyenteEspecial":(notaCreditoTag.find(".//contribuyenteEspecial") is not  None)  and notaCreditoTag.find(".//contribuyenteEspecial").text or "NO",
                                        "total":amount,
                                        "documentoRelacionado": document_related   ,
                                        "fechaEmisionDocSustento":datetime.strptime(fechaEmisionDocSustento, "%d/%m/%Y").strftime("%Y-%m-%d"),
                                        "direccionSocioDocumento":(notaCreditoTag.find(".//direccionComprador") is not None) and notaCreditoTag.find(".//direccionComprador").text or "",
                                        "withhold_line_ids":[]      ,
                                        "line_ids":line_ids,
                                        "infoAdicional": analyze_info(etree_info)   ,
                                        "total_info":  total_info,
                                        "payments_info":payments_info
                                    })                                
                                if(etree_info.tag=="comprobanteRetencion"):
                                    taxes_codes={}
                                    base_withhold,base_withhold_fte,base_withhold_iva,base_withhold_invoice=0.00,0.00,0.00,0.00
                                    tax_total,tax_fte,tax_iva=0.00,0.00,0.00                                    
                                    withhold_line_ids=[]
                                    retencionTag=etree_info.find(".//infoCompRetencion")    
                                    sustentoList=etree_info.find(".//docsSustento")###docsSustento/docSustento/retenciones/retencion
                                    if sustentoList is not None:
                                        sustentoList=sustentoList.getchildren()                                    
                                        for eachSustentoRetencion in sustentoList:
                                            if(eachSustentoRetencion is not None):
                                                numDocSustento=eachSustentoRetencion.find(".//numDocSustento")
                                                fechaEmisionDocSustento=eachSustentoRetencion.find(".//fechaEmisionDocSustento")
                                                document_related=numDocSustento is not None and numDocSustento.text or "000000000000000"
                                                center_line_code="%s-%s" % (document_related[:3],document_related[3:6])
                                                if((document_related is not None and document_related) and len(document_related)>=15):
                                                    document_related="%s-%s-%s" % (document_related[:3],document_related[3:6],document_related[6:])
                                                impuestoList=eachSustentoRetencion.find(".//retenciones")
                                                if impuestoList is not None:
                                                    impuestoList=impuestoList.getchildren()
                                                    for eachImpRetencion in impuestoList:
                                                        valorImpuesto,porcentajeRetener,codigoRetencion,baseImponible=0.00,None,None,None
                                                        if(eachImpRetencion  is not None):
                                                            valorImpuesto=float(eachImpRetencion.find(".//valorRetenido")  is not  None and eachImpRetencion.find(".//valorRetenido").text or "0.00")
                                                            porcentajeRetener=eachImpRetencion.find(".//porcentajeRetener")
                                                            codigoRetencion=eachImpRetencion.find(".//codigoRetencion") 
                                                            if not codigoRetencion is None:
                                                                taxes_codes[codigoRetencion.text]=False                                                           
                                                            baseImponible=eachImpRetencion.find(".//baseImponible")
                                                            amount+=valorImpuesto
                                                            withhold_line_ids.append({
                                                                'numDocSustento':(numDocSustento is not None and numDocSustento.text or ""),
                                                                'fechaEmisionDocSustento':(fechaEmisionDocSustento is not None and fechaEmisionDocSustento.text or ""),
                                                                'periodoFiscal':(fechaEmisionDocSustento is not None and fechaEmisionDocSustento.text[3:] or ""),
                                                                'baseImponible':(baseImponible is not None and baseImponible.text or ""),
                                                                'codigoRetencion':(codigoRetencion is not None and codigoRetencion.text or "") ,
                                                                'porcentajeRetener':(porcentajeRetener is not None and porcentajeRetener.text or ""),
                                                                'valorImpuesto':valorImpuesto
                                                            })
                                                            codigo=eachImpRetencion.find(".//codigo") 
                                                            codigo=(codigo is not None and codigo.text or "")                                                     
                                                            baseImponibleAmount=float(baseImponible  is not  None and baseImponible.text or "0.00")
                                                            if codigo== "1":##RENTA
                                                                tax_total+=valorImpuesto
                                                                tax_fte+=valorImpuesto
                                                                base_withhold_fte+=baseImponibleAmount
                                                            if codigo== "2":##IVA
                                                                tax_total+=valorImpuesto
                                                                tax_iva+=valorImpuesto
                                                                base_withhold_iva+=baseImponibleAmount
                                                            base_withhold+=  baseImponibleAmount                                     
                                    impuestoList=etree_info.find(".//impuestos")
                                    if impuestoList is not None:
                                        impuestoList=impuestoList.getchildren()
                                        for eachImpRetencion in impuestoList:
                                            if(eachImpRetencion  is not None):
                                                numDocSustento=eachImpRetencion.find(".//numDocSustento")
                                                fechaEmisionDocSustento=eachImpRetencion.find(".//fechaEmisionDocSustento")
                                                valorImpuesto,porcentajeRetener,codigoRetencion,baseImponible=0.00,None,None,None
                                                if(eachImpRetencion  is not None):
                                                    valorImpuesto=float(eachImpRetencion.find(".//valorRetenido")  is not  None and eachImpRetencion.find(".//valorRetenido").text or "0.00")
                                                    porcentajeRetener=eachImpRetencion.find(".//porcentajeRetener")
                                                    codigoRetencion=eachImpRetencion.find(".//codigoRetencion") 
                                                    baseImponible=eachImpRetencion.find(".//baseImponible")
                                                    if not codigoRetencion is None:
                                                        taxes_codes[codigoRetencion.text]=False 
                                                    amount+=valorImpuesto                                                    
                                                    document_related=numDocSustento is not None and numDocSustento.text or "000000000000000"
                                                    center_line_code="%s-%s" % (document_related[:3],document_related[3:6])
                                                    if((document_related is not None and document_related) and len(document_related)>=15):
                                                        document_related="%s-%s-%s" % (document_related[:3],document_related[3:6],document_related[6:])
                                                    codigo=eachImpRetencion.find(".//codigo") 
                                                    codigo=(codigo is not None and codigo.text or "")                                                     
                                                    baseImponibleAmount=float(baseImponible  is not  None and baseImponible.text or "0.00")
                                                    if codigo== "1":##RENTA
                                                        tax_total+=valorImpuesto
                                                        tax_fte+=valorImpuesto
                                                        base_withhold_fte+=baseImponibleAmount
                                                    if codigo== "2":##IVA
                                                        tax_total+=valorImpuesto
                                                        tax_iva+=valorImpuesto
                                                        base_withhold_iva+=baseImponibleAmount
                                                    base_withhold+=  baseImponibleAmount                                                            
                                                    withhold_line_ids.append({
                                                           'numDocSustento':(numDocSustento is not None and numDocSustento.text or ""),
                                                            'fechaEmisionDocSustento':(fechaEmisionDocSustento is not None and fechaEmisionDocSustento.text or ""),
                                                            'periodoFiscal':(fechaEmisionDocSustento is not None and fechaEmisionDocSustento.text[3:] or ""),
                                                            'baseImponible':(baseImponible is not None and baseImponible.text or ""),
                                                            'codigoRetencion':(codigoRetencion is not None and codigoRetencion.text or "") ,
                                                            'porcentajeRetener':(porcentajeRetener is not None and porcentajeRetener.text or ""),
                                                            'valorImpuesto':valorImpuesto
                                                        })  
                                                    if not codigoRetencion is None:
                                                        taxes_codes[codigoRetencion.text]=False  
                                    variables.update({
                                        "razonSocialDocumento":retencionTag.find(".//razonSocialSujetoRetenido").text.upper(),
                                        "identificacionDocumento":retencionTag.find(".//identificacionSujetoRetenido").text,
                                        "tipoIdentificacionDocumento":IDENTIFICATION_DESCR[retencionTag.find(".//tipoIdentificacionSujetoRetenido").text], 
                                        "contribuyenteEspecial":(retencionTag.find(".//contribuyenteEspecial") is not  None) and retencionTag.find(".//contribuyenteEspecial").text or "",
                                        "total":amount,
                                        "documentoRelacionado":document_related or ""    ,
                                        "direccionSocioDocumento":"",
                                        "withhold_line_ids":withhold_line_ids,
                                        "line_ids":[],
                                        "infoAdicional": analyze_info(etree_info),
                                        "total_info":[{
                                            "dscr":"Total Retención",
                                            "valor":amount
                                            }]
                                    }) 
                                    vals["taxes_codes"]= to_string_format(taxes_codes)
                                    vals["base_withhold"]=base_withhold
                                    vals["base_withhold_fte"]=base_withhold_fte
                                    vals["base_withhold_iva"]=base_withhold_iva
                                    vals["tax_total"]=tax_total
                                    vals["tax_fte"]=tax_fte
                                    vals["tax_iva"]=tax_iva
                                                                                       
                                vals["document_related"]=document_related
                                vals["amount"]=amount
                                vals.update({"state":"updated",
                                            "xml":comprobante,
                                            "msg":"OK",
                                            "variables":str(variables),
                                            "state_sri":"authorized",
                                            "confirmed_state":(not brw_each.invoice_id and not brw_each.withhold_id) and "received" or "approved"
                                            })                                
                            except Exception as e:
                                vals["msg"]=str(e)                            
                        else:
                            vals={"state":"error",
                              "xml":None,
                              "msg":"SIN COMPROBANTE","state_sri":"not_processed"}
                            _logger.warning("DOCUMENTO SIN COMPROBANTE %s %s" % (brw_each.access_key,sri_data_response))
                    else:
                        vals={"state":"error",
                              "xml":None,
                              "msg":"SIN RESPUESTA","state_sri":"not_processed"}
                        _logger.warning("SIN AUTORIZACION %s %s" % (brw_each.access_key,sri_data_response.autorizaciones))
                else:
                    msg="SIN RESPUESTA"
                    state_sri="not_processed"#test -1
                    if not test or test==NO_JOBS:##anulado
                        if hasattr(sri_data_response, "numeroComprobantes"):
                            if int(sri_data_response.numeroComprobantes)==0:
                                msg="NO ES POSIBLE RECUPERAR COMPROBANTES"
                                state_sri="annulled"
                    vals={"state":"error",
                          "xml":None,
                          "msg":msg,"state_sri":state_sri}
                    if not brw_each.invoice_id and not brw_each.withhold_id:
                        vals["confirmed_state"]="rejected"
                brw_each.write(vals) 
                #OBJ_HISTORY=self.env["electronic.document.received.history"]
                #OBJ_HISTORY.register(brw_each.id,_("REGISTRO ACTUALIZADO" ),vals["state"],confirmed_state=vals.get("confirmed_state",None) )
        return True
    
    def action_recover_state_sri(self):        
        def get_state_sri_response(client,brw_each,vals):
            sri_data_response = client.service.autorizacionComprobante(brw_each.access_key)            
            if sri_data_response.autorizaciones:
                if hasattr(sri_data_response.autorizaciones, "autorizacion"):
                    test=self.test_authorized(sri_data_response)
                    if test==COMMIT:
                        if brw_each.state_sri!= "authorized":
                            vals["state_sri"]="authorized"
                        if(brw_each.invoice_id or brw_each.withhold_id):
                            vals["confirmed_state"]="confirmed"
                    if test==NO_JOBS or not test:
                        vals["state_sri"]="annulled" 
                        if(not brw_each.invoice_id and not brw_each.withhold_id):
                            vals["confirmed_state"]="rejected"
                    if test==NO_HANDLED:
                        vals["state_sri"]="not_found"
            else:
                vals["state_sri"]="not_found"
                if sri_data_response.claveAccesoConsultada:                
                    vals["state_sri"]="annulled"
                    if not brw_each.invoice_id and not brw_each.withhold_id:
                        vals["confirmed_state"]="rejected"
            return vals
        authorization_url=None
        client=False
        msg=None
        try:
            for brw_each in self:
                msg=brw_each.access_key
                vals={}
                authorization_url=self.__resolve_url(brw_each, authorization_url=authorization_url)    
                client=self.__resolve_client(client, authorization_url) 
                vals=get_state_sri_response(client,brw_each,vals)
                if vals:
                    brw_each.write(vals) 
                    #OBJ_HISTORY=self.env["electronic.document.received.history"]
                    #OBJ_HISTORY.register(brw_each.id,_("REGISTRO ACTUALIZADO" ),brw_each.state,confirmed_state=vals.get("confirmed_state",None) )
        except Exception as e:
            _logger.warning("ERROR AL ACTUALIZAR ESTADO DEL SRI %s--> %s" % ((msg is None) or "",str(e)))
        return True
        
    def action_get_pdf(self):
        self=self.with_context({"no_raise":True})
        self=self.with_user(SUPERUSER_ID)
        for brw_each in self:
            if(not brw_each.document_type_id):
                raise ValidationError(_("No hay datos para el documento %s") % (brw_each.access_key,))
            try:
                OBJ_DOCUMENT_RECEIVED=self.env["electronic.document.received"].sudo()
                context = dict(active_ids=[brw_each.id], 
                               active_id=brw_each.id,
                               active_model=self._name,
                               landscape=True
                               )            
                OBJ_DOCUMENT_RECEIVED=OBJ_DOCUMENT_RECEIVED.with_context(context)
                report_value= OBJ_DOCUMENT_RECEIVED.env.ref('gps_einvoice_received.electronic_document_received_report_documents').with_user(SUPERUSER_ID).report_action(OBJ_DOCUMENT_RECEIVED)
                report_value["target"]="new"
                return report_value
            except Exception as e:
                raise ValidationError(_("Error al Imprimir 'gps_einvoice_received.electronic_document_received_report_documents' -- %s") % (str(e),))
    
    def get_xml_data_file(self):
        for brw_each in self:
            xml_file=False
            if brw_each.xml:
                f = tempfile.NamedTemporaryFile(delete=False, suffix=".xml")
                f.close()
                fileName=f.name
                xml_body="""<?xml version="1.0" encoding="UTF-8"?>
<autorizacion>
  <estado>AUTORIZADO</estado>
  <numeroAutorizacion>%s</numeroAutorizacion>
  <fechaAutorizacion>%s</fechaAutorizacion>
  <ambiente>%s</ambiente>
  <comprobante>%s</comprobante> 
</autorizacion>""" % (brw_each.access_key,brw_each.document_date_auth,brw_each.environment_type ,html.escape(brw_each.xml, quote=False))
                with open(fileName, mode="w") as file:
                    file.write(xml_body)
                with open(fileName, mode='rb') as file:
                    fileContent = file.read()
                    xml_file=base64.b64encode(fileContent)
            brw_each.xml_file=xml_file
            
    def action_get_xml(self):
        self.ensure_one()
        brw_each=self
        #brw_each.get_xml_data_file()
        return {
                     'type' : 'ir.actions.act_url',
                     'url': '/web/content/%s/%s/xml_file/%s' % (brw_each._name,brw_each.id,("%s - %s.xml" % (brw_each.document_type_id.name,brw_each.document))),
                     'target': 'new'
        }
    
    def get_variables(self):
        def executeProgrammingCode(programming_code,global_dict, localdict):
            safe_eval(programming_code,global_dict, localdict, mode='exec', nocopy=True)
            return localdict
        variables={"msg_error":None}
        try:
            if self.variables:
                variables={}
                VARIABLES_TEST="result=%s" % (self.variables or "{}",)
                result=executeProgrammingCode(VARIABLES_TEST,variables,variables)
                variables=result.get("result",{})
                variables["msg_error"]=None
        except Exception as e:
            msg=_("ERROR EN EXPRESION PARA ID %s --> %s )") % (self.id,str(e))
            variables={"msg_error":msg}
            _logger.warning(msg)
        return variables

    @api.model
    def update_received_documents_states(self):
        self._cr.execute("""update
 electronic_document_received
 set 
 invoice_id=x.invoice_id,
 confirmed_state=case when(x.invoice_id is null) then 'received' else 'confirmed' end 
 from  
 (
 select 
     edr.id,
     aiw.id as invoice_id,
     count(1) as record_counter 
     from 
     electronic_document_received edr
     inner join account_move aiw on aiw.authorization_type='electronica' 
	 		and aiw.move_type in ('in_invoice','in_refund')
     and aiw.l10n_ec_authorization_number=edr.access_key and aiw.state='posted'
	 and aiw.company_id=edr.company_id 
     inner join l10n_latam_document_type ddt on ddt.id=edr.document_type_id and aiw.l10n_latam_document_type_id=edr.document_type_id
     where  ddt.code!='07' and  edr.state='updated' and edr.invoice_id is null 
     group by edr.id,
     aiw.id
     having count(1)=1
 ) x 
 where electronic_document_received.id=x.id ;
 
update electronic_document_received
set withhold_id=x.withhold_id,
invoice_id=x.invoice_id,
state_number_error=case when(x.withhold_id is null) then 'error' else 'related' end
from (
         select 
         edr.id,
         wtinv.withhold_id,
         wtinv.invoice_id 
         from electronic_document_received edr
         inner join l10n_latam_document_type ddt on ddt.id=edr.document_type_id  and  ddt.code='07' 
         left join (
            select aml.move_id as  withhold_id,
            aml.l10n_ec_withhold_invoice_id as invoice_id ,
            am.l10n_ec_authorization_number,
            am.company_id
            from account_move_line aml
            inner join account_move am on am.id=aml.move_id  and am.state='posted'
            inner join account_move ami on ami.id=aml.l10n_ec_withhold_invoice_id and
            (
                ami.move_type='out_invoice' and ami.state='posted'
            )
            where   aml.l10n_ec_withhold_invoice_id is not null and am.state='posted'
            group by aml.move_id ,
            aml.l10n_ec_withhold_invoice_id,
            am.l10n_ec_authorization_number,
            am.company_id
         ) wtinv on wtinv.l10n_ec_authorization_number=edr.access_key   and wtinv.company_id=edr.company_id 
         where  edr.state='updated'  and edr.withhold_id is null
) x
where electronic_document_received.id=x.id;


update
electronic_document_received
set 
out_withhold_id=x.out_withhold_id
from 
(
	select 
     edr.id,
     wtinv.out_withhold_id,
	 wtinv.invoice_id 
     from electronic_document_received edr
	 inner join l10n_latam_document_type ddt on ddt.id=edr.document_type_id  and  ddt.code='07' 
     inner join (
		select aml.move_id as  out_withhold_id,
 		aml.l10n_ec_withhold_invoice_id as invoice_id ,
	 	am.l10n_ec_authorization_number,
 		am.company_id
		from account_move_line aml
		inner join account_move am on am.id=aml.move_id  and am.state='posted'
		inner join account_move ami on ami.id=aml.l10n_ec_withhold_invoice_id and
		(
		    ami.move_type='in_invoice' and ami.state='posted'
		)
		where   aml.l10n_ec_withhold_invoice_id is not null and am.state='posted'
		group by aml.move_id ,
 		aml.l10n_ec_withhold_invoice_id,
	 	am.l10n_ec_authorization_number,
 		am.company_id
	 ) wtinv on wtinv.invoice_id=edr.invoice_id  and wtinv.company_id=edr.company_id and ddt.code='01'
     where  edr.state='updated'  and edr.invoice_id is not null

) x 
where electronic_document_received.id=x.id;
 
 """)
        return True
    
    @api.model
    def _where_calc(self, domain, active_test=True):
        if not domain:
            domain=[]
        # if self._context.get("pass_compute",False):
        #     return super(ElectronicDocumentReceived,self)._where_calc(domain, active_test)
        # if (self._uid not in (SUPERUSER_ID,)):
        #     OBJ_USERS  =self.env["res.users"].sudo()                 
        #     brw_user=OBJ_USERS.browse(self._uid)
        #     sucursales=brw_user.resolve_user_group_ref("std_abastecimiento","group_warehouse_sales_usr")##sucursales
        #     sucursal_read_usr=brw_user.resolve_user_group_ref(MODULE_NAME,"group_documents_user_read_usr")
        #     department_usr=brw_user.resolve_user_group_ref(MODULE_NAME,"group_documents_user_read_department_usr")
        #     config_usr=brw_user.resolve_user_group_ref(MODULE_NAME,"group_documents_user_config_usr")
        #     admin_usr=brw_user.resolve_user_group_ref(MODULE_NAME,"group_documents_user_admin_usr")
        #     approved_usr=brw_user.resolve_user_group_ref(MODULE_NAME,"group_documents_approve_document_usr")  
        #     if not admin_usr and not  config_usr:##no es financiero ,ni sistemas(admin)
        #         if(department_usr or approved_usr):
        #             domain.append(("document_type_id.code","!=","07") ) ##ven fac y nc
        #             domain=self.update_domain_invoice_rc(domain,self._uid)
        #         else:
        #             if sucursal_read_usr and sucursales:
        #                 domain.append(("document_type_id.code","=","07") ) #retenciones
        #                 warehouse_ids=brw_user.get_filtered_establishment_ids(company_id=brw_user.company_id and brw_user.company_id.id or False,noempty=True)
        #                 domain.append(("warehouse_id","in",tuple(warehouse_ids)) )
        return super(ElectronicDocumentReceived,self)._where_calc(domain, active_test)
    
    @api.model
    def update_domain_invoice_rc(self,domain,uid):        
        if not domain:
            domain=[]
        if not uid:
            return domain
        result=self.__get_partner_list_ids(uid)
        if not result:
            return domain
        domain.append(('partner_id','in',tuple(result)))
        return domain
    
    @api.model
    def __get_partner_list_ids(self,uid):
        self._cr.execute("""select partner_group_id,count(1) as counter 
from  
partner_groups_doc_rel
where user_id=%s 
group by partner_group_id 
""",(uid,))
        result=self._cr.fetchone()
        if not result:
            return []
        partner_group_id=result[0]
        self._cr.execute("""select partner_id,partner_id from partner_groups_partners_rel where partner_group_id=%s """,(partner_group_id,))
        result=self._cr.fetchall()
        result=result and list(dict(result).keys()) or []
        result+=[-1,-1]
        return result
    
    def update_partner(self):
        OBJ_MODEL_DATA=self.env["ir.model.data"].sudo()
        domain=[]
        self.ensure_one()
        brw_each=self
        OBJ_PARTNER=self.env["res.partner"].sudo()
        brw_user=self.env["res.users"].browse(self._uid)
        if not brw_each.partner_id:
            partner_srch=OBJ_PARTNER.search([('vat','=',brw_each.identification)])
            if partner_srch:
                brw_each.partner_id=partner_srch[0].id 
                return True                   
        tree_id = OBJ_MODEL_DATA.resolve_view_ref("base","view_partner_tree")
        form_id = OBJ_MODEL_DATA.resolve_view_ref("base","view_partner_form")
        search_id = OBJ_MODEL_DATA.resolve_view_ref("base","view_res_partner_filter")  
        variables=brw_each.get_variables()                      
        context={"search_default_vat":brw_each.identification,
                 "default_vat":brw_each.identification,
                 "default_name":brw_each.partner_name,
                 "default_country_id":brw_user.company_id.country_id.id,
                 "default_company_type":len(brw_each.identification)==13 and "company" or "person",
                 "default_street":variables.get("dirMatriz",None)
                 }        
        return {
                        'domain': domain,
                        'name': brw_each.identification,
                        'view_mode': 'tree,form',
                        'search_view_id': search_id ,
                        'res_model': OBJ_PARTNER._name,
                        'views': [(tree_id, 'tree'),(form_id, 'form')],
                        "context":context,
                        'type': 'ir.actions.act_window'
                    }  
                   
    def create_process_document(self):
        for brw_each in self:
            if not brw_each.partner_id:
                partner_srch=self.env["res.partner"].sudo().search([('vat','=',brw_each.identification)])
                if partner_srch:
                    brw_each.partner_id=partner_srch[0].id
            if not brw_each.partner_id:
                raise ValidationError(_("No existe proveedor/cliente con identificacion %s ") % (brw_each.identification))
            if brw_each.document_type_code=="07":
                brw_each.create_withhold()
            else:
                if brw_each.document_type_code=="01" and brw_each.invoice_type=="inventory" and not brw_each.order_id:
                    brw_each.create_purchase_order()
                else:
                    if brw_each.invoice_type=="service" and not brw_each.service_id:
                        raise ValidationError(_("Debes definir un  servicio"))
                    brw_each.create_invoice()
        return True
    
    def create_purchase_order(self):
        OBJ_PARTNER=self.env["res.partner"].sudo()
        OBJ_PURCHASE=self.env["purchase.order"].sudo()
        for brw_each in self:
            if not brw_each.process_order_id:
                variables=brw_each.get_variables()
                fechaEmision=variables["fechaEmision"]
                documento=variables["documento"]
                ruc=variables["ruc"]
                line_ids=variables["line_ids"]
                srch_partner=OBJ_PARTNER.search([('vat','=',ruc)])
                if not srch_partner:
                    raise ValidationError(_("Cliente/Proveedor con ID %s no existe") % (ruc,))
                vals={     
                    "currency_id":brw_each.company_id.currency_id.id,
                    "partner_id":brw_each.partner_id.id,
                    "partner_ref":brw_each.partner_id.vat,
                    "date_order":None,#dtObj.strf(dtObj.parse(fechaEmision, "%d/%m/%Y"),"%Y-%m-%d"),
                    "date_planned":None,#dtObj.strf(dtObj.parse(fechaEmision, "%d/%m/%Y"),"%Y-%m-%d"),
                    "origin":brw_each.access_key,
                    "payment_term_id":brw_each.partner_id.property_supplier_payment_term_id and brw_each.partner_id.property_supplier_payment_term_id.id or False,
                    "fiscal_position_id":brw_each.partner_id.property_account_position_id and brw_each.partner_id.property_account_position_id.id or False,
                }
                order_line=[(5,)]
                sequence=1
                dct_products={}
                dct_taxes={}
                for each_line in line_ids:
                    codigoPrincipal=each_line.get("codigoPrincipal",False)
                    if not codigoPrincipal or len(codigoPrincipal)<=0:
                        codigoPrincipal=each_line.get("codigoInterno",False)
                    if brw_each.invoice_type!="service":
                        if not dct_products.get(codigoPrincipal,False):
                            self._cr.execute("""SELECT X.PRODUCT_CODE,
                             COALESCE(X.PRODUCT_ID,PP.ID) AS PRODUCT_ID
                                    FROM PRODUCT_SUPPLIERINFO  X
        INNER JOIN PRODUCT_TEMPLATE PT ON  PT.ID=X.PRODUCT_TMPL_ID
        INNER JOIN PRODUCT_PRODUCT PP ON PP.PRODUCT_TMPL_ID=PT.ID
                            WHERE X.PRODUCT_CODE IS NOT NULL 
                                    AND X.PARTNER_ID=%s AND 
                                    X.PRODUCT_CODE=%s """,(srch_partner[0].id,codigoPrincipal) )
                            result_product=self._cr.fetchone()
                            if result_product:
                                dct_products[result_product[0]]=result_product[1]                    
                    descripcion=each_line["descripcion"]
                    cantidad=each_line["cantidad"]
                    precioUnitario=each_line["precioUnitario"]
                    descuento=float(each_line.get("descuento","0.00"))
                    codigoPorcentaje=each_line.get("codigoPorcentaje",False)
                    precioTotalSinImpuesto=each_line["precioTotalSinImpuesto"]
                    total_sin_descuento=float(cantidad)*float(precioUnitario)
                    total=0.00
                    if total_sin_descuento>0:
                        total=(float(precioTotalSinImpuesto)/total_sin_descuento)
                    discount=(total>0 and descuento>0) and descuento/total or 0.00
                    if(discount>1.00):
                        discount=1.00
                    discount=discount*100.00
                    taxes_id=[(6,0,[])]
                    if codigoPorcentaje:
                        if not dct_taxes.get(codigoPorcentaje,False):
                            srch=self.env["account.tax"].sudo().search([('type_tax_use','=','purchase'),('l10n_ec_code_ats','=',codigoPorcentaje)])
                            if srch:
                                dct_taxes[codigoPorcentaje]=srch[0].id
                        taxes_id=[(6,0,dct_taxes.get(codigoPorcentaje,False) and [dct_taxes.get(codigoPorcentaje,False)] or [])] 
                    product_id=dct_products.get(codigoPrincipal,False)
                    order_line.append((0,0,{
                        "product_id":product_id,
                        "name":descripcion,
                        "product_qty":float(cantidad),
                        "price_unit":float(precioUnitario),
                        "taxes_id":taxes_id,
                        "locked":True,
                        "imported_code":codigoPrincipal,
                        "imported_description":descripcion,
                        "imported_price":float(precioUnitario),
                        "imported_qty":float(cantidad)
                        }))
                    sequence+=1
                vals["order_line"]=order_line
                brw_process_doc=OBJ_PURCHASE.create(vals)
                brw_each.write({"process_order_id":brw_process_doc.id}) 
        return  True
    
    def create_invoice(self):
        OBJ_PARTNER=self.env["res.partner"].sudo()
        OBJ_JOURNAL=self.env["account.journal"].sudo()
        OBJ_MOVE=self.env["account.move"].sudo()
        for brw_each in self:
            if not brw_each.invoice_id:
                move_type=(brw_each.document_type_id.code=="01" and "in_invoice" or "in_refund")
                variables=brw_each.get_variables()
                fechaEmision=variables["fechaEmision"]
                documento=variables["documento"]
                ruc=variables["ruc"]
                claveAcceso=variables["claveAcceso"]
                line_ids=variables["line_ids"]
                srch_partner=OBJ_PARTNER.search([('vat','=',ruc)])
                if not srch_partner:
                    raise ValidationError(_("Cliente/Proveedor con ID %s no existe") % (ruc,))
                ###buscad documento
                srch_journal=OBJ_JOURNAL.search([('type','=',"purchase"),('code','=',"FACTU"),('company_id','=',brw_each.company_id.id)])
                if not srch_journal:
                    raise ValidationError(_("No hay un diario definido por defecto para Facturas de Proveedores"))
                documento_relacionado=None
                fecha_documento_relacionado=None
                reversed_entry_id=False
                required_origin_info=False                
                if move_type=="in_refund":
                    required_origin_info=True
                    documento_relacionado=variables["documentoRelacionado"]
                    fecha_documento_relacionado=variables["fechaEmisionDocSustento"]
                    srch_reversed=OBJ_MOVE.search([('partner_id','=',srch_partner[0].id),
                                                   ('move_type','=','in_invoice'),
                                                   ('state','=','posted'),
                                                   ('format_name','=',documento_relacionado)
                                                   ])
                    reversed_entry_id=srch_reversed and srch_reversed[0].id or False
                vals={
                    "partner_id":srch_partner[0].id,
                    "date": dtObj.strf(dtObj.parse(fechaEmision, "%d/%m/%Y"),"%Y-%m-%d"),
                    "invoice_date": dtObj.strf(dtObj.parse(fechaEmision, "%d/%m/%Y"),"%Y-%m-%d"),
                    "journal_id":srch_journal[0].id,
                    "company_id":brw_each.company_id.id,
                    "currency_id":brw_each.company_id.currency_id.id,
                    "move_type":move_type,
                    "l10n_latam_document_number":documento,
                    "l10n_latam_document_type_id":brw_each.document_type_id.id,
                    "l10n_latam_use_documents":True,
                    "manual_origin":True,
                    "required_origin_info":required_origin_info,
                    "manual_origin_docnum":documento_relacionado,
                    "manual_origin_docdate":fecha_documento_relacionado,
                    "reversed_entry_id":reversed_entry_id,
                    "authorization_type":"electronica",
                    "l10n_ec_authorization_number":claveAcceso
                }
                invoice_line_ids=[(5,)]
                sequence=1
                dct_products={}
                dct_taxes={}
                for each_line in line_ids:
                    codigoPrincipal=each_line.get("codigoPrincipal",False)
                    if not codigoPrincipal or len(codigoPrincipal)<=0:
                        codigoPrincipal=each_line.get("codigoInterno",False)
                    if brw_each.invoice_type!="service":                        
                        if not dct_products.get(codigoPrincipal,False):
                            self._cr.execute("""SELECT X.PRODUCT_CODE,
                             COALESCE(X.PRODUCT_ID,PP.ID) AS PRODUCT_ID
                                    FROM PRODUCT_SUPPLIERINFO  X
        INNER JOIN PRODUCT_TEMPLATE PT ON  PT.ID=X.PRODUCT_TMPL_ID
        INNER JOIN PRODUCT_PRODUCT PP ON PP.PRODUCT_TMPL_ID=PT.ID
                            WHERE X.PRODUCT_CODE IS NOT NULL 
                                    AND X.PARTNER_ID=%s AND 
                                    X.PRODUCT_CODE=%s """,(srch_partner[0].id,codigoPrincipal) )
                            result_product=self._cr.fetchone()
                            if result_product:
                                dct_products[result_product[0]]=result_product[1]                    
                    descripcion=each_line["descripcion"]
                    cantidad=each_line["cantidad"]
                    precioUnitario=each_line["precioUnitario"]
                    codigoPorcentaje=each_line.get("codigoPorcentaje",False)
                    descuento=float(each_line.get("descuento","0.00"))
                    precioTotalSinImpuesto=each_line["precioTotalSinImpuesto"]
                    total_sin_descuento=float(cantidad)*float(precioUnitario)

                    discount = 0.00
                    if total_sin_descuento > 0:
                        discount=(float(descuento)/total_sin_descuento)
                    if discount > 1.00:
                        discount = 1.00
                    discount = discount * 100.00
                    purchase_order_line_id=False
                    if brw_each.invoice_type!="service":
                        product_id=dct_products.get(codigoPrincipal,False)
                    else:
                        product_id=brw_each.service_id.id
                    if move_type=="in_invoice":
                        if brw_each.order_id and product_id:
                            purchase_order_line_srch=self.env["purchase.order.line"].sudo().search([('order_id','=',brw_each.order_id.id),('product_id','=',product_id),('order_id.state','=','purchase')])
                            purchase_order_line_id=purchase_order_line_srch and purchase_order_line_srch[0].id or False
                    taxes_id=[(6,0,[])]
                    if codigoPorcentaje:
                        if not dct_taxes.get(codigoPorcentaje,False):
                            srch=self.env["account.tax"].sudo().search([('type_tax_use','=','purchase'),('l10n_ec_code_ats','=',codigoPorcentaje)])
                            if srch:
                                dct_taxes[codigoPorcentaje]=srch[0].id
                        taxes_id=[(6,0,dct_taxes.get(codigoPorcentaje,False) and [dct_taxes.get(codigoPorcentaje,False)] or [])] 
                    invoice_line_ids.append((0,0,{
                        "product_id":product_id,
                        "name":descripcion,
                        "quantity":float(cantidad),
                        "price_unit":float(precioUnitario),
                        "discount":discount,
                        "purchase_line_id":purchase_order_line_id,
                        "tax_ids":taxes_id,
                        "locked":True,
                        "imported_code":codigoPrincipal,
                        "imported_description":descripcion,
                        "imported_price":float(precioUnitario),
                        "imported_qty":float(cantidad)
                        }))
                    sequence+=1
                payments_info=variables["payments_info"]
                l10n_ec_sri_payment_id=False
                for each_payment in payments_info:
                    formaPago=each_payment["formaPago"]
                    src_payment = self.env["l10n_ec.sri.payment"].sudo().search([('code','=',formaPago)])
                    if src_payment:
                        l10n_ec_sri_payment_id=src_payment[0].id
                        continue
                vals["l10n_ec_sri_payment_id"] = l10n_ec_sri_payment_id
                vals["invoice_line_ids"]=invoice_line_ids
                brw_process_doc=OBJ_MOVE.create(vals)
                brw_each.write({"invoice_id":brw_process_doc.id})
        return  True
            
    def create_withhold(self):
        OBJ_WIZARD_WITTHOLD=self.env["l10n_ec.wizard.account.withhold"]
        OBJ_PARTNER=self.env["res.partner"].sudo()
        OBJ_JOURNAL=self.env["account.journal"].sudo()
        OBJ_MOVE=self.env["account.move"].sudo()
        OBJ_TAX=self.env["account.tax"].sudo()
        for brw_each in self:           
            if not brw_each.withhold_id:
                variables=brw_each.get_variables()
                fechaEmision=variables["fechaEmision"]
                documento=variables["documento"]
                ruc=variables["ruc"]
                claveAcceso=variables["claveAcceso"]
                withhold_line_values=variables["withhold_line_ids"]
                documento_relacionado=variables["documentoRelacionado"]
                srch_partner=OBJ_PARTNER.search([('vat','=',ruc)])
                if not srch_partner:
                    raise ValidationError(_("Cliente/Proveedor con ID %s no existe") % (ruc,))
                ####buscar retencion
                
                srch_journal=OBJ_JOURNAL.search([('type','=',"general"),('l10n_ec_withhold_type','=',"in_withhold")])
                if not srch_journal:
                    raise ValidationError(_("No hay un diario definido por defecto para retenciones de clientes"))
                srch_move=OBJ_MOVE.search([('partner_id','=',srch_partner[0].id),
                                           ('format_name','=',documento_relacionado),
                                           ('move_type','=','out_invoice'),
                                           ('state','=','posted')                                           
                                           ])
                if not srch_move:
                    raise ValidationError(_("No existe de factura de cliente %s para cliente con  id %s") % (documento_relacionado,ruc) )            
                related_invoice_ids=[(6,0,[srch_move[0].id])]
                vals={
                    "partner_id":srch_partner[0].id,
                    "date":None,#dtObj.strf(dtObj.parse(fechaEmision, "%d/%m/%Y"),"%Y-%m-%d"),
                    "journal_id":srch_journal[0].id,
                    "company_id":brw_each.company_id.id,
                    "currency_id":brw_each.company_id.currency_id.id,
                    "withhold_type":"in_withhold",
                    "document_number":documento,
                    "l10n_latam_document_type_id":brw_each.document_type_id.id,
                    "related_invoice_ids":related_invoice_ids,                    
                    "authorization_type":"electronica",
                    "external_number_authorization":claveAcceso  
                }
                withhold_line_ids=[(5,)]
                sequence=1
                for each_line in withhold_line_values:
                    tax_code=each_line["codigoRetencion"]
                    srch_tax=OBJ_TAX.search([('l10n_ec_code_ats','=',tax_code)])
                    if not srch_tax:
                        raise ValidationError(_("Impuesto con codigo %s no existe") % (tax_code,))
                    base_imponible=each_line["baseImponible"]
                    withhold_line_ids.append((0,0,{"company_id":brw_each.company_id.id,
                                                   "sequence":sequence,
                                                   "invoice_id":srch_move[0].id,
                                                   "tax_id":srch_tax[0].id,
                                                   "base":float(base_imponible)
                                                   }))
                    
                    sequence+=1                
                vals["withhold_line_ids"]=withhold_line_ids
                brw_process_doc=OBJ_WIZARD_WITTHOLD.create(vals)
                brw_process_doc.action_create_and_post_withhold()
                brw_each.write({"withhold_id":brw_process_doc.id})
            

    def get_edi_document_auth(self):
        return  self
        
        