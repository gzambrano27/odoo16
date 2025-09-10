from odoo import models, fields, api,_
from odoo.exceptions import ValidationError


# class AccountMoveLine(models.Model):
#     _inherit = "account.move.line"

    # @api.constrains('move_id','move_id.state','account_id','analytic_distribution')
    # def validate_accounts(self):
    #     for brw_each in self:
    #         if brw_each.account_id:
    #             if brw_each.move_id.journal_id.name.lower() not in ('nómina','nomina'):
    #                 if brw_each.account_id.code.startswith('4') or brw_each.account_id.code.startswith('5') or brw_each.account_id.code.startswith('6'):
    #                     if not brw_each.analytic_distribution:
    #                         raise ValidationError(_("Debes definir cuentas analiticas cuando la cuenta inicia con 4 ,5 o 6"))
    #     return True
    

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        self.validate_analytic_distribution()
        return super().action_post()

    def validate_analytic_distribution(self):
        for move in self:
            if move.journal_id == move.company_id.payslip_journal_id or move.journal_id.code=='CIERR':
                continue
            for line in move.line_ids:
                if not line.account_id:
                    continue
                code = line.account_id.code or ''
                if code.startswith(('4', '5', '6')):
                    if not line.analytic_distribution:
                        raise ValidationError(_(
                            "Debes definir una distribución analítica para cuentas que inician con 4, 5 o 6.\n"
                            f"Línea con cuenta: {code} en el documento {move.name or move.id}"
                        ))