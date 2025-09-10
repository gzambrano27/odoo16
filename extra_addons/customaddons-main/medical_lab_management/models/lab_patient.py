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

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class LabPatient(models.Model):
    _name = 'lab.patient'
    _rec_name = 'patient'
    _description = 'Paciente'

    patient = fields.Many2one('res.partner', string='Paciente', required=True)
    patient_aspirante = fields.Many2one('hr.applicant', string='Paciente', required=True)
    patient_image = fields.Binary(string='Foto')
    patient_id = fields.Char(string='Paciente ID', readonly=True)
    name = fields.Char(string='Paciente ID', default=lambda self: _('New'))
    tipo = fields.Selection([
         ('empleado', 'Empleado'),
         ('aspirante', 'Aspirante')
    ], string='Tipo', default='empleado', required=True)
    title = fields.Selection([
         ('ms', 'Señora'),
         ('mister', 'Señor'),
         ('mrs', 'Señorita'),
    ], string='Titulo', default='mister', required=True)
    emergency_contact = fields.Many2one(
        'res.partner', string='Contacto de Emergencia')
    gender = fields.Selection(
        [('m', 'Masculino'), ('f', 'Femenino'),
         ('ot', 'Otro')], 'Genero', required=True)
    dob = fields.Date(string='Fecha de Nacimiento', required=True)
    age = fields.Char(string='Edad', compute='compute_age', store=True)
    blood_group = fields.Selection(
        [('A+', 'A+ve'), ('B+', 'B+ve'), ('O+', 'O+ve'), ('AB+', 'AB+ve'),
         ('A-', 'A-ve'), ('B-', 'B-ve'), ('O-', 'O-ve'), ('AB-', 'AB-ve')],
        'Grupo Sanguineo')
    visa_info = fields.Char(string='Info Visa', size=64)
    id_proof_number = fields.Char(string='Numero de Prueba')
    note = fields.Text(string='Notas')
    date = fields.Datetime(string='Fecha de Solicitud', default=lambda s: fields.Datetime.now(), invisible=True)
    phone = fields.Char(string="Telefono", required=True)
    email = fields.Char(string="Email", required=True)

    @api.depends('dob')
    def compute_age(self):
        for data in self:
            if data.dob:
                dob = fields.Datetime.from_string(data.dob)
                date = fields.Datetime.from_string(data.date)
                delta = relativedelta(date, dob)
                data.age = str(delta.years) + ' ' + 'años'
            else:
                data.age = ''

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('lab.patient')
        vals['name'] = sequence or _('Nuevo')
        result = super(LabPatient, self).create(vals)
        return result

    @api.onchange('patient','patient_aspirante')
    def detail_get(self):
        self.phone = self.patient.phone
        self.email = self.patient.email
        if self.tipo=='empleado':
            empleado = self.env['hr.employee'].search([('work_contact_id','=',self.patient.id)])
            self.dob = empleado.birthday if empleado else None
            self.gender = 'm' if empleado.gender =='male' else 'f'
        else:
            self.dob = self.patient_aspirante.dob
            self.gender = self.patient_aspirante.gender
        

class HrAspirante(models.Model):
    _inherit = 'hr.applicant'

    dob = fields.Date(string='Fecha de Nacimiento', required=True)
    gender = fields.Selection(
        [('m', 'Masculino'), ('f', 'Femenino'),
         ('ot', 'Otro')], 'Genero', required=True)
    

    def name_get(self):
        res = []
        for record in self:
            name = '{} - {}'.format(record.name, record.partner_name)
            res.append((record.id, name))
        return res