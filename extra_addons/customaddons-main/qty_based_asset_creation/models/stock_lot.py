# -*- coding: utf-8 -*-
# developed and maintained by RADORP Pvt.Ltd.

from odoo import models, fields, api, _


class StockLot(models.Model):
    _inherit = 'stock.lot'

    linked_asset_entries = fields.One2many('account.asset.asset', 'linked_serial_id', string='Asset Entries')
    linked_asset_count = fields.Integer('Asset entries count', compute='_compute_linked_asset_count')
    state = fields.Selection(
        [('activo', 'Activo'), ('depreciado', 'Depreciado'),('vendido', 'Vendido'), ('anulado', 'Anulado')],
        string='Status', readonly=True)

    @api.depends('linked_asset_entries')
    def _compute_linked_asset_count(self):
        for lot in self:
            lot.linked_asset_count = len(lot.linked_asset_entries)

    def action_view_asset(self):
        self.invalidate_model(['linked_asset_entries'])
        self.sudo()._read(['linked_asset_entries'])
        assets = self.linked_asset_entries
        action = self.env['ir.actions.act_window']._for_xml_id('om_account_asset.action_account_asset_asset_form')
        if len(assets) > 1:
            action['domain'] = [('id', 'in', assets.ids)]
        elif len(assets) == 1:
            res = self.env.ref('om_account_asset.view_account_asset_asset_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = assets.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
