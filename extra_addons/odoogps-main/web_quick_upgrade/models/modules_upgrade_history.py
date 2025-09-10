from datetime import datetime

from odoo import _, api, fields, models


class ModulesUpgradeHisotry(models.Model):
    _name = "modules.upgrade.history"

    last_update_module_date = fields.Datetime("Last Update Date")
    module_id = fields.Many2one("ir.module.module", "Module")
    shortdesc = fields.Char(related="module_id.shortdesc", string="Short Description")
    TechnicalName = fields.Char(related="module_id.name", string="Technical Name")
    state = fields.Selection(related="module_id.state", string="Status")

    def button_immediate_upgrade(self):
        self.module_id.button_immediate_upgrade()
        history_record = self.search([("module_id", "=", self.module_id.id)])
        if history_record:
            for record in history_record:
                record.write(
                    {
                        "last_update_module_date": datetime.strftime(
                            datetime.now(), "%Y-%m-%d %H:%M:%S"
                        )
                    }
                )
        else:
            self.env["modules.upgrade.history"].create(
                {
                    "last_update_module_date": datetime.strftime(
                        datetime.now(), "%Y-%m-%d %H:%M:%S"
                    ),
                    "module_id": self.module_id,
                }
            )
        return {"type": "ir.actions.client", "tag": "reload"}
