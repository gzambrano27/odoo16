from odoo import http
from odoo.http import request
import base64

class AccountPaymentReportController(http.Controller):

    @http.route('/web/content/account.payment.report/<int:report_id>/download', type='http', auth="user")
    def download_file(self, report_id, **kwargs):
        record = request.env['account.payment.report'].browse(report_id)
        if record.exists():
            file_content = base64.b64decode(record.csv_export_file)
            filename = record.csv_export_filename
            return request.make_response(
                file_content,
                [('Content-Type', 'application/octet-stream'),
                 ('Content-Disposition', 'attachment; filename="%s"' % filename)]
            )
        else:
            return request.not_found()