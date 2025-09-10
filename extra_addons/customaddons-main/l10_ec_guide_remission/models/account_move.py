# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.osv import expression


class AccountMove(models.Model):
    _inherit = "account.move"

    guide_remission_ids = fields.One2many('l10n_ec.guide.remission', 'invoice_id', string='Guide Remission',
                                          readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    guide_remission_order_count = fields.Integer(compute="_compute_origin_gr_count", string='Guide Remission Count')
    #store=True


    #@api.depends('guide_remission_ids')
    def _compute_origin_gr_count(self):
        for move in self:
            move.guide_remission_order_count = len(move.guide_remission_ids)

    def action_view_guide_remission(self):
        """This function returns an action that display existing Guide Remission
        of given invoice.
        It can either be a in a list or in a form view, if there is only
        one Guide Remission to show.
        """
        self.ensure_one()
        form_view_name = "l10_ec_guide_remission.std_referral_guide_view_form"
        result = self.env["ir.actions.act_window"]._for_xml_id(
            "l10_ec_guide_remission.action_guide_remission"
        )
        if len(self.guide_remission_ids) > 1:
            result["domain"] = "[('id', 'in', %s)]" % self.guide_remission_ids.ids
        else:
            form_view = self.env.ref(form_view_name)
            result["views"] = [(form_view.id, "form")]
            result["res_id"] = self.guide_remission_ids.id
        return result





