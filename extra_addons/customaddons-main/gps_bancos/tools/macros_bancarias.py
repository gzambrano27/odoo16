# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from odoo import fields, models, api, _
from collections import defaultdict

from werkzeug.routing import ValidationError


class macros_bancarias(object):

    def get_file_name_macro_local(self, obj):
        raise ValidationError(_("Metodo 'get_file_name_macro_local' no implementado"))

    def generate_file_macro_local(self,obj, writer, journal_name, brw_company):
        raise ValidationError(_("Metodo 'generate_file_macro_local' no implementado"))

    def get_file_name_macro_ext(self, obj):
        raise ValidationError(_("Metodo 'get_file_name_macro_ext' no implementado"))

    def generate_file_macro_ext(self,obj, writer, journal_name, brw_company):
        raise ValidationError(_("Metodo 'generate_file_macro_ext' no implementado"))
