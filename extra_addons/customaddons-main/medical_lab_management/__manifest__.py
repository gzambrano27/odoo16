# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

{
    'name': "Medical Lab Management",
    'version': '16.0.1.1.0',
    'summary': """Manage Medical Lab Operations.""",
    'description': """Manage Medical Lab General Operations, Odoo16""",
    'author': "Washington Guijarro",
    'maintainer': 'GPS Group',
    'company': "GPS",
    'website': "https://www.gpsgroup.com",
    'category': 'Industrias',
    'depends': ['base', 'mail', 'account', 'contacts','hr_recruitment'],
    'data': [
        'security/lab_users.xml',
        'security/ir.model.access.csv',
        'views/res_partner.xml',
        'views/lab_patient_view.xml',
        'views/test_unit_view.xml',
        'views/lab_test_type.xml',
        'views/lab_test_content_type.xml',
        'views/physician_specialty.xml',
        'views/physician_details.xml',
        'views/lab_request.xml',
        'views/lab_appointment.xml',
        'views/account_invoice.xml',
        'report/report.xml',
        'report/lab_test_report.xml',
        'report/lab_patient_card.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
