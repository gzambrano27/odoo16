# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Anusha P P @ cybrosys and Niyas Raphy @ cybrosys(odoo@cybrosys.com)
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

import datetime
from odoo.exceptions import UserError
from odoo import fields, models, api, _


class Appointment(models.Model):
    _name = 'lab.appointment'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _description = "Cita"
    _order = 'appointment_date'

    user_id = fields.Many2one('res.users', 'Responsable', readonly=True)
    patient_id = fields.Many2one('lab.patient', string='Paciente', required=True, select=True,
                                 help='Nombre de Paciente')
    name = fields.Char(string='ID Cita', readonly=True, default=lambda self: _('New'))
    date = fields.Datetime(string='Fecha de Solicitud', default=lambda s: fields.Datetime.now(),
                           help="Esta es la fecha en la que se anota la cita del paciente.")
    appointment_date = fields.Datetime(string='Fecha de Cita', default=lambda s: fields.Datetime.now(),
                                       help="Esta es la fecha de la cita")
    physician_id = fields.Many2one('res.partner', string='Referido Por', select=True)
    comment = fields.Text(string='Comentarios')
    appointment_lines = fields.One2many('lab.appointment.lines', 'test_line_appointment', string="Prueba de Solicitud")

    request_count = fields.Integer(compute="_compute_state", string='# de Solicitudes', copy=False, default=0)
    inv_count = fields.Integer(compute="_compute_state", string='# de Facturas', copy=False, default=0)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('request_lab', 'Solicitud Laboratorio'),
        ('completed', 'Resultado de Prueba'),
        ('to_invoice', 'A Facturar'),
        ('invoiced', 'Hecho'),
        ('cancel', 'Cancelado'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft',
    )

    priority = fields.Selection([
        ('0', 'Bajo'),
        ('1', 'Normal'),
        ('2', 'Alto')
    ], size=1)

    _defaults = {
        'priority': '0',
    }

    @api.model
    def create(self, vals):
        if vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('lab.appointment') or _('Nuevo')
            result = super(Appointment, self).create(vals)
            return result

    def _compute_state(self):
        for obj in self:
            obj.request_count = self.env['lab.request'].search_count([('app_id', '=', obj.id)])
            obj.inv_count = self.env['account.move'].search_count([('lab_request', '=', obj.id)])

    def create_invoice(self):
        invoice_obj = self.env["account.move"]
        for lab in self:
            lab.write({'state': 'to_invoice'})
            if lab.patient_id:
                curr_invoice = {
                    'partner_id': lab.patient_id.patient.id,
                    'state': 'draft',
                    'move_type': 'out_invoice',
                    'invoice_date': str(datetime.datetime.now()),
                    'invoice_origin': "Lab Test# : " + lab.name,
                    'lab_request': lab.id,
                    'is_lab_invoice': True,
                }

                inv_ids = invoice_obj.create(curr_invoice)
                inv_id = inv_ids.id

                if inv_ids:
                    journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
                    prd_account_id = journal.default_account_id.id
                    list_value = []
                    if lab.appointment_lines:
                        for line in lab.appointment_lines:
                            list_value.append((0, 0, {
                                'name': line.lab_test.lab_test,
                                'price_unit': line.cost,
                                'quantity': 1.0,
                                'account_id': prd_account_id,
                                'move_id': inv_id,
                            }))
                        print(list_value)
                        inv_ids.write({'invoice_line_ids': list_value})

                self.write({'state': 'invoiced'})
                view_id = self.env.ref('account.view_move_form').id
                return {
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name': _('Lab Invoices'),
                    'res_id': inv_id
                }

    def action_request(self):
        if self.appointment_lines:
            for line in self.appointment_lines:
                data = self.env['lab.test'].search([('lab_test', '=', line.lab_test.lab_test)])
                self.env['lab.request'].create({'lab_request_id': self.name,
                                                'app_id': self.id,
                                                'lab_requestor': self.patient_id.id,
                                                'lab_requesting_date': self.appointment_date,
                                                'test_request': line.lab_test.id,
                                                'request_line': [(6, 0, [x.id for x in data.test_lines])],
                                                })
            self.state = 'request_lab'
        else:
            raise UserError(_('Please Select Lab Test.'))

    def confirm_appointment(self):
        """ Confirma la cita y envía un correo al paciente """
        
        # Verificar si el paciente tiene un email
        if not self.patient_id or not self.patient_id.email:
            raise ValueError("El paciente no tiene un correo electrónico registrado.")

        message_body = f"""
            <p>Estimado/a {self.patient.name},</p>
            <p>Tu cita ha sido confirmada.</p>
            <p><strong>ID Cita:</strong> {self.name}</p>
            <p><strong>Fecha:</strong> {self.appointment_date}</p>
            <br>
            <p>Gracias.</p>
        """

        # Crear plantilla de correo
        mail_values = {
            'subject': 'Confirmación de Cita',
            'body_html': message_body,
            'email_from': self.env.company.email,  # Email de la empresa actual
            'email_to': self.patient_id.email,  # 'wguijarro@gpsgroup.com.ec'#
        }

        # Crear el correo y enviarlo
        mail_id = self.env['mail.mail'].sudo().create(mail_values)
        mail_id.sudo().send()  # Corregido: se usa send() sin parámetros

        # Cambiar el estado de la cita a "confirmada"
        self.write({'state': 'confirm'})

    def cancel_appointment(self):
        return self.write({'state': 'cancel'})


class LabAppointmentLines(models.Model):
    _name = 'lab.appointment.lines'
    _description = 'Cita Consultorio '

    lab_test = fields.Many2one('lab.test', string="Prueba")
    cost = fields.Float(string="Costo")
    requesting_date = fields.Date(string="Fecha")
    test_line_appointment = fields.Many2one('lab.appointment', string="Cita")

    @api.onchange('lab_test')
    def cost_update(self):
        if self.lab_test:
            self.cost = self.lab_test.test_cost


class LabPatientInherit(models.Model):
    _inherit = 'lab.patient'

    app_count = fields.Integer(compute="_compute_state", string='# de Citas', copy=False, default=0)

    def _compute_state(self):
        for obj in self:
            obj.app_count = self.env['lab.appointment'].search_count([('patient_id', '=', obj.id)])
