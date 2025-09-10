# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api,fields, models,_
from odoo.exceptions import UserError,ValidationError
import re

class ResGroups(models.Model):
    _inherit="res.groups"

    is_profile=fields.Boolean('Perfil',default=False)

    def __copy_from_group_to_uid(self,to_uids):
        self.ensure_one()
        from_group=self
        to_users = self.env["res.users"].browse(to_uids)
        menu_ids = [(6, 0, [each_menu.id for each_menu in from_group.menu_ids])]
        report_ids = [(6, 0, [each_report.id for each_report in from_group.report_ids])]
        groups_id = [(6, 0, [from_group.id])]
        for brw_user in to_users:
            brw_user.write({"menu_ids": menu_ids,
                           "report_ids": report_ids,
                           "groups_id":groups_id
                           })
        return True

    def copy_from_group(self,user_ids):
        return self.__copy_from_group_to_uid(user_ids)
