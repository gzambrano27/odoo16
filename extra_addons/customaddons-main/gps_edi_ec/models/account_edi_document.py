# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from json import dumps

from odoo import _, api, fields, models
from datetime import datetime,timedelta

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'
    
    @api.model
    def _cron_process_documents_web_services(self, job_count=None):
        ''' Method called by the EDI cron processing all web-services.

        :param job_count: Limit explicitely the number of web service calls. If not provided, process all.
        '''
        time_account_edi = self.env['ir.config_parameter'].sudo().get_param('time.account.edi.document','0')
        NOW=fields.Datetime.now()
        SECONDS=timedelta(seconds=int(time_account_edi))
        edi_documents = self.search([('state', 'in', ('to_send', 'to_cancel')), ('move_id.state', '=', 'posted'),('create_date','>=',NOW-SECONDS)])
        #print(edi_documents.ids)
        nb_remaining_jobs = edi_documents._process_documents_web_services(job_count=job_count)

        # Mark the CRON to be triggered again asap since there is some remaining jobs to process.
        if nb_remaining_jobs > 0:
            self.env.ref('account_edi.ir_cron_edi_network')._trigger()