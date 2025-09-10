# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _,SUPERUSER_ID
import base64
from xml.etree.ElementTree import Element, SubElement, tostring
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager
fileO=FileManager()        
dateO=DateManager()
calendarO=CalendarManager()

class l10n_ec_ats(models.TransientModel):
    _name = "l10n.ec.ats"
    _description = "ATS"
    
    @api.model
    def get_default_company_id(self):
        if self._context.get("allowed_company_ids", []):
            return self._context.get("allowed_company_ids", [])[0]
        return self.env["res.users"].browse(self._uid).company_id.id
    
    @api.model
    def get_default_year(self):
        return fields.Date.today().year
    
    @api.model
    def get_default_month_id(self):
        month=fields.Date.today().month
        srch=self.env["calendar.month"].sudo().search([('value','=',month)])
        return srch and srch[0].id or False
    
    company_id=fields.Many2one("res.company","Compañia",default=get_default_company_id)
    report_file = fields.Binary(copy=False, )
    file_name = fields.Char(copy=False, )
    type_report = fields.Selection([('ATS', '(ATS) ANEXO TRANSACCIONAL SIMPLIFICADO')],default='ATS', copy=False)
    year=fields.Integer("Año",default=get_default_year)
    month_id=fields.Many2one("calendar.month","Mes",required=True,default=get_default_month_id)

    type_info=fields.Selection([('detailed','Detallado'),('grouped','Agrupado')],string="Tipo de Reporte",default="grouped")

    @api.model
    def get_default_date_start(self):
        if self._context.get("is_report",False):
            NOW=fields.Date.today()
            YEAR=NOW.year
            MONTH=NOW.month      
            return dateO.create(YEAR,MONTH, 1).date()
        return None
    
    @api.model
    def get_default_date_end(self):
        if self._context.get("is_report",False):
            NOW=fields.Date.today()
            YEAR=NOW.year
            MONTH=NOW.month        
            LAST_DAY=calendarO.days(YEAR,MONTH)
            return dateO.create(YEAR,MONTH,LAST_DAY).date()
        return None
    
    date_start=fields.Date("Fecha Inicial",required=True,store=True,readonly=False,default=get_default_date_start)
    date_end=fields.Date("Fecha Final",required=True,store=True,readonly=False,default=get_default_date_end)
    
    @api.onchange('year','month_id')
    def onchange_year_month(self):
        YEAR=self.year
        MONTH=self.month_id.value
        
        LAST_DAY=calendarO.days(YEAR,MONTH)
        self.date_start=dateO.create(YEAR,MONTH,1).date() 
        self.date_end=dateO.create(YEAR,MONTH,LAST_DAY).date() 
        
        
    def process(self):
        if self.type_report == 'ATS':
            file = self.ATS(self.date_start, self.date_end)
            file_name = str(self.type_report)+".xml"

            self.report_file = file
            self.file_name = file_name
            return {
                         'type' : 'ir.actions.act_url',
                         'url': '/web/content/%s/%s/report_file/%s' % (self._name,self.id,file_name),
                         'target': 'new'
                }

    # region ATS
    def ATS(self, date_from, date_to):
        config = self.env['ir.config_parameter'].sudo()
        company_id = self.env.user.company_id

        root = Element("iva")
        SubElement(root, "TipoIDInformante").text = 'R'
        SubElement(root, "IdInformante").text = company_id.vat
        SubElement(root, "razonSocial").text = self.xmlGen(company_id.name.replace('.', '')).upper()
        SubElement(root, "Anio").text = str(date_to.year)
        SubElement(root, "Mes").text = str(date_to.month).zfill(2)
        str_date_from = str(date_from.year) + "-" + str(date_from.month).zfill(2) + "-" + str(date_from.day).zfill(2)
        str_date_to = str(date_to.year) + "-" + str(date_to.month).zfill(2) + "-" + str(date_to.day).zfill(2)

        sql = """
            select substring(right(replace(t0.name,'-',''),15) from 1 for 3) codEstab, 
            COUNT(1)
            from account_move t0
            inner join l10n_latam_document_type t1 on t1.id = t0.l10n_latam_document_type_id 
            where t0.state in ('posted', 'paid')
            and t0.move_type in ('out_invoice', 'out_refund') 
           and t0.invoice_date<='"""+str_date_to+"""' and t1.code!='00' 
            group by substring(right(replace(t0.name,'-',''),15) from 1 for 3)    
            order by substring(right(replace(t0.name,'-',''),15) from 1 for 3)  desc        
        """#
        self.env.cr.execute(sql)
        result=self.env.cr.fetchall()
        SubElement(root, "numEstabRuc").text = str(len(result)).zfill(3)             
        SubElement(root, "totalVentas").text = "0.00"        
        SubElement(root, "codigoOperativo").text = "IVA"
        
        self._generate_compras(root, date_from, date_to)
        self._generate_ventas(root, date_from, date_to)
        


        self._generate_ventasEstablecimiento(root, date_from, date_to)
        self._generate_anulados(root, date_from, date_to)

        report = tostring(root, encoding="UTF-8")
        return base64.b64encode(report)

    def _generate_ventas_general(self, root, date_from, date_to):
        company_id = self.env.user.company_id
        str_date_from = str(date_from.year) + "-" + str(date_from.month).zfill(2) + "-" + str(date_from.day).zfill(2)
        str_date_to = str(date_to.year) + "-" + str(date_to.month).zfill(2) + "-" + str(date_to.day).zfill(2)

        sql = """
                        select 
                'ventas'::VARCHAR tipo,
                rp.vat as idinformante,
                rp.name razonsocial,
                '001'::VARCHAR numestabruc,
                'NA'::VARCHAR::VARCHAR totalventas,
                'iva'::VARCHAR codigooperativo,
                case when(rp.vat='9999999999999') then '07'
                    else l10n_latam_identification_type.l10n_ec_code
                end as ventas_tpidcliente,
                res_partner.vat as ventas_idcliente,
                'NO'::VARCHAR ventas_parterel,
                case when res_partner.is_company='f' then '01' else '02' end ventas_tipocliente,                
                case when doc_document_type.code='01' then '18' else doc_document_type.code end ventas_tipocomprobante,
                'E' ventas_tipoem,
                count(1) ventas_numerocomprobantes,
                0.00 as ventas_valorretiva,
                0.00 as ventas_valorretrenta,
                CAST('01' AS VARCHAR ) ventas_formapago,
                CAST('' AS VARCHAR ) ventas_codestab,
                0.00 as ventas_ventasestab,
                'NA'::VARCHAR ventas_ivacomp,
                sum(account_move.amount_base0) as   ventas_basenograiva,
                sum(account_move.amount_baseno0) as   ventas_baseimponible,
                sum(account_move.amount_tax0) as   ventas_baseimpgrav,
                sum(account_move.amount_taxno0) as  ventas_montoiva,
                'NA'::VARCHAR ventas_tipocompe,
                0 ventas_monto,
                0 ventas_montoice
                
                from res_company 
                inner join res_partner rp  on rp.id=res_company.partner_id 
                inner join account_move on account_move.company_id = res_company.id and account_move.move_type in ('out_invoice','out_refund') and account_move.state in ('posted','paid') 
                and coalesce(account_move.anulado_sri,false)!=true 
                left join res_partner on account_move.partner_id = res_partner.id
                left join l10n_latam_identification_type on res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
                left join l10n_ec_sri_payment doc_payment_type on doc_payment_type.id = account_move.l10n_ec_sri_payment_id 
                left join l10n_latam_document_type doc_document_type on doc_document_type.id = account_move.l10n_latam_document_type_id 
                where account_move.invoice_date>='%s' and account_move.invoice_date<='%s' and account_move.company_id=%s and doc_document_type.code!='00'  
group by        rp.vat,
                rp.name ,
                case when(rp.vat='9999999999999') then '07'
                    else l10n_latam_identification_type.l10n_ec_code end,
                res_partner.vat,
                case when res_partner.is_company='f' then '01' else '02' end ,                
                case when doc_document_type.code='01' then '18' else doc_document_type.code end 
                
        """ % (str_date_from,str_date_from,company_id)

        self.env.cr.execute(sql)
        result = self.env.cr.dictfetchall()
        totalVentas = 0
        for line in result:
            totalVentas = line['ventas_ventasestab']
        SubElement(root, "totalVentas").text = '%.2f' % float(totalVentas)
        SubElement(root, "codigoOperativo").text = "IVA"
        return root

    def _generate_compras(self, root, date_from, date_to):
        str_date_from = str(date_from.year) + "-" + str(date_from.month).zfill(2) + "-" + str(date_from.day).zfill(2)
        str_date_to = str(date_to.year) + "-" + str(date_to.month).zfill(2) + "-" + str(date_to.day).zfill(2)
        company_id = self.env.user.company_id
        

        sql = """;with variables as (
    select '%s'::date as fecha_inicial,
    '%s'::date as fecha_final    ,
	%s::int as company_id   

),
retenciones_detalle as (
                select account_move.id,
                    sum(aml.l10n_ec_withhold_tax_amount) as total,
                    atxg.l10n_ec_type,
    round(abs(atx.amount),2) as percent_tax 
                from res_company 
                inner join variables on res_company.id=variables.company_id 
                inner join res_partner rp  on rp.id=res_company.partner_id
                inner join account_move on account_move.company_id = res_company.id and account_move.move_type in ('in_invoice') and account_move.state in ('posted','paid')  and 
                account_move.invoice_date>=variables.fecha_inicial and account_move.invoice_date<=variables.fecha_final
                
                inner join account_journal aj on  aj.id=account_move.journal_id and coalesce(aj.l10n_latam_use_documents,false)=true 
                
                inner join account_move_line aml on aml.l10n_ec_withhold_invoice_id=account_move.id 
                inner join account_move_line_account_tax_rel atxrl on atxrl.account_move_line_id=aml.id 
                inner join account_tax atx on atx.id=  atxrl.account_tax_id 
                inner join account_tax_group atxg on atxg.id=atx.tax_group_id
                inner join account_move awt on awt.id=aml.move_id and awt.state in ('posted','paid')  and coalesce(awt.anulado_sri,false)!=true 
                where aml.l10n_ec_withhold_tax_amount>0.00
                group by     account_move.id        ,atxg.l10n_ec_type,round(abs(atx.amount),2)
),retenciones_detalle_retencion as (
                select account_move.id as move_id,
                    awt.name,awt.invoice_date as fechaemiret1,
    awt.l10n_ec_authorization_number as autretencion1,
    left(right(replace(awt.nAME,'-',''),15),3) as estabretencion1,
                left(right(replace(awt.nAME,'-',''),12),3) as ptoemiretencion1,
                right(replace(awt.nAME,'-',''),9) as secretencion1,
     json_agg(json_build_object('valretair',aml.l10n_ec_withhold_tax_amount,
                                  'porcentajeair',round(abs(atx.amount),2),
                               'baseimpair', aml.balance,
                               'codretair', atx    .l10n_ec_code_base 
))  as detalle
    
                from res_company 
               inner join variables on res_company.id=variables.company_id 
                inner join res_partner rp  on rp.id=res_company.partner_id
                inner join account_move on account_move.company_id = res_company.id and account_move.move_type in ('in_invoice') and account_move.state in ('posted','paid')  and 
                account_move.invoice_date>=variables.fecha_inicial and account_move.invoice_date<=variables.fecha_final
                
                inner join account_journal aj on  aj.id=account_move.journal_id and coalesce(aj.l10n_latam_use_documents,false)=true 
                
                inner join l10n_latam_document_type doc_document_type on doc_document_type.id = account_move.l10n_latam_document_type_id 
                
                
                inner join account_move_line aml on aml.l10n_ec_withhold_invoice_id=account_move.id 
                inner join account_move_line_account_tax_rel atxrl on atxrl.account_move_line_id=aml.id 
                inner join account_tax atx on atx.id=  atxrl.account_tax_id and atx.l10n_ec_code_base!='731' 
                inner join account_tax_group atxg on atxg.id=atx.tax_group_id
                inner join account_move awt on awt.id=aml.move_id and awt.state in ('posted','paid')  
                where aml.l10n_ec_withhold_tax_amount>0.00 and doc_document_type.code!='00'  
              group by   account_move.id,
                  awt.name,awt.invoice_date,
awt.l10n_ec_authorization_number
)


select 

                case  when(l10n_latam_identification_type.l10n_ec_code='04') then '01'  
                   when(l10n_latam_identification_type.l10n_ec_code='05') then '02' 
                   when(l10n_latam_identification_type.l10n_ec_code='06') then '03' else '03' 
                end as compras_tpidprov, 
                res_partner.vat as compras_idprov,
                res_partner.name as compras_nombreprov,
                'NO'::VARCHAR compras_parterel,
                account_move.l10n_ec_code_taxsupport as compras_codsustento,
                left(right(replace(account_move.nAME,'-',''),15),3) as compras_establecimiento,
                left(right(replace(account_move.nAME,'-',''),12),3) as compras_puntoemision,
                right(replace(account_move.nAME,'-',''),9) as compras_secuencial,
                account_move.invoice_date as compras_fechaemision,
                account_move.l10n_ec_authorization_number as compras_autorizacion,
                case when res_partner.is_company='f' then '01' else '02' end compras_tipoproveedor,                
                doc_document_type.code as  compras_tipocomprobante,
                case when (account_move.authorization_type='electronica') then 'E' else 'F' end compras_tipoem,
                Coalesce(doc_payment_type.code,'01') as compras_formapago,
                0.00 as   compras_basenograiva,
                coalesce(account_move.amount_base0,0.00) as   compras_baseimponible,
                coalesce(account_move.amount_baseno0,0.00) as   compras_baseimpgrav,
                coalesce(account_move.amount_tax,0.00) as  compras_montoiva,                
                0.00 as  compras_baseimpexe,
                'NA'::VARCHAR compras_tipocompe,
                0.00 as compras_montoice,
                coalesce(rdiva10.total,0.00) AS compras_valretbien10,
                coalesce(rdiva20.total,0.00) AS compras_valretserv20,
                coalesce(rdiva30.total,0.00) AS compras_valorretbienes,
                coalesce(rdiva50.total,0.00) AS compras_valretserv50,
                coalesce(rdiva70.total,0.00) AS compras_valorretservicios,
                coalesce(rdiva100.total,0.00) AS compras_valretserv100   ,
                dtr.fechaemiret1,
                dtr.autretencion1,
                dtr.estabretencion1,
                dtr.ptoemiretencion1,
                dtr.secretencion1,
                dtr.autretencion1  ,
                dtr.detalle,
                left(right(replace(account_move.manual_document_number,'-',''),15),3) as compras_estabmodificado,
                left(right(replace(account_move.manual_document_number,'-',''),12),3) as compras_ptoemimodificado,
                right(replace(account_move.manual_document_number,'-',''),9) as compras_secmodificado,
                case when(account_move.manual_document_number is null)  then null  else '01' end as compras_docmodificado,
                account_move.manual_origin_authorization  as compras_autmodificado                 
                from res_company 
                inner join variables on res_company.id=variables.company_id 
                inner join res_partner rp  on rp.id=res_company.partner_id 
                inner join account_move on account_move.company_id = res_company.id and account_move.move_type in ('in_invoice','in_refund') and account_move.state in ('posted','paid')  and 
                account_move.invoice_date>=variables.fecha_inicial and account_move.invoice_date<=variables.fecha_final 
                inner join account_journal aj on  aj.id=account_move.journal_id and coalesce(aj.l10n_latam_use_documents,false)=true  
                inner join res_partner on account_move.partner_id = res_partner.id
                inner join l10n_latam_identification_type on res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
                inner join l10n_ec_sri_payment doc_payment_type on doc_payment_type.id = account_move.l10n_ec_sri_payment_id 
                inner join l10n_latam_document_type doc_document_type on doc_document_type.id = account_move.l10n_latam_document_type_id 
                left join retenciones_detalle rdiva10 on rdiva10.id=account_move.id and rdiva10.l10n_ec_type='withhold_vat_purchase' and  rdiva10.percent_tax=10.00 
                left join retenciones_detalle rdiva20 on rdiva20.id=account_move.id and rdiva20.l10n_ec_type='withhold_vat_purchase' and  rdiva20.percent_tax=20.00 
                left join retenciones_detalle rdiva30 on rdiva30.id=account_move.id and rdiva30.l10n_ec_type='withhold_vat_purchase' and  rdiva30.percent_tax=30.00                 
                left join retenciones_detalle rdiva50 on rdiva50.id=account_move.id and rdiva50.l10n_ec_type='withhold_vat_purchase' and  rdiva50.percent_tax=50.00 
                left join retenciones_detalle rdiva70 on rdiva70.id=account_move.id and rdiva70.l10n_ec_type='withhold_vat_purchase' and  rdiva70.percent_tax=70.00 
                left join retenciones_detalle rdiva100 on rdiva100.id=account_move.id and rdiva100.l10n_ec_type='withhold_vat_purchase' and  rdiva100.percent_tax=100.00 
                left join retenciones_detalle rdfte on rdfte.id=account_move.id and rdfte.l10n_ec_type='withhold_income_purchase'
                left join retenciones_detalle_retencion dtr on dtr.move_id=account_move.id 
                where doc_document_type.code!='00'                  
                """ % (date_from,date_to,company_id.id)

        self.env.cr.execute(sql)
        result = self.env.cr.dictfetchall()
        if result:
            compras = SubElement(root, "compras")        
            for line in result:
                detalleCompras = SubElement(compras, "detalleCompras")
                SubElement(detalleCompras, "codSustento").text = line['compras_codsustento']
                SubElement(detalleCompras, "tpIdProv").text = line['compras_tpidprov']
    
                SubElement(detalleCompras, "idProv").text = line['compras_idprov']
                SubElement(detalleCompras, "tipoComprobante").text = line['compras_tipocomprobante']
    
                if line['compras_tpidprov'] == "03":
                    SubElement(detalleCompras, "tipoProv").text = "01"# line['compras_tipoprov']
                    SubElement(detalleCompras, "denoProv").text = line['compras_nombreprov']
    
                SubElement(detalleCompras, "parteRel").text = line['compras_parterel'].upper()
                SubElement(detalleCompras, "fechaRegistro").text = str(line['compras_fechaemision'])[8:10] + "/" + str(line['compras_fechaemision'])[5:7] + "/" + str(line['compras_fechaemision'])[0:4]
                SubElement(detalleCompras, "establecimiento").text = line['compras_establecimiento']
                SubElement(detalleCompras, "puntoEmision").text = line['compras_puntoemision']
                SubElement(detalleCompras, "secuencial").text = line['compras_secuencial']
                SubElement(detalleCompras, "fechaEmision").text = str(line['compras_fechaemision'])[8:10] + "/" + str(line['compras_fechaemision'])[5:7] + "/" + str(line['compras_fechaemision'])[0:4]
                SubElement(detalleCompras, "autorizacion").text = line['compras_autorizacion']
    
                SubElement(detalleCompras, "baseNoGraIva").text = '%.2f' % float(line['compras_basenograiva'])
                SubElement(detalleCompras, "baseImponible").text = '%.2f' % float(line['compras_baseimponible'])
                SubElement(detalleCompras, "baseImpGrav").text = '%.2f' % float(line['compras_baseimpgrav'])
                SubElement(detalleCompras, "baseImpExe").text = '%.2f' % float(line['compras_baseimpexe'])
    
                SubElement(detalleCompras, "montoIce").text = '%.2f' % float(line['compras_montoice'])
                SubElement(detalleCompras, "montoIva").text = '%.2f' % float(line['compras_montoiva'])
    
                SubElement(detalleCompras, "valRetBien10").text = '%.2f' % float(line['compras_valretbien10'])
                SubElement(detalleCompras, "valRetServ20").text = '%.2f' % float(line['compras_valretserv20'])
                SubElement(detalleCompras, "valorRetBienes").text = '%.2f' % float(line['compras_valorretbienes'])
                SubElement(detalleCompras, "valRetServ50").text = '%.2f' % float(line['compras_valretserv50'])
                SubElement(detalleCompras, "valorRetServicios").text = '%.2f' % float(line['compras_valorretservicios'])
                SubElement(detalleCompras, "valRetServ100").text = '%.2f' % float(line['compras_valretserv100'])
                SubElement(detalleCompras, "valorRetencionNc").text = "0.00"
                SubElement(detalleCompras, "totbasesImpReemb").text = "0.00"
                #
                
                pagoExterior = SubElement(detalleCompras, "pagoExterior")
                SubElement(pagoExterior, "pagoLocExt").text = "01"
                SubElement(pagoExterior, "paisEfecPago").text = "NA"
                SubElement(pagoExterior, "aplicConvDobTrib").text = "NA"
                SubElement(pagoExterior, "pagExtSujRetNorLeg").text = "NA"
                #if(line['compras_baseimponible'])>1000:
                formasDePago = SubElement(detalleCompras, "formasDePago")
                SubElement(formasDePago, "formaPago").text = line['compras_formapago']
                
                if (line["detalle"]):
                    air = SubElement(detalleCompras, "air")
                    for detalle in line["detalle"]:
                        detalleAir = SubElement(air, "detalleAir")
                        SubElement(detalleAir, "codRetAir").text = detalle["codretair"]
                        SubElement(detalleAir, "baseImpAir").text = '%.2f' % detalle["baseimpair"]
                        SubElement(detalleAir, "porcentajeAir").text = '%.2f' % detalle["porcentajeair"]
                        SubElement(detalleAir, "valRetAir").text = '%.2f' % detalle["valretair"]
                #                    
                #totalreembolso = 0
                #if line['compras_tipocomprobante'] != "20":
                #    for reem in self.env['account.sustent.doc'].search([('invoice_id', '=', line['id_compras'])]):
                #        totalreembolso = totalreembolso + (reem.baseImponibleReemb + reem.baseImpGravReemb + reem.baseNoGraIvaReemb + reem.baseImpExeReemb)
    
                #SubElement(detalleCompras, "totbasesImpReemb").text = '%.2f' % float(totalreembolso)
    
                # if not line.compras_docmodificado:
                # pagoExterior = SubElement(detalleCompras, "pagoExterior")
                # SubElement(pagoExterior, "pagoLocExt").text = line['compras_pagolocext']
                # SubElement(pagoExterior, "paisEfecPago").text = line['compras_paisefecpago']
                # SubElement(pagoExterior, "aplicConvDobTrib").text = line['compras_aplicconvdobtrib']
                # SubElement(pagoExterior, "pagExtSujRetNorLeg").text = line['compras_pagextsujretnorleg']
    
                # if not line['compras_docmodificado'] or line['compras_tipocomprobante'] != "04":
                #     formasDePago = SubElement(detalleCompras, "formasDePago")
                #     SubElement(formasDePago, "formaPago").text = line['compras_formapago']
                #
                # if line['compras_tipocomprobante'] == "41":
                #     reembolsos = SubElement(detalleCompras, "reembolsos")
                #     for reem in self.env['account.sustent.doc'].search([('invoice_id', '=', line['id_compras'])]):
                #         reembolso = SubElement(reembolsos, "reembolso")
                #         SubElement(reembolso, "tipoComprobanteReemb").text = reem.reemb_doc_document_type_id.code
                #         # SubElement(reembolso, "tpIdProvReemb").text = reem.reemb_partner_id.doc_type_identification_id.code_tax
                #
                #         SubElement(reembolso, "tpIdProvReemb").text = reem.reemb_doc_document_type_id.code #line['compras_tipoprov']
                #
                #         idProvReemb = ""
                #         if reem.partner_exist and reem.reemb_partner_id:
                #             idProvReemb = reem.reemb_partner_id.vat_doc
                #         else:
                #             idProvReemb = reem.partner_vat
                #
                #
                #         SubElement(reembolso, "idProvReemb").text = idProvReemb
                #         SubElement(reembolso, "establecimientoReemb").text = reem.docnum[0:3]
                #         SubElement(reembolso, "puntoEmisionReemb").text = reem.docnum[4:7]
                #         SubElement(reembolso, "secuencialReemb").text = reem.docnum[8:100]
                #         SubElement(reembolso, "fechaEmisionReemb").text = str(reem.fechaEmisionReemb)[8:10] + "/" + str(reem.fechaEmisionReemb)[5:7] + "/" + str(reem.fechaEmisionReemb)[0:4]
                #         SubElement(reembolso, "autorizacionReemb").text = reem.authorization
                #         SubElement(reembolso, "baseImponibleReemb").text = '%.2f' % float(reem.baseImponibleReemb)
                #         SubElement(reembolso, "baseImpGravReemb").text = '%.2f' % float(reem.baseImpGravReemb)
                #         SubElement(reembolso, "baseNoGraIvaReemb").text = '%.2f' % float(reem.baseNoGraIvaReemb)
                #         SubElement(reembolso, "baseImpExeReemb").text = '%.2f' % float(reem.baseImpExeReemb)
                #         SubElement(reembolso, "montoIceRemb").text = '%.2f' % float(reem.montoIceRemb)
                #         SubElement(reembolso, "montoIvaRemb").text = '%.2f' % float(reem.montoIvaRemb)
                #
                #         # SubElement(detalleCompras, "codDocReemb").text = "41"
                #         # SubElement(detalleCompras, "totalComprobantesReembolso").text = '%.2f' % (float(line['compras_baseimponible']) + float(line['compras_montoiva']))
                #         # SubElement(detalleCompras, "totalBaseImponibleReembolso").text = '%.2f' % float(line['compras_baseimponible'])
                #         # SubElement(detalleCompras, "totalImpuestoReembolso").text = '%.2f' % float(line['compras_montoiva'])
                #
                #
                # if float(line['compras_baseimpair']) > 0 and line['compras_tipocomprobante'] != "41": #todo no muestra retenciones si es reembolso cod=41
                #     air = SubElement(detalleCompras, "air")
                #
                #     for retencion in self.env['account.out.withholding'].search([('docnum_mask', '=', line['compras_estabretencion1'] + "-" + line['compras_ptoemiretencion1'] + "-" + line['compras_secretencion1'])]):
                #         if retencion.partner_id.vat_doc == line['compras_idprov']:
                #             for retencion_line in retencion.line_ids:
                #                 if retencion_line.tax_id.tax_group_id.name == "RETENCION EN LA FUENTE COMPRAS":
                #                     detalleAir = SubElement(air, "detalleAir")
                #                     SubElement(detalleAir, "codRetAir").text = retencion_line.tax_id.name
                #                     SubElement(detalleAir, "baseImpAir").text = '%.2f' % float(retencion_line.base)
                #                     SubElement(detalleAir, "porcentajeAir").text = '%.2f' % float(retencion_line.porcentage)
                #                     SubElement(detalleAir, "valRetAir").text = '%.2f' % float(retencion_line.amount)
                #                     if retencion_line.tax_id.inf_dividendo:
                #                         SubElement(detalleAir, "fechaPagoDiv").text = str(retencion_line.fechaPagoDiv)[8:10] + "/" + str(retencion_line.fechaPagoDiv)[5:7] + "/" + str(retencion_line.fechaPagoDiv)[0:4]
                #                         SubElement(detalleAir, "imRentaSoc").text = '%.2f' % float(retencion_line.imRentaSoc)
                #                         SubElement(detalleAir, "anioUtDiv").text = str(retencion_line.anioUtDiv)
                #
                #
                if line['fechaemiret1']:
                    SubElement(detalleCompras, "estabRetencion1").text = line['estabretencion1']
                    SubElement(detalleCompras, "ptoEmiRetencion1").text = line['ptoemiretencion1']
                    SubElement(detalleCompras, "secRetencion1").text = line['secretencion1']
                    SubElement(detalleCompras, "autRetencion1").text = line['autretencion1']
                    fechaEmiRet1 = str(line['fechaemiret1'])[8:10] + "/" + str(line['fechaemiret1'])[5:7] + "/" + str(line['fechaemiret1'])[0:4]
                    SubElement(detalleCompras, "fechaEmiRet1").text = fechaEmiRet1
                
                
                if line['compras_docmodificado']:
                    SubElement(detalleCompras, "docModificado").text = line['compras_docmodificado']
                    SubElement(detalleCompras, "estabModificado").text = line['compras_estabmodificado']
                    SubElement(detalleCompras, "ptoEmiModificado").text = line['compras_ptoemimodificado']
                    SubElement(detalleCompras, "secModificado").text = line['compras_secmodificado']
                    SubElement(detalleCompras, "autModificado").text = line['compras_autmodificado']

        return root
    
    def _generate_ventas(self, root, date_from, date_to):
        company_id = self.env.user.company_id
        str_date_from = str(date_from.year) + "-" + str(date_from.month).zfill(2) + "-" + str(date_from.day).zfill(2)
        str_date_to = str(date_to.year) + "-" + str(date_to.month).zfill(2) + "-" + str(date_to.day).zfill(2)

        sql = """

;with variables as (
    select '%s'::date as fecha_inicial,
    '%s'::date as fecha_final ,
	%s::int as company_id    
),
retenciones_detalle as (
                select account_move.id,
                    sum(aml.l10n_ec_withhold_tax_amount) as total,
                    atxg.l10n_ec_type

                from res_company 
               inner join variables on res_company.id=variables.company_id 
                inner join res_partner rp  on rp.id=res_company.partner_id
                inner join account_move on account_move.company_id = res_company.id and account_move.move_type in ('out_invoice') and account_move.state in ('posted','paid')  and 
                account_move.invoice_date>=variables.fecha_inicial and account_move.invoice_date<=variables.fecha_final
                
                inner join account_journal aj on  aj.id=account_move.journal_id and coalesce(aj.l10n_latam_use_documents,false)=true 
                
                inner join account_move_line aml on aml.l10n_ec_withhold_invoice_id=account_move.id 
                inner join account_move_line_account_tax_rel atxrl on atxrl.account_move_line_id=aml.id 
                inner join account_tax atx on atx.id=  atxrl.account_tax_id 
                inner join account_tax_group atxg on atxg.id=atx.tax_group_id
                inner join account_move awt on awt.id=aml.move_id and awt.state in ('posted','paid')  
                where aml.l10n_ec_withhold_tax_amount>0.00
                group by     account_move.id        ,atxg.l10n_ec_type
)

select 
                'ventas'::VARCHAR tipo,
                rp.vat as idinformante,
                rp.name razonsocial,
                '001'::VARCHAR numestabruc,
                'NA'::VARCHAR::VARCHAR totalventas,
                'iva'::VARCHAR codigooperativo,
                case when(res_partner.vat='9999999999999') then '07'
                    else l10n_latam_identification_type.l10n_ec_code
                end as  ventas_tpidcliente,
                res_partner.vat as ventas_idcliente,
                'NO'::VARCHAR ventas_parterel,
                case when res_partner.is_company='f' then '01' else '02' end ventas_tipocliente,                
                case when doc_document_type.code='01' then '18' else doc_document_type.code end ventas_tipocomprobante,
                'E' ventas_tipoem,
                count(1)::INTEGER ventas_numerocomprobantes,
                coalesce(sum(coalesce(rdiva.total,0.00)),0.00)  as ventas_valorretiva,
                coalesce(sum(coalesce(rdfte.total,0.00)),0.00) as ventas_valorretrenta,
                Coalesce(doc_payment_type.code,'01') as ventas_formapago,
                0.00 as   ventas_basenograiva,
                sum(account_move.amount_base0) as   ventas_baseimponible,
                sum(account_move.amount_baseno0) as   ventas_baseimpgrav,
                sum(account_move.amount_taxno0) as  ventas_montoiva,
                'NA'::VARCHAR ventas_tipocompe,
                0.00 as ventas_montoice
                
                from res_company 
                inner join variables on res_company.id=variables.company_id 
                inner join res_partner rp  on rp.id=res_company.partner_id
                inner join account_move on account_move.company_id = res_company.id and account_move.move_type in ('out_invoice','out_refund') and account_move.state in ('posted','paid')  and 
                account_move.invoice_date>=variables.fecha_inicial and account_move.invoice_date<=variables.fecha_final 
                and coalesce(account_move.anulado_sri,false)!=true 
                inner join account_journal aj on  aj.id=account_move.journal_id and coalesce(aj.l10n_latam_use_documents,false)=true 
                
                left join res_partner on account_move.partner_id = res_partner.id
                left join l10n_latam_identification_type on res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
                left join l10n_ec_sri_payment doc_payment_type on doc_payment_type.id = account_move.l10n_ec_sri_payment_id 
                left join l10n_latam_document_type doc_document_type on doc_document_type.id = account_move.l10n_latam_document_type_id 
                left join retenciones_detalle rdiva on rdiva.id=account_move.id and rdiva.l10n_ec_type='withhold_vat_sale'
                left join retenciones_detalle rdfte on rdfte.id=account_move.id and rdfte.l10n_ec_type='withhold_income_sale' 
where doc_document_type.code!='00'                 
group by        rp.vat,
                rp.name , 
                  case when(res_partner.vat='9999999999999') then '07'
                    else l10n_latam_identification_type.l10n_ec_code
                end,
                res_partner.vat,Coalesce(doc_payment_type.code,'01'),
                case when res_partner.is_company='f' then '01' else '02' end ,                
                case when doc_document_type.code='01' then '18' else doc_document_type.code end """ % (str_date_from,str_date_to,company_id.id)
        self.env.cr.execute(sql)
        result = self.env.cr.dictfetchall()
        if result:
            ventas = SubElement(root, "ventas")
            for line in result:
                detalleVentas = SubElement(ventas, "detalleVentas")
                SubElement(detalleVentas, "tpIdCliente").text = line['ventas_tpidcliente']
                
                SubElement(detalleVentas, "idCliente").text = self.xmlGen(line['ventas_idcliente'])
    
                if line['ventas_tpidcliente'] != "07":
                    SubElement(detalleVentas, "parteRelVtas").text = "NO"
    
                if line['ventas_tpidcliente'] == "06" or line['ventas_tpidcliente'] == "08":
                    SubElement(detalleVentas, "tipoCliente").text = line['ventas_tipocliente']
                    SubElement(detalleVentas, "denoCli").text = self.xmlGen(line['ventas_denocli'])
    
                SubElement(detalleVentas, "tipoComprobante").text = line['ventas_tipocomprobante']
                SubElement(detalleVentas, "tipoEmision").text = line['ventas_tipoem']
                SubElement(detalleVentas, "numeroComprobantes").text = str(int(line['ventas_numerocomprobantes']))
    
                SubElement(detalleVentas, "baseNoGraIva").text = '%.2f' % float(line['ventas_basenograiva'])
                SubElement(detalleVentas, "baseImponible").text = '%.2f' % float(line['ventas_baseimponible'])
                SubElement(detalleVentas, "baseImpGrav").text = '%.2f' % float(line['ventas_baseimpgrav'])
    
                SubElement(detalleVentas, "montoIva").text = '%.2f' % float(line['ventas_montoiva'])
                SubElement(detalleVentas, "montoIce").text = '%.2f' % float(line['ventas_montoice'])
    
                SubElement(detalleVentas, "valorRetIva").text = '%.2f' % float(line['ventas_valorretiva'])
                SubElement(detalleVentas, "valorRetRenta").text = '%.2f' % float(line['ventas_valorretrenta'])
                
                if  line['ventas_tipocomprobante']!="04":
                    formasDePago = SubElement(detalleVentas, "formasDePago")
                    SubElement(formasDePago, "formaPago").text = line['ventas_formapago']

        return root

    def _generate_ventasEstablecimiento(self, root, date_from, date_to):
        company_id = self.env.user.company_id
        str_date_from = str(date_from.year) + "-" + str(date_from.month).zfill(2) + "-" + str(date_from.day).zfill(2)
        str_date_to = str(date_to.year) + "-" + str(date_to.month).zfill(2) + "-" + str(date_to.day).zfill(2)

        

        sql = """
            select substring(right(replace(t0.name,'-',''),15) from 1 for 3) codEstab, 
            sum(case when t0.move_type = 'out_invoice' then t0.amount_untaxed else -t0.amount_untaxed end) ventasEstab
            from account_move t0 
            inner join account_journal aj on  aj.id=t0.journal_id and coalesce(aj.l10n_latam_use_documents,false)=true 
            inner join l10n_latam_document_type t1 on t1.id = t0.l10n_latam_document_type_id 
            where t0.state in ('posted', 'paid') and t0.company_id="""+str(company_id.id)+""" 
            and t0.move_type in ('out_invoice', 'out_refund') and coalesce(t0.anulado_sri,false)!=true  
           and t0.invoice_date>='"""+str_date_from+"""' and t0.invoice_date<='"""+str_date_to+"""' and t1.code!='00' 
            group by substring(right(replace(t0.name,'-',''),15) from 1 for 3)            
        """
        self.env.cr.execute(sql)
        result = self.env.cr.dictfetchall()

        existlines = False
        i=0
        for line in result:
            i+=1
        #SubElement(root, "numEstabRuc").text = str(i).zfill(3)
        if result:
            ventasEstablecimiento = SubElement(root, "ventasEstablecimiento")
            for line in result:
                existlines = True
                ventaEst = SubElement(ventasEstablecimiento, "ventaEst")
                SubElement(ventaEst, "codEstab").text = line['codestab']
                SubElement(ventaEst, "ventasEstab").text = '0.00'#%.2f' % float(line['ventasestab'])
                SubElement(ventaEst, "ivaComp").text = '%.2f' % float(0)

        if not existlines:
            pass
            #ventaEst = SubElement(ventasEstablecimiento, "ventaEst")
            #SubElement(ventaEst, "codEstab").text = "000"
            #SubElement(ventaEst, "ventasEstab").text = '0.00'
            #SubElement(ventaEst, "ivaComp").text = '0.00'

    def _generate_anulados(self, root, date_from, date_to):
        company_id = self.env.user.company_id
        anulados = False
        str_date_from = str(date_from.year) + "-" + str(date_from.month).zfill(2) + "-" + str(date_from.day).zfill(2)
        str_date_to = str(date_to.year) + "-" + str(date_to.month).zfill(2) + "-" + str(date_to.day).zfill(2)
        
        sql = """ select 'anulados' tipo,
            rp.vat as idinformante,
            rp.name as razonsocial,
            'iva' codigooperativo,           
            t1.code tipocomprobante,
            substring(right(replace(t0.name,'-',''),15) from 1 for 3) establecimiento, 
            left(right(replace(t0.name,'-',''),12),3)  puntoemision,
            substring(right(replace(t0.name,'-',''),15) from 9 for 10) secuencialinicio,
            substring(right(replace(t0.name,'-',''),15) from 9 for 10) secuencialfin,
            t0.l10n_ec_authorization_number autorización
            
            from account_move t0 
            inner join res_company on res_company.id=t0.company_id 
            inner join res_partner rp on rp.id=res_company.partner_id 
            inner join account_journal aj on  aj.id=t0.journal_id and coalesce(aj.l10n_latam_use_documents,false)=true 
            inner join l10n_latam_document_type t1 on t1.id = t0.l10n_latam_document_type_id 
            where t0.state!='draft' and t0.company_id="""+str(company_id.id)+"""  
            and t0.move_type in ('out_invoice', 'out_refund') and coalesce(t0.anulado_sri,false)=true  and t1.code!='00' 
           and t0.invoice_date>='"""+str_date_from+"""' and t0.invoice_date<='"""+str_date_to+"""' 
             """           
            

        self.env.cr.execute(sql)
        result = self.env.cr.dictfetchall()

        if len(result) > 0:
            anulados = SubElement(root, "anulados")

        for line in result:
            detalleAnulados = SubElement(anulados, "detalleAnulados")
            SubElement(detalleAnulados, "tipoComprobante").text = line['tipocomprobante']
            SubElement(detalleAnulados, "establecimiento").text = line['establecimiento']
            SubElement(detalleAnulados, "puntoEmision").text = line['puntoemision']
            SubElement(detalleAnulados, "secuencialInicio").text = line['secuencialinicio']
            SubElement(detalleAnulados, "secuencialFin").text = line['secuencialfin']
            SubElement(detalleAnulados, "autorizacion").text = line['autorización']

    # endregion

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
            str_field = str_field.replace('-', '')
            str_field = str_field.replace('(', '')
            str_field = str_field.replace(')', '')
            str_field = str_field.replace('\n', '')
            str_field = str_field.replace('\r', '')
            str_field = str_field.replace('.', '')

        return str_field
    
    def process_report(self):
        #print(self._context)
        REPORT=self._context.get('default_report','')
        self=self.with_context({"no_raise":True})
        self=self.with_user(SUPERUSER_ID)        
        for brw_each in self:
            try:
                OBJ_ATS=self.env[self._name].sudo()
                context = dict(active_ids=[brw_each.id], 
                               active_id=brw_each.id,
                               active_model=self._name,
                               landscape=True
                               )            
                OBJ_ATS=OBJ_ATS.with_context(context)
                report_value= OBJ_ATS.env.ref(REPORT).with_user(SUPERUSER_ID).report_action(OBJ_ATS)
                report_value["target"]="new"
                return report_value
            except Exception as e:
                raise ValidationError(_("Error al Imprimir %s -- %s") % (REPORT,str(e),))
    
    # endregion


