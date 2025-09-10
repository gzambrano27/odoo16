# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import SUPERUSER_ID,api,fields, models,_
from odoo.exceptions import UserError
from ..functions.CompileFunction import CompileFunction
from ..functions.PrototypeFunction import PrototypeFunction
from ..tools.NumberTranslator import NumberTranslator
from ...message_dialog.tools import FileManager
from ...calendar_days.tools import CalendarManager,DateManager,MonthManager
from time import time
from odoo.tools.safe_eval import safe_eval
import logging
_logger = logging.getLogger(__name__)

class DynamicFunction(models.Model):    
    _name="dynamic.function"
    _description="Función"
    
    @api.model
    def __get_warning_displayed_name(self):
        return _("NOMBRE DE FUNCION NO VALIDA")
    
    def _get_displayed_name(self):
        for brw_each in self:
            displayed_name=(not brw_each.interface_id and ("%s(%s)" % (brw_each.name,brw_each.arguments and brw_each.arguments or "")) or (brw_each.external_name and brw_each.external_name or brw_each.name))
            brw_each.displayed_name= displayed_name
    
    @api.model
    def _get_default_programming_code(self):
        return "result=None"
    
    @api.model
    def _get_default_help_programming_code(self):
        def limit_name(name):
            fill_text=" "*39
            return ("#%s%s" % (name,fill_text))[:39]
        
        help_code= """#time                                  package             time
#calendarm                             class               CalendarManager()
#datem                                 class               DateManager(date_format=FORMAT_DATE)
#monthm                                class               MonthManager(year,month)
#filem                                 class               FileManager()
#error                                 exception           UserError(str)
#log                                   instance            _logger
#_                                     def                 _(str)
#_n                                    def                 NumberTranslator()._n(number)
#message                               def                 message(title,msg,type_dialog="info")
#download                              def                 download(title,msg,fileobj,filename)
#_month                                def                 self.env["calendar.month"].sudo().get_month_name(value)
#_day                                  def                 self.env["calendar.day"].sudo().get_day_name(value)
#SUPERUSER_ID                          int                 SUPERUSER_ID
#self                                  model               self
#compile_function                      def                 CompileFunction().execute(programming_code,*args)\n"""
        srch_function=self.search([('active','=',True)])
        for each_function in srch_function:
            help_code+="%sdef                 PrototypeFunction().execute(%s)\n" % (limit_name(each_function.name),each_function.arguments)
        return help_code
    
    def _compute_help_programming_code(self):
        for brw_each in self:
            help_programming_code=self._get_default_help_programming_code()
            brw_each.help_programming_code=help_programming_code
            
    name=fields.Char("Nombre de Función",required=True,size=35)
    external_name=fields.Char("Nombre Externo",required=False,size=255)
    arguments=fields.Text("Argumentos",required=False,default="")
    programming_code=fields.Text("Código de Programación",required=True,default=_get_default_programming_code)
    help_programming_code=fields.Text(compute='_compute_help_programming_code',string="Ayuda de Programación",readonly=False,store=False,default=_get_default_help_programming_code)    
    notes=fields.Text("Descripción",required=False)
    active=fields.Boolean("Activo",default=True)
    locked=fields.Boolean("Bloqueado",help="Registro no puede ser borrado",default=False)
    interface_id=fields.Many2one("dynamic.function.interface","Interfaz",required=False)
    property_ids=fields.Many2many("dynamic.function.property","dynamic_properties_rel","function_id","property_id","Propiedades")
    displayed_name=fields.Text(compute='_get_displayed_name', string='Definición',default=__get_warning_displayed_name)
    history_ids=fields.One2many('log.history','model_id','Historial',domain=[('model_name','=',_name)])
    
    
    _rec_name="displayed_name"
    _order="name asc"
    
    def unlink(self):
        for brw_each in self:
            if brw_each.locked:
                raise UserError(_("Registro esta bloqueado no puede ser borrado"))
        return super(DynamicFunction,self).unlink()
    
    def write(self,vals):        
        value= super(DynamicFunction,self).write(vals)
        return value
    
    @api.model
    def create(self, vals):
        brw_new= super(DynamicFunction,self).create(vals)
        return brw_new
    
    @api.onchange('name','arguments')
    def onchange_name(self):
        if self.name:
            name = self.name and self.name.lower() or ''
            arguments = self.arguments and self.arguments.lower() or ''
            return {"value":{"name":name,"arguments":arguments,"displayed_name": "%s(%s)" % (name,arguments and arguments or "") }}
        return {"value":{"displayed_name":self.__get_warning_displayed_name()}}
    
    @api.onchange('notes')
    def onchange_notes(self):
        for brw_each in self:
            brw_each.notes = brw_each.notes and brw_each.notes.upper() or ''
            
    @api.model
    def initialize(self):
        return self.get_dicts()
    
    @api.model
    def get_dicts(self):
        function_ids=self.search([('active','=',True)])    
        def message(title,msg,type_dialog="info"):        
            return self.env["message.wizard"].show(title,msg,type_dialog,self._context)
        def download(title,msg,fileobj,filename):        
            return self.env["file.wizard"].download(title,msg,fileobj,filename,self._context)
        global_dict = {
                    "calendarm":CalendarManager,
                    "datem":DateManager,
                    "monthm":MonthManager,
                    "filem":FileManager,
                    "error":UserError,
                    "_":_,
                    "time":time,
                    "_n":NumberTranslator()._n,
                    "message":message,
                    "download":download,
                    "SUPERUSER_ID":SUPERUSER_ID,
                    "_month":self.env["calendar.month"].sudo().get_month_name,
                    "_day":self.env["calendar.day"].sudo().get_day_name,
                    "log":_logger
                    }        
        def_object = CompileFunction( "compile_function", "programming_code,*args", "result=None", self._context, global_dict)
        global_dict["compile_function"] = getattr(def_object, "execute")
        localdict=global_dict.copy()
        localdict.update({"cr":self._cr,
                          "uid":self._uid,
                          "context":self._context.copy(),
                          "self":self})
        if function_ids:
            for brw in function_ids:
                def_object = self.create_function(brw.name, brw.arguments, brw.programming_code, self._context, global_dict)
                localdict[brw.name] = getattr(def_object, "execute")
                global_dict[brw.name] = getattr(def_object, "execute")
        return localdict,global_dict
    
    @api.model
    def function(self,function_name,variables,*args):
        localdict,global_dict=self.initialize()
        localdict.update(variables)
        return localdict[function_name](*args)
    
    @api.model  
    def execute(self,programming_code,variables):
        localdict,global_dict=self.initialize()
        localdict.update(variables)
        return self.executeProgrammingCode(programming_code, global_dict, localdict)

    @api.model
    def executeProgrammingCode(self,programming_code,global_dict, localdict):
        safe_eval(programming_code,global_dict, localdict, mode='exec', nocopy=True)
        return localdict
    
    @api.model
    def create_function(self,name,arguments,programming_code,context, global_dict):
        return PrototypeFunction(name, arguments, programming_code, context, global_dict)
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        search_ids = None
        if name:
            search_ids = self.search( [('interface_id','!=',False),('external_name',operator,name)] + args, limit=limit)
        if not search_ids:
            search_ids = self.search( [('name',operator,name)] + args, limit=limit)
        return (search_ids is not None) and search_ids.name_get() or []
    
