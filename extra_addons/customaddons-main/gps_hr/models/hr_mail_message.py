# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_, SUPERUSER_ID
import base64

class HrMailMessage(models.Model):    
    _name="hr.mail.message"
    _description="Mensajes de Nomina"
    
    internal_type=fields.Selection([('batch','Lote'),('process','Manual')],string="Tipo Envio",default="batch")
    type=fields.Selection([('payslip','Rol'),],string="Tipo",default="payslip")
    name=fields.Char(string="PK",required=True)
    internal_id=fields.Integer(required=True,string="ID Interno")
    model_name=fields.Char(string="Modelo",required=True)
    description=fields.Char(string="Descripcion",required=True)
    email=fields.Char(string="Correo",required=False)

    employee_id=fields.Many2one("hr.employee",string="Empleado")
    company_id=fields.Many2one("res.company",string="Compañia")

    last_message_email=fields.Text(string="Ult. Mensaje Envio")
    last_message_date=fields.Datetime(string="Ult. Fecha Envio")
    
    state=fields.Selection([('draft','Preliminar'),('send','Enviado'),('error','Error'),('annulled','Anulado')],string="Estado",default="draft")

    message_id=fields.Many2one("mail.mail",string="Mensaje de Correo")
    template_id=fields.Many2one("mail.template",string="Plantilla")
    report_name_ref=fields.Char(string="# Ref Reporte")

    def get_mail_to_send(self):
        self.ensure_one()
        brw_each=self
        OBJ_PARAM = self.env['ir.config_parameter'].sudo() 
        mail_test_enable=OBJ_PARAM.get_param("mail.test.rrhh.enable","True")
        mail_send=brw_each.email
        if mail_test_enable in ("True","1"):
            mail_send=OBJ_PARAM.get_param("mail.test.rrhh",False)
            if not mail_send:
                mail_send=brw_each.email
        return mail_send

    def get_object_browse(self):
        self.ensure_one()
        brw_each =self
        return self.env[brw_each.model_name].sudo().browse(brw_each.internal_id)

    def send_mail(self):
        for brw_each in  self:
            template = brw_each.template_id
            model_obj=self.env[brw_each.model_name].sudo().browse(brw_each.internal_id)
            ctx = dict(
                default_model=brw_each._name,
                default_res_id=brw_each.id,
                default_use_template=bool(template),
                default_template_id=template and template.id or False,
                default_composition_mode='comment',
                model_obj=model_obj
            )
            if brw_each.company_id:
                srch_mail_server=self.env["ir.mail_server"].sudo().search([('active','=',True),
                                                                      ('smtp_user','=',brw_each.company_id.email)
                                                                      ])
                if srch_mail_server:
                    ctx["default_mail_server_id"]=srch_mail_server[0].id
            email_values=None
            if brw_each.report_name_ref:
                email_values={}
                res_ids=[model_obj.id]
                data={}
                report_template = self.env.ref(brw_each.report_name_ref)

                context = {
                    'lang': 'es_ES',  # Si quieres establecer un idioma específico
                }
                report_template= report_template.with_context(context)
                pdf= self.env["ir.actions.report"]._render(report_template, res_ids, data=data)


                report_pdf,pdf_name = pdf

                # Convert PDF content to base64
                pdf_base64 = base64.b64encode(report_pdf)
                #rint(pdf)
                email_values["attachments"]=[("%s.%s" % (brw_each.description,pdf_name), pdf_base64)]
            template=template.with_context(ctx)
            message_id=template.send_mail(brw_each.id,force_send=True,email_values=email_values)
            brw_each.write({"message_id":message_id})
            if brw_each.message_id:
                if brw_each.message_id.state in ("sent","received"):
                    brw_each.write({"state":"send","last_message_email":"OK","last_message_date":fields.Datetime.now()})
                if brw_each.message_id.state in ("exception",):
                    brw_each.write({"state":"error","last_message_email":brw_each.message_id.failure_reason or '',"last_message_date":fields.Datetime.now()})
        return True
    
    def action_cancel(self):
        for brw_each in  self:
            brw_each.write({"state":"annulled"})
        return True

    @api.model
    def send_all_pendings(self,limit,order,domain):
        new_domain=domain+[('email','!=',False),('email','!=',None),('email','ilike',"@"),('state','not in',('annulled','send'))]#se omite error
        srch=self.env["hr.mail.message"].sudo().search(new_domain,order=order,limit=limit)
        if srch:
            try:
                for brw_each in srch:
                    brw_each.send_mail()
                    self._cr.commit()
            except Exception as e:
                    result=(str(e))
        ###########################################
        new_domain=domain+[('state','in',('draft',)),'|','|','|',('email','=',''),('email','=',False),('email','=',None),('email','not ilike',"@")]#se omite error
        srch=self.env["hr.mail.message"].sudo().search(new_domain,order=order,limit=limit)
        if srch:
            try:
                for brw_each in srch:
                    brw_each.write({"state":"annulled","last_message_email":'NO HAY UN CORREO CONFIGURADO O CORREO VALIDO',"last_message_date":fields.Datetime.now()})
                    self._cr.commit()
            except Exception as e:
                    result=(str(e))

    _order = "id desc"

    _check_company_auto = True
    