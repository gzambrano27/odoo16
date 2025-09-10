from odoo import api, fields, models
from datetime import date

class FleetVehicleMulta(models.Model):
    _name = 'fleet.vehicle.multa'
    _description = 'Multas del Vehículo'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo')
    date = fields.Date(string='Fecha', required=True)
    amount = fields.Float(string='Monto', required=True)
    description = fields.Text(string='Descripción')
    responsable_id = fields.Many2one('res.partner')
    
class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    multa_ids = fields.One2many('fleet.vehicle.multa', 'vehicle_id', string='Multas')
    tipo = fields.Selection([
        ('propio', 'Propio'),
        ('rentado', 'Rentado'),
        ], 'Tipo', track_visibility='onchange', copy=False, default='propio')
    # Pestaña Batería
    battery_installation_date = fields.Date(string="Fecha de Instalación")
    battery_brand = fields.Char(string="Marca de la Batería")
    battery_manufacture_date = fields.Date(string="Fecha de Fabricación")
    battery_serial_number = fields.Char(string="Numeración")
    battery_check_date = fields.Date(string="Fecha de Toma")
    # Campos para la pestaña "Impuestos"
    tax_ids = fields.One2many('fleet.vehicle.tax', 'vehicle_id', string="Impuestos")
    maintenance_ids = fields.One2many('vehicle.maintenance', 'vehicle_id', string="Mantenimientos")
    # Campos para la pestaña "Seguro"
    insurance_company = fields.Char(string="Aseguradora")
    insurance_policy = fields.Char(string="Póliza Seguro")
    insurance_start_date = fields.Date(string="Fecha de Inicio")
    insurance_end_date = fields.Date(string="Fecha de Vencimiento")
    insurance_paid_amount = fields.Float(string="Importe Pagado ($)")
    insurance_payment_date = fields.Date(string="Fecha de Pago")
    insurance_status = fields.Selection(
        [('vigente', 'Vigente'), ('vencido', 'Vencido')],
        string="Estado Póliza",
        compute="_compute_insurance_status",
        store=True,
    )

    @api.depends('insurance_end_date')
    def _compute_insurance_status(self):
        """Determina el estado de la póliza de seguro."""
        for record in self:
            if record.insurance_end_date and record.insurance_end_date < date.today():
                record.insurance_status = 'vencido'
            else:
                record.insurance_status = 'vigente'

    # Pestaña Llantas
    tire_installation_date = fields.Date(string="Fecha de Instalación")
    tire_brand = fields.Char(string="Marca Neumáticos")
    tire_manufacture_date = fields.Date(string="Fecha de Fabricación")
    tire_model = fields.Char(string="Modelo Neumático")
    tire_size_front_left = fields.Char(string="Medida Delt LH")
    tire_size_front_right = fields.Char(string="Medida Delt RH")
    tire_size_rear_left = fields.Char(string="Medida Post LH")
    tire_size_rear_right = fields.Char(string="Medida Post RH")
    tire_second_axle_left_1 = fields.Char(string="2do eje - 1era LH")
    tire_second_axle_left_2 = fields.Char(string="2do eje - 1era LH2")
    tire_third_axle_left_1 = fields.Char(string="3er eje - 1era LH1")
    tire_third_axle_left_2 = fields.Char(string="3er eje - 1era LH12")
    tire_check_date = fields.Date(string="Fecha de Toma")

class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'
    

    vehicle_type = fields.Selection(selection_add=[
        ('moto', 'Moto'),
        ('camion', 'Camion'),
        ('camioneta', 'Camioneta'),
        ('tractor', 'Tractor'),
    ], ondelete={
        'moto': 'set default',
        'camion': 'set default',
        'camioneta': 'set default',
        'tractor': 'set default',
    })

class FleetVehicleTax(models.Model):
        _name = 'fleet.vehicle.tax'
        _description = 'Impuestos de Vehículo'

        vehicle_id = fields.Many2one('fleet.vehicle', string="Vehículo", required=True, ondelete='cascade')
        tax_type = fields.Char(string="Tipo Impuesto")
        year = fields.Integer(string="Año")
        tax_name = fields.Char(string="Impuesto")
        tax_amount = fields.Float(string="Impuesto ($)")
        payment_date = fields.Date(string="Fecha de Pago")
        remaining_days = fields.Integer(string="Días Restantes Pago", compute="_compute_remaining_days", store=True)
        comment1 = fields.Text(string="Comentario 1")
        month = fields.Selection(
            [(str(i), f"{i:02d}") for i in range(1, 13)], string="MES"
        )
        comment2 = fields.Text(string="Comentario 2")

        @api.depends('payment_date')
        def _compute_remaining_days(self):
            """Calcula los días restantes para el pago."""
            for record in self:
                if record.payment_date:
                    delta = (record.payment_date - date.today()).days
                    record.remaining_days = delta if delta >= 0 else 0
                else:
                    record.remaining_days = 0

