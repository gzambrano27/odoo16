# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError,UserError
from odoo import api, fields, models, _



class ProductCategory(models.Model):
    _inherit="product.category"

    def write(self, vals):
        value = super(ProductCategory, self).write(vals)
        self.validate_permisos()
        return value

    @api.model
    def create(self, vals):
        brw_new = super(ProductCategory, self).create(vals)
        self.validate_permisos()
        return brw_new

    def validate_permisos(self):
        if self._uid in (1,2):
            return True
        user=self.env.user
        if not user.has_group('gps_inventario.group_categorias_manager'):
            raise ValidationError(_("Solo las personas del grupo 'Acceso a crear categorias' puedes crear o modificar una categoria"))
        return True