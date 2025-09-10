# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from functools import partial
from lxml import etree
from markupsafe import Markup

from odoo import _, models
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_VAT_SUBTAXES
from odoo.addons.l10n_ec_edi.models.ir_attachment import L10N_EC_XSD_URLS
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import float_repr, float_round, html_escape
from odoo.tools.xml_utils import cleanup_xml_node, validate_xml_from_attachment
from pytz import timezone
from requests.exceptions import ConnectionError as RConnectionError
from zeep import Client
from zeep.exceptions import Error as ZeepError
from zeep.transports import Transport

TEST_URL = {
    'reception': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
    'authorization': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
}

PRODUCTION_URL = {
    'reception': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
    'authorization': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
}

DEFAULT_TIMEOUT_WS = 20

class AccountEdiFormat(models.Model):

    _inherit = 'account.edi.format'


    def _check_move_configuration(self, move):
        # EXTENDS account.edi.format
        errors = super()._check_move_configuration(move)

        if self.code != 'ecuadorian_edi' or move.country_code != 'EC':
            return errors

        if (move.move_type in ('out_invoice', 'out_refund')
                or move.l10n_latam_document_type_id.internal_type == 'purchase_liquidation'
                or move.journal_id.l10n_ec_withhold_type == 'in_withhold'):
            journal = move.journal_id
            address = journal.l10n_ec_emission_address_id
            if not move.company_id.vat:
                errors.append(_("You must set a VAT number for company %s", move.company_id.display_name))

            if not address:
                errors.append(_("You must set an emission address on journal %s", journal.display_name))

            if address and not address.street:
                errors.append(_("You must set an address on contact %s, field Street must be filled", address.display_name))

            if address and not address.commercial_partner_id.street:
                errors.append(_(
                    "You must set a headquarter address on contact %s, field Street must be filled",
                    address.commercial_partner_id.display_name
                ))

            if not move.commercial_partner_id.vat:
                errors.append(_("You must set a VAT number for partner %s", move.commercial_partner_id.display_name))

            if not move.l10n_ec_sri_payment_id and move.move_type in ['out_invoice', 'in_invoice']: #needed for sale invoice and purchase liquidation
                errors.append(_("You must set the Payment Method SRI on document %s", move.display_name))

            if not move.l10n_latam_document_number:
                errors.append(_("You must set the Document Number on document %s", move.display_name))

            if move._l10n_ec_is_withholding():
                for line in move.l10n_ec_withhold_line_ids:
                    if not line.l10n_ec_withhold_invoice_id.l10n_ec_sri_payment_id:
                        errors.append(_(
                            "You must set the Payment Method SRI on document %s",
                            line.l10n_ec_withhold_invoice_id.name
                        ))
                    if not line.l10n_ec_withhold_invoice_id:
                        errors.append(_("Please use the wizard on the invoice to generate the withholding."))
                    code = move._l10n_ec_wth_map_tax_code(line)
                    if not code:
                        errors.append(_("Wrong tax (%s) for document %s", line.tax_ids[0].name, move.display_name))
            else:
                unsupported_tax_types = set()
                vat_subtaxes = (lambda l: L10N_EC_VAT_SUBTAXES[l.tax_group_id.l10n_ec_type])
                tax_groups = self.env['account.move']._l10n_ec_map_tax_groups
                for line in move.line_ids.filtered(lambda l: l.tax_group_id.l10n_ec_type):
                    if not (vat_subtaxes(line) and tax_groups(line)):
                        unsupported_tax_types.add(line.tax_group_id.l10n_ec_type)
                for tax_type in unsupported_tax_types:
                    errors.append(_("Tax type not supported: %s", tax_type))

        if not move.company_id.sudo().l10n_ec_edi_certificate_id and not move.company_id._l10n_ec_is_demo_environment():
            errors.append(_("You must select a valid certificate in the settings for company %s", move.company_id.name))

        if not move.company_id.l10n_ec_legal_name:
            pass
            #errors.append(_("You must define a legal name in the settings for company %s", move.company_id.name))

        if not move.commercial_partner_id.country_id:
            errors.append(_("You must set a Country for Partner: %s", move.commercial_partner_id.name))

        # if move.move_type == "out_refund": #and not move.reversed_entry_id:
        #     errors.append(_(
        #         "Credit Note %s must have an original invoice related, try to 'Add Credit Note' from invoice",
        #         move.display_name
        #     ))

        if move.l10n_latam_document_type_id.internal_type == 'debit_note' and not move.debit_origin_id:
            errors.append(_(
                "Debit Note %s must have an original invoice related, try to 'Add Debit Note' from invoice",
                move.display_name
            ))
        return errors