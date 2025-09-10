# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .BaseFunction import BaseFunction
from odoo.tools.safe_eval import safe_eval

class PrototypeFunction(BaseFunction):
        
    def __init__(self,name,arguments,programming_code,context,global_dict={}):
        super(PrototypeFunction,self).__init__(name,arguments)
        self.context=context
        self.programming_code=programming_code
        self.global_dict=global_dict
    
    def execute_code(self,programming_code,localdict):
        safe_eval(programming_code,self.global_dict, localdict, mode='exec', nocopy=True)
            
    def execute(self,*args):
        localdict=self.global_dict.copy()
        try:
            localdict=self._wrap_arguments(args, localdict)
            self.execute_code(self.programming_code,localdict)
            return localdict.get("result",None)
        except Exception as e:
            localdict["exception"]=e
            self._raise(e)
        