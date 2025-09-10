# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _,api
from odoo.exceptions import UserError,ValidationError

class AccountDebitNote(models.TransientModel):
    _inherit = "account.debit.note"
    
    @api.model
    def get_default_journal_id(self):
        active_ids=self._context.get("active_ids",[])
        if active_ids:
            brw_move=self.env["account.move"].sudo().browse(active_ids[0])
            return brw_move.journal_id.id
        return False
    
    journal_id=fields.Many2one(default=get_default_journal_id)
    
    @api.onchange('reason')
    def onchange_reason(self):
        self.reason=(self.reason and self.reason.upper() or None)
        
    def _prepare_default_values(self, move):
        self=self.with_context({"internal_type":"debit_note"})
        values=super(AccountDebitNote,self)._prepare_default_values(move)
        values["manual_origin"]=False
        l10n_latam_document_type_srch=self.env["l10n_latam.document.type"].sudo().search([('country_id.code', '=', 'EC'), ('internal_type', '=', 'debit_note')])
        values["l10n_latam_document_type_id"]=l10n_latam_document_type_srch and l10n_latam_document_type_srch[0].id or False
        return values
    
    def create_debit(self):
        self.ensure_one()
        moves = self.move_ids
        if not moves:
            raise ValidationError(_("Debes definir un documento base"))
        for brw_move in moves:
            if brw_move.move_type== "out_invoice" and brw_move.journal_id.type== "sale" and brw_move.journal_id.l10n_latam_use_documents:
                if brw_move.partner_id.vat== "9999999999999":
                    raise ValidationError(_("No puedes crear una nota de debito de un consumidor final"))
        self=self.with_context({"internal_type":"debit_note"})
        values=super(AccountDebitNote,self).create_debit()
        context=values["context"].copy()
        context["internal_type"]="debit_note"
        values["context"]=context
        return values