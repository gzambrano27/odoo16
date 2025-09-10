# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_

class AccountPrepaymentAssignment(models.TransientModel):
    _inherit="account.prepayment.assignment"

    @api.model
    def _get_default_company_id(self):
        if self._context.get("active_ids",[]):
            brw_move=self.env["account.move"].sudo().browse(self._context["active_ids"])
            return brw_move[0].company_id.id
        return False

    company_id=fields.Many2one("res.company",string="Empresa",default=_get_default_company_id)
    journal_type=fields.Char(selection=[('sale', 'Ventas'),
            ('purchase', 'Compras'),
            ('cash', 'Efectivo'),
            ('bank', 'Banco'),
            ('general', 'General'),],string="Tipo de Diario",compute="_get_journal_type")
    new_journal_id=fields.Many2one("account.journal",string="Diario")

    @api.onchange('prepayment_aml_id')
    def onchange_prepayment_aml_id(self):
        self.journal_type=None
        self.new_journal_id=False
        if self.prepayment_aml_id:
            self._get_journal_type()

    @api.depends('prepayment_aml_id')
    def _get_journal_type(self):
        for brw_each in self:
            brw_each.journal_type = brw_each.prepayment_aml_id.move_id.journal_id.type

    def button_confirm(self):
        self.move_id.prepayment_assign_move_new(
            prepayment_aml_id=self.prepayment_aml_id,
            amount=self.amount,
            date=self.date,
            new_journal_id=self.new_journal_id
        )
        return True