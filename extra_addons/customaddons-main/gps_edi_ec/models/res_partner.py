# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields,api,_
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('vat')
    def validate_vat(self):
        for brw_each in self:
            if brw_each.vat:
                srch_identification = self.search(
                    [('id', '!=', brw_each.id), ('vat', '=', brw_each.vat),('parent_id','=',False)])
                if len(srch_identification) > 0:
                    raise ValidationError(
                        _("Existe un contacto(cliente,proveedor,empleado,usuario,etc...) con la identificación %s ya registrada") % (brw_each.vat   ,))
