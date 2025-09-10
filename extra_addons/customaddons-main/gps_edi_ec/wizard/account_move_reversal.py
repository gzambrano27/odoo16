# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _,api
from odoo.exceptions import UserError,ValidationError

class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"
    
    def reverse_moves(self):
        self.ensure_one()
        moves = self.move_ids
        if not moves:
            raise ValidationError(_("Debes definir un documento base"))
        for brw_move in moves:
            if brw_move.move_type== "out_invoice" and brw_move.journal_id.type== "sale" and brw_move.journal_id.l10n_latam_use_documents:
                if brw_move.partner_id.vat== "9999999999999":
                    if self.journal_id.l10n_latam_use_documents:
                        raise ValidationError(_("No puedes crear una nc de un consumidor final"))
        result=super(AccountMoveReversal,self).reverse_moves()
        if self.new_move_ids:
            self.new_move_ids._write({
                "manual_origin":False
                })
            for brw_new_move in self.new_move_ids:
                if brw_new_move.move_type == "out_refund":
                    brw_new_move._inverse_l10n_latam_document_number()
        return result
    
    @api.onchange('reason')
    def onchange_reason(self):
        self.reason=(self.reason and self.reason.upper() or None)
        
