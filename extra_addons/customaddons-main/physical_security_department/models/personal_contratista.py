from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PersonalContratista(models.Model):
    _name = 'physical_security.personal_contratista'
    _description = 'Personal Contratista'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Nombre', compute='_compute_name', store=True)
    cedula = fields.Char(string='Cédula', required=True, tracking=True)
    apellidos = fields.Char(string='Apellidos', required=True, tracking=True)
    nombres = fields.Char(string='Nombres', required=True, tracking=True)
    cargo = fields.Char(string='Cargo', required=True, tracking=True)
    enlace_documento = fields.Char(string='Enlace documento', required=True, tracking=True)

    _sql_constraints = [
        ('unique_cedula', 'unique(cedula)', 'La cédula ya existe. Debe ser única.'),
    ]

    @api.depends('cedula', 'apellidos', 'nombres')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.cedula} - {record.apellidos} {record.nombres}"

    @api.constrains('cedula')
    def _check_valid_cedula(self):
        for record in self:
            ced = record.cedula or ''
            # Si no hay 10 caracteres aún, no validamos
            if len(ced) < 10:
                continue

            # A partir de aquí, len(ced) >= 10
            # Debe tener exactamente 10 dígitos numéricos
            if len(ced) != 10 or not ced.isdigit():
                raise ValidationError("La cédula debe tener exactamente 10 dígitos numéricos.")

            # Validación de código de provincia (01–24)
            province = int(ced[:2])
            if province < 1 or province > 24:
                raise ValidationError("La cédula tiene un código de provincia inválido.")

            # El tercer dígito < 6
            third_digit = int(ced[2])
            if third_digit >= 6:
                raise ValidationError("La cédula tiene un tercer dígito inválido para ser ecuatoriana.")

            # Cálculo del dígito verificador
            total = 0
            for i in range(9):
                d = int(ced[i])
                if i % 2 == 0:
                    d = d * 2
                    if d > 9:
                        d -= 9
                total += d
            next_ten = ((total + 9) // 10) * 10
            check_digit = next_ten - total if (next_ten - total) != 10 else 0

            if check_digit != int(ced[9]):
                raise ValidationError("La cédula no es válida según el algoritmo ecuatoriano.")