# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import sys, traceback
from odoo import _
from odoo.exceptions import AccessError

class BaseFunction(object):
    
    def __init__(self,name,arguments):
        self.name=name
        self.arguments=arguments
    
    def _match_arguments(self,arguments_text):
        return arguments_text and arguments_text.split(",") or []
    
    def _wrap_arguments(self,args,localdict):
        index=0
        ALL_ARGS=self._match_arguments(self.arguments)
        for each_match_args in ALL_ARGS:
            localdict[each_match_args]=args[index]
            index+=1
        return localdict
    
    def _raise(self,exception):
        traceback.print_exc(file=sys.stdout)
        raise AccessError(_("Error ejecutando función %s: %s " % (self.name,str(exception))))
    
    def execute(self,*args):
        return None