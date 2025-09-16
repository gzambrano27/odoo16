# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

DEFAULT_MODE_PAYMENTS=[('check', 'Cheque'),
                                             ('bank', 'Transferencia'),
                                             ('credit_card', 'Tarjeta de Crédito')
                                             ]

from .document_financial import *
from .document_financial_line import *
from .document_financial_line_payment import *
from .document_financial_line_payment_group import  *
from .document_financial_line_invoiced import *
from . res_bank import  *
from . res_bank_code import *

from .account_payment_request import *
from .account_configuration_payment import *
from .account_configuration_payment_bank import *

from .purchase_order import *

from .account_payment import *
from .account_payment_term import *

from .account_payment_bank_macro import *
from .account_payment_bank_macro_line import *
from .account_payment_bank_macro_summary import  *

from .account_move import *
from .account_move_line import  *
from .res_partner_bank import  *

from .account_group_report import *
from .account_group_report_line import *

from .account_partner_group_category import*
from .res_partner import *

from .purchase_order_payment_line import *

from .res_company import *
from .account_payment_request_type import *
from .account_payment_analysis_request_wizard import *
from .account_payment_analysis_request_line_wizard import *

from .bank_mail_message  import *

from . document_financial_version import  *
from . document_financial_placement import *

from . document_bank_reconciliation import  *
from . document_financial_liquidation import *
from . document_bank_reconciliation_line import  *
from . document_bank_reconciliation_line_group import  *

from . hr_employee_payment import *
from . hr_employee_movement import *
from . hr_employee_liquidation import *

from . document_bank_reconciliation_type import *
from . document_bank_reconciliation_summary import *

from .account_payment_lines import *

from .hr_salary_rule import *

from .hr_registro_reembolsos import *
from .hr_registro_caja_chica import *

from .bank_account_template import *

from .res_partner_bank_request import *

from .hr_employee import *

from .account_payment_request_lines import *

from .res_users import *