
{
    'name': 'Cambios en Pagos',
    'version': '1.0',
    'category': 'Se realiza  cambios de modulos de pagos',
    'description': """

    """,
    'author': "GPS",
    'website': '',
    'depends': [
         'account_payment_advance','bi_purchase_advance_payment'
    ],
    'data': [
         "security/res_groups.xml",
        "security/ir.model.access.csv",
        "wizard/account_prepayment_assignment.xml",
        "wizard/account_payment_cancel_wizard.xml",
        "views/account_payment.xml",
    ],
    'installable': True,
}
