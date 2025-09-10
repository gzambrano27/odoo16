# -*- encoding: utf-8 -*-
#from addons.mail.models import mail_tracking_value
from odoo import api,fields, models, SUPERUSER_ID
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class MailTracking(models.Model):
    _inherit = 'mail.tracking.value'

    id_text = fields.Text(string="Texto", compute="_compute_id_text", store=True)
    
    @api.depends('field_desc')
    def _compute_id_text(self):
        for record in self:
            record.id_text = str(record.mail_message_id.id)

    fecha_res_id = fields.Datetime(string="Fecha relacionada", compute="_compute_fecha_res_id", store=True)

    @api.depends('mail_message_id')
    def _compute_fecha_res_id(self):
        for record in self:
            record.fecha_res_id = False
            try:
                msg = record.mail_message_id
                model_name = msg.model
                res_id = msg.res_id

                if model_name == 'purchase.order' and model_name in self.env and res_id:
                    related_record = self.env[model_name].browse(res_id)
                    if related_record.exists():
                        record.fecha_res_id = related_record.create_date
                if model_name != 'purchase.order' and model_name in self.env and res_id:
                    related_record = self.env[model_name].browse(res_id)
                    if related_record.exists():
                        record.fecha_res_id = related_record.create_date

            except Exception as e:
                _logger.warning("Error en _compute_fecha_res_id: %s", e)


