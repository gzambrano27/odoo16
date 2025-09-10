# -*- coding: utf-8 -*-
# © <2024> <Washington Guijarro>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from functools import partial
from odoo import api, fields, models
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from hashlib import sha256
from json import dumps
import math
import re
from textwrap import shorten

from odoo import api, fields, models, _, Command
from odoo.addons.account.tools import format_rf_reference
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.tools import (
    date_utils,
    email_re,
    email_split,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    groupby,
    is_html_empty,
    sql
)
L10N_EC_VAT_RATES = {
    5: 5.0,
    2: 12.0,
    10: 13.0,
    3: 14.0,
    4: 15.0,
    0: 0.0,
    6: 0.0,
    7: 0.0,
    8: 8.0,
}
L10N_EC_VAT_SUBTAXES = {
    'vat05': 5,
    'vat08': 8,
    'vat12': 2,
    'vat13': 10,
    'vat14': 3,
    'vat15': 4,
    'zero_vat': 0,
    'not_charged_vat': 6,
    'exempt_vat': 7,
}  # NOTE: non-IVA cases such as ICE and IRBPNR not supported
L10N_EC_VAT_TAX_NOT_ZERO_GROUPS = (
    'vat05',
    'vat08',
    'vat12',
    'vat13',
    'vat14',
    'vat15',
)
L10N_EC_VAT_TAX_ZERO_GROUPS = (
    'zero_vat',
    'not_charged_vat',
    'exempt_vat',
)
L10N_EC_VAT_TAX_GROUPS = tuple(L10N_EC_VAT_TAX_NOT_ZERO_GROUPS + L10N_EC_VAT_TAX_ZERO_GROUPS)  # all VAT taxes
L10N_EC_WITHHOLD_CODES = {
    'withhold_vat_purchase': 2,
    'withhold_income_purchase': 1,
}
L10N_EC_WITHHOLD_VAT_CODES = {
    0.0: 7,  # 0% vat withhold
    10.0: 9,  # 10% vat withhold
    20.0: 10,  # 20% vat withhold
    30.0: 1,  # 30% vat withhold
    50.0: 11, # 50% vat withhold
    70.0: 2,  # 70% vat withhold
    100.0: 3,  # 100% vat withhold
}  # NOTE: non-IVA cases such as ICE and IRBPNR not supported
# Codes from tax report "Form 103", useful for withhold automation:
L10N_EC_WTH_FOREIGN_GENERAL_REGIME_CODES = ['402', '403', '404', '405', '406', '407', '408', '409', '410', '411', '412', '413', '414', '415', '416', '417', '418', '419', '420', '421', '422', '423']
L10N_EC_WTH_FOREIGN_TAX_HAVEN_OR_LOWER_TAX_CODES = ['424', '425', '426', '427', '428', '429', '430', '431', '432', '433']
L10N_EC_WTH_FOREIGN_NOT_SUBJECT_WITHHOLD_CODES = ['412', '423', '433']
L10N_EC_WTH_FOREIGN_SUBJECT_WITHHOLD_CODES = list(set(L10N_EC_WTH_FOREIGN_GENERAL_REGIME_CODES) - set(L10N_EC_WTH_FOREIGN_NOT_SUBJECT_WITHHOLD_CODES))
L10N_EC_WTH_FOREIGN_DOUBLE_TAXATION_CODES = ['402', '403', '404', '405', '406', '407', '408', '409', '410', '411', '412']
L10N_EC_WITHHOLD_FOREIGN_REGIME = [('01', '(01) General Regime'), ('02', '(02) Fiscal Paradise'), ('03', '(03) Preferential Tax Regime')]



class AccountMove(models.Model):
    _inherit= 'account.move'

    company_mult_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company)
    manual_date = fields.Date(string='Manual Date')
    manual_document_number = fields.Char(string="Manual Document Number")
    tax_line_ids = fields.One2many(
        comodel_name="account.move.taxes", inverse_name="move_id", string=_("Taxes"),compute="_compute_tax_line_ids",store=True
    )


    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref(self._get_mail_template(), raise_if_not_found=False)
        lang = False
        if template:
            lang = template._render_lang(self.ids)[self.id]
        if not lang:
            lang = get_lang(self.env).code
        compose_form = self.env.ref('account.account_invoice_send_wizard_form', raise_if_not_found=False)
        print(self.env.company)
        user_company = self.company_mult_id
        print(user_company)
        # Find the email template for the user's company and set the email_from
        if template:
            template.email_from = user_company.email or self.env.user.email

        ctx = dict(
            default_model='account.move',
            default_res_id=self.id,
            # For the sake of consistency we need a default_res_model if
            # default_res_id is set. Not renaming default_model as it can
            # create many side-effects.
            default_res_model='account.move',
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
            default_email_layout_xmlid="mail.mail_notification_layout_with_responsible_signature",
            model_description=self.with_context(lang=lang).type_name,
            force_email=True,
            active_ids=self.ids,
        )

        report_action = {
            'name': _('Send Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice.send',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

        if self.env.is_admin() and not self.env.company.external_report_layout_id and not self.env.context.get('discard_logo_check'):
            return self.env['ir.actions.report']._action_configure_external_report_layout(report_action)

        return report_action
    
    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number')
    def _inverse_l10n_latam_document_number(self):
        for rec in self.filtered(lambda x: x.l10n_latam_document_type_id):
            if not rec.l10n_latam_document_number:
                rec.name = '/'
            else:
                parts = rec.l10n_latam_document_number.split('-')

                if len(parts) == 1 and len(parts[0]) <= 9:
                    # Only the sequential part is provided, pad it with zeroes
                    part3 = parts[0].zfill(9)
                    entidad = self.journal_id.l10n_ec_entity
                    pto_emision = self.journal_id.l10n_ec_emission
                    document_number = f"{entidad}-{pto_emision}-{part3}"
                else:
                    document_number = rec.l10n_latam_document_number
                l10n_latam_document_number = rec.l10n_latam_document_type_id._format_document_number(document_number)
                if rec.l10n_latam_document_number != l10n_latam_document_number:
                    rec.l10n_latam_document_number = l10n_latam_document_number
                rec.name = "%s %s" % (rec.l10n_latam_document_type_id.doc_code_prefix, l10n_latam_document_number)

    def _get_profit_vat_tax_grouped_details(self):
        """ This methods is to return the amounts grouped by tax support and the withhold tax to be applied"""
        # Create a grouped tax method to return profit and vat tax details with _prepare_edi_tax_details method
        self.ensure_one()

        def grouping_function(wth_tax_index, base_line, tax_values):
            line = base_line['record']
            for tax in base_line['taxes']:  # Iterar sobre los impuestos
                tax_support = tax.l10n_ec_code_taxsupport
            # Should return tuple doc sustento + withholding tax
            #tax_support = base_line['taxes'].l10n_ec_code_taxsupport
            # Profit withhold logic
                withhold = line._get_suggested_supplier_withhold_taxes()[wth_tax_index]
                return {'tax_support': tax_support,
                        'withhold_tax': withhold}
        # Calculate tax_details grouped for the (profit, VAT) withholds
        return (
            self._prepare_edi_tax_details(grouping_key_generator=partial(grouping_function, 1)),  # profit grouping
            self._prepare_edi_tax_details(grouping_key_generator=partial(grouping_function, 0))  # VAT grouping
        )
    
    @api.model
    def _get_taxes_vals(self, line):#gps
        tax_vals = {}
        if not line.tax_ids:
            return tax_vals
        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        taxes = line.tax_ids.compute_all(
            price,
            line.move_id.currency_id,
            line.quantity,
            product=line.product_id,
        )["taxes"]
        base_tax = line.tax_ids.filtered(lambda x: x.include_base_amount)
        #base = 0
        #if base_tax:
        #    base = sum([t.get("amount") for t in taxes if base_tax.id == t.get("id")])
        for tl in taxes:
            tax_id = tl.get("id")
            tax = line.tax_ids.filtered(lambda x: x.id == tax_id and x.is_base_affected)
            #if tax and tl.get("amount") != 0:
            #    tl.update({"base": base})
            tax_vals.update(
                {
                    tax_id: {
                        "move_id": self.id,
                        "sequence": tl.get("sequence"),
                        "amount": tl.get("amount"),
                        "base": tl.get("base"),
                        "name": tl.get("name"),
                        "account_id": tl.get("account_id"),
                    }
                }
            )
        return tax_vals
    
    @api.onchange('tax_totals','invoice_line_ids')
    @api.depends('tax_totals','invoice_line_ids')
    def _compute_tax_line_ids(self):
        for brw_each in self:
            brw_each.button_update_move_taxes()

    def button_update_move_taxes(self):
        self.ensure_one()
        values = {}
        for line in self.invoice_line_ids:
            taxes = self._get_taxes_vals(line)
            for tax in taxes:
                if not tax in values:
                    values.update({tax: taxes[tax]})
                else:
                    values[tax]["base"] += taxes[tax]["base"]
                    values[tax]["amount"] += taxes[tax]["amount"]
        tax_line_ids=[(5,)]
        if values:            
            for tax, vals in values.items():
                tax_line_ids.append((0,0,vals))
        self.tax_line_ids=tax_line_ids

    def action_post_masivo(self):
        print("action_post_masivo")
        invoices = self.env['account.move'].with_context(active_test=False).search([
            ('move_type', 'in', ['in_invoice','out_invoice']),
            ('state', '=', 'draft'),
            ('to_check', '=', True)
        ])

        if not invoices:
            print("No invoices to confirm")
            return

        confirmed_count = 0
        error_count = 0
        for rec in invoices:
            try:
                rec.action_post()
                confirmed_count += 1
            except Exception as e:
                error_count += 1

        if confirmed_count > 0:
            message = _("%d invoices confirmed successfully." % confirmed_count)
            if error_count > 0:
                message += _("\n%d invoices failed to confirm. Check the logs for details." % error_count)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Confirmation Complete'),
                    'message': message,
                    'type': 'success' if error_count == 0 else 'warning',
                    'sticky': False,
                }
            }
        else:
            raise UserError(_("No invoices were confirmed. Please check if they meet the criteria."))
        

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    analytic_account_names = fields.Char(
        string='Cuentas Analíticas',
        compute='_compute_analytic_account_names'
    )

    @api.depends('analytic_distribution')
    def _compute_analytic_account_names(self):
        for line in self:
            if isinstance(line.analytic_distribution, dict):
                # Obtiene los IDs de las cuentas analíticas
                analytic_account_ids = list(line.analytic_distribution.keys())
                # Busca los nombres de las cuentas analíticas utilizando esos IDs
                analytic_accounts = self.env['account.analytic.account'].search([('id', 'in', analytic_account_ids)])
                line.analytic_account_names = ', '.join(analytic_accounts.mapped('name'))
            else:
                line.analytic_account_names = ''

    # def name_get(self):
    #     return [(line.id, " ".join(
    #         element for element in (
    #             line.move_id.name,
    #             'XXXXXXXXXXX',
    #             line.ref and f"({line.ref})",
    #             line.name or line.product_id.display_name,
    #         ) if element
    #     )) for line in self]
