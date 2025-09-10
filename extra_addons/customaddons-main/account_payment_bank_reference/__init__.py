from . import models
from . import wizards

"""
from odoo import SUPERUSER_ID
from odoo import api

import logging
_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    aml = env['account.move.line'].search([])
    for a in aml:
        if a.payment_id:
            p = a.payment_id
            try:
                a.bank_reference = p.payment_slip_number or p.check_number or p.bank_reference
            except:
                pass
            if p.payment_slip_number:
                _logger.warning("Computing bank reference for move: %s", a.name)
                _logger.warning("p.payment_slip_number is: %s", p.payment_slip_number)
                _logger.warning("p.check_number is: %s", p.check_number)
                _logger.warning("p.bank_reference is: %s", p.bank_reference)
                _logger.warning("a.bank_reference is: %s", a.bank_reference)

    payments = env['account.payment'].search([])
    for p in payments:
        try:
            p.bank_reference = p.payment_slip_number or p.check_number
        except:
            pass
        if p.payment_slip_number:
            _logger.warning("Computing bank match number for payment: %s", p.name)
            _logger.warning("p.payment_slip_number is: %s", p.payment_slip_number)
            _logger.warning("p.check_number is: %s", p.check_number)
            _logger.warning("p.bank_reference is: %s", p.bank_reference)
            _logger.warning("new p.bank_reference is: %s", p.bank_reference)
"""
