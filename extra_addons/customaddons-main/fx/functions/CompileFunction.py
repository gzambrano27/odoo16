# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .PrototypeFunction import PrototypeFunction

class CompileFunction(PrototypeFunction):
        
    def execute(self,*args):
        localdict=self.global_dict.copy()
        try:
            localdict=self._wrap_arguments(args, localdict)
            self.programming_code=args[0]
            self.execute_code(self.programming_code,localdict)
            return localdict.get("result",None)
        except Exception as e:
            localdict["exception"]=e
            self._raise(e)
            
    def _wrap_arguments(self,args,localdict):
        index=0
        for value in args:
            if index>0:
                each_match_args="arg%s" % (index-1,)
                localdict[each_match_args]=value
            index+=1
        return localdict