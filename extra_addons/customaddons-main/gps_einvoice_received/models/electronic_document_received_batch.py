 # -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import AccessError, UserError, ValidationError, Warning
from odoo import api, fields, models, _
import html
import base64
import logging
_logger = logging.getLogger(__name__)

NO_JOBS=0
ERROR=1
COMMIT=2
NO_HANDLED=3

ALERT_TOP=100

from ...calendar_days.tools import CalendarManager
from ...calendar_days.tools import DateManager
from ...message_dialog.tools import FileManager
dateO=DateManager()
fileO=FileManager()
calendarO=CalendarManager()

class ElectronicDocumentReceivedBatch(models.Model):
    _name="electronic.document.received.batch"
    _description="Lote de Documentos recibidos"

    @api.model
    def get_default_name(self):
        return "CARGA DE DOCUMENTOS DEL DIA %s" % (fields.Date.today(),)
    
    def compute_has_pendings(self):
        for brw_each in self:
            has_pendings=False
#             if brw_each.state not in ('draft', 'annulled'):
#                 self._cr.execute("""select count(1) from
# document_received_batch_rel drl
# inner join electronic_document_received r on r.id=drl.document_id
# where drl.batch_id=%s  and r.state='updated'
# and r.withhold_id is null or r.invoice_id is null""",(brw_each.id,))
#                 result=self._cr.fetchone()
#                 has_pendings=(result and ((result[0])>0) or False)
            brw_each.has_pendings=has_pendings
    
    @api.model
    def get_default_year(self):
        return fields.Date.today().year
    
    @api.model
    def get_default_month_id(self):
        month=fields.Date.today().month
        srch=self.env["calendar.month"].sudo().search([('value','=',month)])
        return srch and srch[0].id or False

    company_id = fields.Many2one(
        "res.company",
        string="Compañia",
        required=True,
        copy=False,
        default=lambda self: self.env.company,
    )
    file=fields.Binary("Archivo",required=False)
    file_name=fields.Char("Nombre de Archivo",required=False,size=255)
    state=fields.Selection([('draft','Preliminar'),
                            ('started','Iniciado'),
                            ('in_progress','En progreso'),
                            ('ended','Finalizado'),
                            ('annulled','Anulado')],string="Estado",required=True,default="draft")
    name=fields.Char("Lote de Documentos Recibidos",size=255,required=True,default=get_default_name)
    date=fields.Date("Fecha de Registro",required=True,default=fields.Date.today())
    comments=fields.Text("Comentarios")
    document_ids=fields.Many2many("electronic.document.received",
                                  "document_received_batch_rel",
                                  "batch_id",
                                  "document_id",
                                  "Lote de Documentos")
    # history_ids=fields.One2many("electronic.document.received.batch.history","parent_id","historial")
    has_pendings=fields.Boolean("Tiene pendientes?",compute="compute_has_pendings",default=False)
    year=fields.Integer("Año",required=True,default=get_default_year)
    month_id=fields.Many2one("calendar.month","Mes",required=True,default=get_default_month_id)
    
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        brw_new=super(ElectronicDocumentReceivedBatch,self).create(vals)
        brw_new.validate_period()
        #OBJ_HISTORY=self.env["electronic.document.received.batch.history"]
        #OBJ_HISTORY.register(brw_new.id,_("REGISTRO CREADO" ),brw_new.state)
        return brw_new
    
    @api.returns('self', lambda value:value.id)
    def copy(self, default=None):
        raise ValidationError(_("No puedes duplicar este documento"))
    
    def write(self, vals):       
        value= super(ElectronicDocumentReceivedBatch,self).write(vals)
        for brw_each in  self:
            brw_each.validate_period()
        return value
    
    def validate_period(self):
        OBJ_PARAM=self.env['ir.config_parameter'].sudo() 
        months=int(OBJ_PARAM.get_param('time.enable.state.sri','1') )
        for brw_each in  self:
            YEAR=brw_each.year
            MONTH=brw_each.month_id.value
            # date_validate=dateO.create(YEAR,MONTH,1).date()
            # today=dateO.parse(dateO.now()).date()
            # if(date_validate>today):
            #     raise ValidationError(_("No puedes crear un registro con un periodo mayor al mes y año de la fecha actual"))
            # date_min_validated=dateO.addMonths(today,-months)
            # date_min_validated=dateO.create(date_min_validated.year,date_min_validated.month,1).date()
            # if(date_validate>today):
            #     raise ValidationError(_("No puedes crear un registro con un periodo mayor al mes y año de la fecha actual"))
            # if(date_validate<date_min_validated):
            #     raise ValidationError(_("No puedes actualizar registros con un periodo menor a los meses permitidos de la fecha actual: %s") % (months,))
        return True
    
    def unlink(self):
        for brw_each in self:
            if brw_each.state!="draft":
                raise ValidationError(_("No puedes borrar un registro que no sea preliminar"))
        value= super(ElectronicDocumentReceivedBatch,self).unlink()
        return value
    
    @api.onchange('name')
    def onchange_name(self):
        self.name=(self.name and self.name.upper() or None)
    
    @api.onchange('comments')
    def onchange_comments(self):
        self.comments=(self.comments and self.comments.upper() or None)
    
    @api.model
    def create_document(self,access_key,brw_each,identification,partner_name,document_ids):
        OBJ_DOCUMENT=self.env["electronic.document.received"]
        if access_key:
            document_srch=OBJ_DOCUMENT.search([('access_key','=',access_key)])
            if not document_srch:
                document_srch=OBJ_DOCUMENT.create({
                                        "company_id":brw_each.company_id.id,
                                        "state":"draft",
                                        "identification":identification,
                                        "partner_name":partner_name,
                                        "name":"%s - %s" % (identification,partner_name),
                                        "access_key":access_key
                                        })
                document_ids.append(document_srch.id)
            else:
                document_ids.append(document_srch.id)
        return document_ids
                
    def process_text(self,ext,brw_each,document_ids):
        if ext not in ("txt",):
            raise ValidationError(_("Extension no soportada para procesar el archivo"))
        file_content=(base64.decodebytes(brw_each.file))
        lines = str(file_content).split('\\n')
        for line in lines:
            row = str(line).split('\\t')
            if len(row)>=12:
                identification=""
                partner_name=""
                access_key=False
                try:
                    identification=str(row[0])
                    partner_name=html.unescape((str(row[1])).upper())
                    access_key=row[4]
                    if(len(access_key)!=49):###es clave de acceso no un tag
                        continue
                except:
                    pass
                self.create_document(access_key, brw_each, identification, partner_name, document_ids)
        return document_ids
        
    def process_file(self):
        #OBJ_HISTORY=self.env["electronic.document.received.batch.history"]
        for brw_each in self:
            brw_each.document_ids = [(6,0,[])]
            document_ids=[]                            
            try:
                ext="txt"#fileO.get_ext(brw_each.file_name)
                PROCESS_MAP={
                    "txt":self.process_text
                }
                document_ids=PROCESS_MAP[ext](ext,brw_each,document_ids)
                if document_ids:
                    brw_each.write({"document_ids":[(6,0,document_ids)],
                                    "state":"started"})                
                #OBJ_HISTORY.register(brw_each.id,_("REGISTROS RECUPERADOS %s REGISTRO(S)" ) % (len(document_ids),),brw_each.state)
            except Exception as e:
                raise ValidationError(_("Error al procesar el archivo:\n\n" + str(e)))                      
        return True
    
    def action_recover(self):
        #OBJ_HISTORY=self.env["electronic.document.received.batch.history"]
        for brw_each in self:
            if brw_each.state== "ended":
                raise ValidationError(_("Lote de documentos ya procesado"))
            brw_each.write({"state":"in_progress"}) 
            #OBJ_HISTORY.register(brw_each.id,_("INICIO DE RECUPERACION DE REGISTROS" ),"in_progress")
            if brw_each.document_ids:
                MAX_COUNT=len(brw_each.document_ids)
                log_message="%s REGISTROS POR RECUPERAR DEL SRI..." % (MAX_COUNT,)
                _logger.warning(log_message)
                i=0            
                for brw_document in brw_each.document_ids:
                    if brw_document.state not in ("updated", "annulled"):
                        try:
                            brw_document.action_recover()
                            if i>=ALERT_TOP:
                                if(MAX_COUNT-i)>0:
                                    MAX_COUNT=(MAX_COUNT-i)
                                log_message="FALTAN %s REGISTROS POR RECUPERAR DEL SRI." % (MAX_COUNT,)
                                _logger.warning(log_message)
                                i=0  
                        except Exception as e:
                            _logger.warning("ERROR AL RECUPERAR DEL SRI EN %s" % (str(e),))
                        finally:
                            i+=1
                log_message="NO HAY REGISTROS POR RECUPERAR DEL SRI!!."
                _logger.warning(log_message)  
                document_ids=brw_each.document_ids.ids
                document_ids+=[-1,-1]
                srch_document_ids=self.env["electronic.document.received"].search([('state','not in',('updated',"annulled")),('id','in',tuple(document_ids))])
                if not srch_document_ids:
                    brw_each.write({"state":"ended"}) 
                    #OBJ_HISTORY.register(brw_each.id,_("NO HAY DOCUMENTOS POR RECUPERAR" ),"ended")
                else:
                    pass#OBJ_HISTORY.register(brw_each.id,_("EXISTEN DOCUMENTO(S) POR RECUPERAR" ),brw_each.state)
        return True 
            
    def action_cancel(self):
        OBJ_HISTORY=self.env["electronic.document.received.history.batch"]
        for brw_each in self: 
            brw_each.write({"state":"annulled"})
            if brw_each.document_ids:
                document_ids=brw_each.document_ids.ids
                document_ids+=[-1,-1]
                srch_document_ids=self.env["electronic.document.received"].search([('state','not in',('updated',"annulled")),('id','in',tuple(document_ids))])
                if srch_document_ids:
                    brw_each.write({"state":"annulled"})    
                    OBJ_HISTORY.register(brw_each.id,_("REGISTRO ANULADO" ),"annulled")             
        return True
    
    def update_documents(self):
        for brw_each in self:
            self.update_states_sri_by_period(brw_each.month_id,brw_each.year)
        return True
    
    @api.model
    def update_states_sri_by_period(self,brw_month,year,not_related=True):
        YEAR=year
        MONTH=brw_month.value
        LAST_DAY=calendarO.days(YEAR,MONTH)
        date_from=dateO.create(YEAR,MONTH,1).date() 
        date_to=dateO.create(YEAR,MONTH,LAST_DAY).date() 
        self.update_states_sri(date_from=date_from,date_to=date_to,not_related=not_related)
        return self.env["electronic.document.received"].sudo().update_received_documents_states()
    
    @api.model
    def update_states_sri(self,date_from=None,date_to=None,not_related=True):
        QUERY="""select x.id,x.id 
from electronic_document_received x 
where x.state!='annulled' and x.state_sri!='annulled' """
        if date_from is not None:
            QUERY+=" and x.date>='%s' " % (dateO.strf(date_from),)
        if date_to is not None:
            QUERY+=" and x.date<='%s' " % (dateO.strf(date_to),)
        if not_related:
            QUERY+=" and (x.invoice_id is null and x.withhold_id is null ) " 
        QUERY+=" order by x.date asc "
        self._cr.execute(QUERY)
        result=self._cr.fetchall()
        list_document_ids=result and list(dict(result).keys()) or []
        list_document_ids+=[-1,-1]
        srch_document_ids=self.env["electronic.document.received"].sudo().search([('id','in',tuple(list_document_ids))])
        if srch_document_ids:            
            MAX_COUNT=len(srch_document_ids)
            log_message="%s REGISTROS POR RECUPERAR ESTADO DEL SRI..." % (MAX_COUNT,)
            _logger.warning(log_message)
            i=0
            for brw_document in srch_document_ids:
                try:                    
                    brw_document.action_recover_state_sri()
                    if i>=ALERT_TOP:
                        if(MAX_COUNT-i)>0:
                            MAX_COUNT=(MAX_COUNT-i)
                        log_message="FALTAN %s REGISTROS POR RECUPERAR ESTADO DEL SRI." % (MAX_COUNT,)
                        _logger.warning(log_message)
                        i=0                                   
                except Exception as e:
                    _logger.warning(str(e))
                finally:
                    i+=1
            log_message="NO HAY REGISTROS POR RECUPERAR ESTADO DEL SRI!!."
            _logger.warning(log_message)                    
        return True
            
    _order="id desc"