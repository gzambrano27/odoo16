from odoo import models, fields, api,SUPERUSER_ID,_
from odoo.exceptions import ValidationError

class ResPartnerBankWizard(models.TransientModel):
    _name = 'res.partner.bank.wizard'
    _description = 'Wizard para res.partner.bank'

    def process(self):
        self = self.with_context({"no_raise": True})
        self = self.with_user(SUPERUSER_ID)
        REPORT = "gps_bancos.report_res_partner_bank_wizard_report_xlsx_act"
        for brw_each in self:
            try:
                #brw_each.validate_range_days()
                OBJ_REPORTS = self.env[self._name].sudo()
                context = dict(active_ids=[brw_each.id],
                               active_id=brw_each.id,
                               active_model=self._name,
                               landscape=True
                               )
                OBJ_REPORTS = OBJ_REPORTS.with_context(context)
                report_value = OBJ_REPORTS.env.ref(REPORT).with_user(SUPERUSER_ID).report_action(OBJ_REPORTS)
                report_value["target"] = "new"
                return report_value
            except Exception as e:
                raise ValidationError(_("Error al Imprimir %s -- %s") % (REPORT, str(e),))