# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
import re
import logging  
_logger = logging.getLogger(__name__)

class L10nLatamDocumentType(models.Model):
    _inherit = "l10n_latam.document.type"

    def _format_document_number(self, document_number):
        self.ensure_one()
        if self.country_id != self.env.ref("base.ec"):
            return super(L10nLatamDocumentType, self)._format_document_number(document_number)
        if not document_number:
            return False
        if self.l10n_ec_check_format:
            document_number = re.sub(r'\s+', "", document_number)  # remove any whitespace
            _logger.info("Document Number Before Format: %s", document_number)  # Mensaje de depuración

            # Split the document number by dashes to see if it's already partially formatted
            parts = document_number.split('-')

            if len(parts) == 1 and len(parts[0]) <= 9:
                # Only the sequential part is provided, pad it with zeroes
                part3 = parts[0].zfill(9)
                document_number = f"001-001-{part3}"
                _logger.info("Document Number After Auto Format: %s", document_number)
            elif len(parts) == 3:
                # Handle the case where the document number might already be partially formatted
                part1, part2, part3 = parts
                if len(part1) <= 3 and len(part2) <= 3 and len(part3) <= 9:
                    part1 = part1.zfill(3)
                    part2 = part2.zfill(3)
                    part3 = part3.zfill(9)
                    document_number = f"{part1}-{part2}-{part3}"
                    _logger.info("Document Number After Format: %s", document_number)  # Mensaje de depuración
                else:
                    raise UserError(
                        _("Ecuadorian Document %s must be like 001-001-123456789") % (self.display_name)
                    )
            else:
                raise UserError(
                    _("Ecuadorian Document %s must be like 001-001-123456789") % (self.display_name)
                )

        return document_number