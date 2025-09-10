# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models,api
import logging
_logger = logging.getLogger(__name__)

INVOICE_TYPE_LIST=[('service','Servicio')]#,('inventory','Inventario')

class ElectronicDocumentReceivedWorkflowWizard(models.TransientModel):
    _inherit="workflow.wizard"   
    _name="electronic.document.received.workflow.wizard"
    _description="Asistente de Workflow de Movimientos de Inventarios"
    
    @api.model
    def get_selection_state(self):
        return [('draft','Preliminar'),('updated','Actualizada'),('error','Error'),('annulled','Anulado')]
    
    @api.model
    def get_default_state(self):
        if "default_state" in self._context:
            return self._context["default_state"]
        active_ids=self._context.get("active_ids",[])
        if not active_ids:
            return None
        return self.env["electronic.document.received"].sudo().browse(active_ids[0]).state
    
    @api.model
    def get_default_confirmed_state(self):
        if "default_confirmed_state" in self._context:
            return self._context["default_confirmed_state"]
        return None

    @api.model
    def get_default_company_id(self):
        if "active_ids" in self._context:
            brw_active=self.env["electronic.document.received"].sudo().browse(self._context["active_ids"])
            return brw_active and brw_active.company_id.id or False
        return False

    state=fields.Selection(selection =get_selection_state,string="Estado",default=get_default_state,required=False)
    confirmed_state=fields.Selection([('received','Recibido'),
                                      ('rejected','Rechazado'),
                                      ('verified','Verificado'),
                                      ('confirmed','Confirmado')],string="Recepción",required=False,default=get_default_confirmed_state)
    
    comments=fields.Text("Comentarios")
    company_id=fields.Many2one("res.company","Compania",default=get_default_company_id)
    
    @api.model
    def get_default_document_code(self):
        active_ids=self._context.get("active_ids",[])
        if not active_ids:
            return None
        return self.env["electronic.document.received"].sudo().browse(active_ids[0]).document_type_id.code
    
    @api.model
    def get_default_partner_id(self):
        active_ids=self._context.get("active_ids",[])
        if not active_ids:
            return False
        brw_received=self.env["electronic.document.received"].sudo().browse(active_ids[0])
        if brw_received.partner_id:
            return brw_received.partner_id.id
        srch_partner=self.env["res.partner"].sudo().search([('vat','=',brw_received.identification)])
        if not srch_partner:
            return False
        brw_received.write({"partner_id":srch_partner[0].id})
        return srch_partner[0].id
        
    document_code=fields.Selection([('01','Factura'),('04','Nota de Credito'),('07','Retencion')],string="Codigo de Documento",default=get_default_document_code)
    order_id=fields.Many2one("purchase.order","# Orden")    
    partner_id=fields.Many2one("res.partner","Emisor",default=get_default_partner_id)
    invoice_type=fields.Selection(INVOICE_TYPE_LIST,default="service",string="Tipo Fact/NC",required=True)
    service_id=fields.Many2one("product.product","Servicio por Defecto",domain=[('detailed_type','=','service')])
    
    
    def process(self):
        INVOICE_TYPE_DSCR=dict(INVOICE_TYPE_LIST)
        OBJ_PROCESS=self.env["electronic.document.received"]
        if(self._context.get("active_ids",False)):
            for brw_each in self:
                for brw_process in OBJ_PROCESS.browse(self._context["active_ids"]):
                    if not self._context.get("only_update",False):
                        to_state=(brw_each.state is None) and brw_process.state or brw_each.state
                        confirmed_state=(brw_each.confirmed_state is None)  and brw_process.confirmed_state or brw_each.confirmed_state                        
                        brw_process.update_workflow(brw_each.comments, to_state,confirmed_state=confirmed_state,order_id=brw_each.order_id and brw_each.order_id.id or False)                  
                    else:
                        vals={}
                        comments=brw_each.comments and brw_each.comments or ""
                        if brw_each.document_code== "01":
                            vals={#"order_id":brw_each.order_id and brw_each.order_id.id or False,
                                  "invoice_type":brw_each.invoice_type,
                                  "service_id":brw_each.service_id and brw_each.service_id.id or False
                                  }
                            comments="%s: %s" % (brw_each.comments,"ORDEN %s,TIPO FACT/NC: %s,SERVICIO POR DEFECTO:%s" % (brw_each.order_id and brw_each.order_id.name or "",INVOICE_TYPE_DSCR[brw_each.invoice_type],brw_each.service_id and brw_each.service_id.name or ""))
                        if brw_each.document_code== "04":
                            vals={"invoice_type":brw_each.invoice_type,
                                  "service_id":brw_each.service_id and brw_each.service_id.id or False
                                  }
                            comments="%s: %s" % (brw_each.comments,"TIPO FACT/NC: %s,SERVICIO POR DEFECTO:%s" % (INVOICE_TYPE_DSCR[brw_each.invoice_type],brw_each.service_id and brw_each.service_id.name or ""))
                        vals["last_msg"]=comments
                        brw_process.write(vals)#actualiza estado
                        #self.env["electronic.document.received.history"].register(brw_process.id,comments,brw_process.state)
        return True
