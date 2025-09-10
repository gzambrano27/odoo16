# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .amount_to_text import amount_to_text_ec,amount_to_text_es

class NumberTranslator(object):
    
    def __init__(self):
        pass
    
    _languages={
        "es":amount_to_text_es,
        "ec":amount_to_text_ec
    }
    
    def _n(self,language,number,currency):
        return self._languages[language](number,currency)
        