# models/account_account_supercias.py
from odoo import models, fields, api, _

class AccountAccountSupercias(models.Model):
	_name = 'account.account.supercias'
	_description = 'Grupo Supercia'
	_inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

	code = fields.Char(string="Código Grupo Supercia")
	name_base = fields.Char(string="Nombre del Grupo Supercia", required=True, tracking=True)
	name = fields.Char(string="Nombre Completo", compute="_compute_name", store=True)

	@api.depends('code', 'name_base')
	def _compute_name(self):
		for rec in self:
			parts = []
			if rec.code:
				parts.append(rec.code.strip())
			if rec.name_base:
				parts.append(rec.name_base.strip())
			rec.name = " - ".join(parts)
