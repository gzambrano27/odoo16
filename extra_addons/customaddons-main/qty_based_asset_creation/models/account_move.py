# -*- coding: utf-8 -*-
# developed and maintained by RADORP Pvt.Ltd.

from odoo import models, fields, _
from odoo.exceptions import AccessError
from odoo.exceptions import UserError

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_asset_vals(self):
        self.ensure_one()
        price = self.price_unit if self.asset_category_id.based_on_qty else self.price_subtotal
        price_subtotal = self.currency_id._convert(
            price,
            self.company_currency_id,
            self.company_id,
            self.move_id.invoice_date or fields.Date.context_today(
                self))
        return {
            'name': self.name,
            'code': self.name or False,
            'category_id': self.asset_category_id.id,
            'value': price_subtotal,
            'partner_id': self.move_id.partner_id.id,
            'company_id': self.move_id.company_id.id,
            'currency_id': self.move_id.company_currency_id.id,
            'date': self.move_id.invoice_date or self.move_id.date,
            'invoice_id': self.move_id.id,
        }

    def _asset_create(self, vals):
        """ *- create asset with provided values
            *- Do auto validate if auto-confirm set to ture in asset category"""
        asset = self.env['account.asset.asset'].create(vals)
        if self.asset_category_id.open_asset:
            if not self.env.user.has_group('account.group_account_manager'):
                raise AccessError(
                    _("Purchased asset is configured to auto confirm. Please contact Accounting Advisor to "
                      "confirm this bill"))
            if asset.date_first_depreciation == 'manual':
                asset.first_depreciation_manual_date = asset.date
            asset.validate()

    def asset_create(self):
        """ *- overridden from om_account_asset
            *- efficiently split the base function for future customizations"""
        if self.asset_category_id:
            vals = self._get_asset_vals()
            changed_vals = self.env['account.asset.asset'].onchange_category_id_values(vals['category_id'])
            vals.update(changed_vals['value'])
            if self.asset_category_id.based_on_qty:
                vals.update({
                    'linked_product_id': self.product_id.id or False,
                    'purchase_order_id': self.purchase_order_id.id or False,
                })
                for count in range(int(self.quantity)):
                    serial_no = self.product_id._find_no_asset_lot(self)
                    if str(serial_no) == "None":
                        raise UserError(_("El número de serie (serial_no) no puede ser None. Asegúrate de que se haya asignado un número de serie antes de proceder."))
                    name = self.name + '-' + str(serial_no.name) if serial_no else self.name
                    vals.update({
                        'linked_serial_id': serial_no.id or False,
                        'name': name or False,
                    })
                    self._asset_create(vals)
            else:
                self._asset_create(vals)
        return True
