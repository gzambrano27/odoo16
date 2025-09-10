# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _,SUPERUSER_ID
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import DateManager
from ...calendar_days.tools import CalendarManager
fileO=FileManager()        
dateO=DateManager()
calendarO=CalendarManager()
from datetime import timedelta

REPORT_DICT_VALUES= {
    'kardex':'gps_inventario.report_kardex_report_xlsx_act',
    'date_inventory':'gps_inventario.report_date_inventory_report_xlsx_act',
    'all_movement':'gps_inventario.report_all_movement_report_xlsx_act',
    'adjust':'gps_inventario.report_adjust_inventory_xlsx_act',
}

class StockInventoryReport(models.TransientModel):
    _name = "stock.inventory.report"
    _description = "Asistente de Informes de Inventarios"
    
    @api.model
    def get_default_company_ids(self):
        if self._context.get("allowed_company_ids", []):
            return self._context.get("allowed_company_ids", [])
        return [self.env["res.users"].browse(self._uid).company_id.id]

    @api.model
    def get_default_company_id(self):
        if self._context.get("allowed_company_ids", []):
            return self._context.get("allowed_company_ids", [])[0]
        return [self.env["res.users"].browse(self._uid).company_id.id][0]

    company_ids=fields.Many2many("res.company","stock_inventory_wizard_report_company_rel","wizard_id","company_id","Compañias",default=get_default_company_ids)
    company_id = fields.Many2one("res.company",  "Compañia", default=get_default_company_id)

    product_ids=fields.Many2many("product.product","stock_inventory_wizard_product_rel","wizard_id","product_id","Producto")

    product_id = fields.Many2one("product.product", "Producto")

    enable_parent_location=fields.Boolean("Habilitar Solo Ub. Padres",default=False)

    location_ids = fields.Many2many("stock.location", "stock_inventory_wizard_location_rel", "wizard_id", "location_id",
                                   "Ubicaciones")

    warehouse_ids = fields.Many2many("stock.warehouse", "stock_inventory_wizard_warehouse_rel", "wizard_id", "warehouse_id",
                                    "Bodegas")


    type_report = fields.Selection([('kardex', 'Kardex'),
                                    ('date_inventory', 'Inventario a la fecha'),
                                    ('all_movement', 'Todos los movimientos'),
                                    ('adjust','Ajustes de Inventarios')
                                    ],
                                   default='kardex', copy=False,string="Tipo de Reporte")

    by_company=fields.Boolean(string="Agrupado por Empresa",default=True)

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.warehouse_ids=[(6,0,[])]
        self.location_ids = [(6, 0, [])]

    @api.onchange('company_id','warehouse_ids','enable_parent_location')
    def onchange_warehouse_ids(self):
        OBJ_LOCATION=self.env["stock.location"].sudo()
        warehouse_ids=self.warehouse_ids.ids
        warehouse_ids += [-1, -1]
        all_locations=[]
        print(self.company_id.id,tuple(warehouse_ids))
        if not self.enable_parent_location:
            self._cr.execute("""select sl.id,sl.id
    
    from stock_location sl 
    inner join stock_warehouse wh on wh.id=sl.warehouse_id
    where sl.usage='internal'
    and wh.company_id=%s and wh.id in %s""",(self.company_id.id,tuple(warehouse_ids)))
            result=self._cr.fetchall()
            if result:
                all_locations+=[*dict(result)]
        else:#solo padres
            self._cr.execute("""select sl.id, sl.location_id 
    
    from stock_location sl 
    inner join stock_warehouse wh on wh.id=sl.warehouse_id
	inner join stock_location slv on slv.id=sl.location_id
    where sl.usage='internal' and slv.usage='view'
    and wh.company_id=%s and wh.id in %s""",(self.company_id.id,tuple(warehouse_ids)))
            result = self._cr.fetchall()
            if result:
                all_locations += [*dict(result)]
        self.location_ids = [(6, 0, all_locations)]
        all_locations+=[-1,-1]
        return {"domain":{"location_ids":[('id','in',all_locations)]}}


    @api.model
    def get_default_date_from(self):
        if self._context.get('default_type_report','')=='kardex':
            return dateO.create(2024,9,30)
        return fields.Date.context_today(self)+timedelta(days=-30)

    @api.model
    def get_default_date_to(self):
        return fields.Date.context_today(self)


    date_from=fields.Date(string="Desde",default=get_default_date_from)
    date_to = fields.Date(string="Hasta",default=get_default_date_to)

    def process_report(self):
        self = self.with_context({"no_raise": True})
        self = self.with_user(SUPERUSER_ID)
        for brw_each in self:
            if brw_each.type_report=='kardex':
                if brw_each.date_from<dateO.create(2024,9,30).date():
                    raise ValidationError(_("No puedes consultar el kardex de un fecha anterior al  2024-09-30"))
            try:
                OBJ_REPORTS= self.env[self._name].sudo()
                context = dict(active_ids=[brw_each.id],
                               active_id=brw_each.id,
                               active_model=self._name,
                               landscape=True
                               )
                REPORT = REPORT_DICT_VALUES[brw_each.type_report]
                OBJ_REPORTS = OBJ_REPORTS.with_context(context)
                report_value = OBJ_REPORTS.env.ref(REPORT).with_user(SUPERUSER_ID).report_action(OBJ_REPORTS)
                report_value["target"] = "new"
                return report_value
            except Exception as e:
                raise ValidationError(_("Error al Imprimir %s -- %s") % (REPORT, str(e),))