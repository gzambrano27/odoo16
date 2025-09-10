# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class delete_internal_transfers_company(models.Model):
#     _name = 'delete_internal_transfers_company.delete_internal_transfers_company'
#     _description = 'delete_internal_transfers_company.delete_internal_transfers_company'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
