from datetime import datetime

from odoo import api, models


class IRMOdule(models.Model):
    _inherit = "ir.module.module"

    def button_immediate_upgrade(self):
        res = super(IRMOdule, self).button_immediate_upgrade()
        history_record = self.env["modules.upgrade.history"].search(
            [("module_id", "=", self.id)]
        )
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
                    "module_id": self.id,
                }
            )
        return res
