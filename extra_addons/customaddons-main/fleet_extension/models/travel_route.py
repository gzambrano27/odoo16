from odoo import models, fields, api

class TravelRoute(models.Model):
    _name = 'travel.route'
    _description = 'Rutas de Viaje'

    name = fields.Char(string="Nombre", required=True, default=lambda self: self.env['ir.sequence'].next_by_code('travel.route'))
    departure_date = fields.Date(string="Fecha de Salida", required=True)
    arrival_date = fields.Date(string="Fecha de Llegada", required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehículo", required=True)
    license_plate = fields.Char(related="vehicle_id.license_plate", string="Placa", readonly=True)
    driver_id = fields.Many2one('res.partner', string="Conductor")
    vehicle_status = fields.Char(string="Estado Vehículo")
    origin_address_id = fields.Many2one('travel.address', string="Dirección Origen")
    origin_place = fields.Char(string="Origen", related='origin_address_id.place', readonly=True)
    destination_address_id = fields.Many2one('travel.address', string="Dirección Destino")
    destination_place = fields.Char(string="Destino", related='destination_address_id.place', readonly=True)
    odometer_start = fields.Float(string="Kms Inicial (Odómetro)")
    odometer_end = fields.Float(string="Kms Final (Odómetro)")
    kms_traveled = fields.Float(string="Kms Recorridos", compute="_compute_kms_traveled", store=True)
    cargo_weight = fields.Float(string="Peso de carga (Kg)")
    cost_per_kg = fields.Float(string="Costo por Kg de carga ($/Kg)")
    total_income = fields.Float(string="Ingreso Total ($)", compute="_compute_total_income", store=True)
    fuel_station = fields.Char(string="Estación de Combustible")
    fuel_type = fields.Selection([('gasoline', 'Gasolina'), ('diesel', 'Diésel')], string="Tipo de Combustible")
    price_per_gallon = fields.Float(string="Precio x Galón ($/gal)")
    total_fuel_cost = fields.Float(string="Total Combustible ($)")
    toll_expense = fields.Float(string="Gasto peajes ($)")
    food_expense = fields.Float(string="Gasto comidas ($)")
    other_expenses = fields.Float(string="Otros Gastos ($)")
    total_expenses = fields.Float(string="Gasto Total ($)", compute="_compute_total_expenses", store=True)
    fuel_volume = fields.Float(string="Volumen de Combustible (gal)")
    efficiency = fields.Float(string="Recorrido por und. de comb. (Km/gal)", compute="_compute_efficiency", store=True)
    income_per_km = fields.Float(string="Ingreso por Kms de recorrido ($/Km)", compute="_compute_income_per_km", store=True)
    notes = fields.Text(string="Observaciones")


    @api.depends('odometer_start', 'odometer_end')
    def _compute_kms_traveled(self):
        for record in self:
            record.kms_traveled = max(0, record.odometer_end - record.odometer_start)

    @api.depends('cargo_weight', 'cost_per_kg')
    def _compute_total_income(self):
        for record in self:
            record.total_income = record.cargo_weight * record.cost_per_kg

    @api.depends('toll_expense', 'food_expense', 'other_expenses', 'total_fuel_cost')
    def _compute_total_expenses(self):
        for record in self:
            record.total_expenses = sum([record.toll_expense, record.food_expense, record.other_expenses, record.total_fuel_cost])

    @api.depends('kms_traveled', 'fuel_volume')
    def _compute_efficiency(self):
        for record in self:
            record.efficiency = record.kms_traveled / record.fuel_volume if record.fuel_volume else 0.0

    @api.depends('total_income', 'kms_traveled')
    def _compute_income_per_km(self):
        for record in self:
            record.income_per_km = record.total_income / record.kms_traveled if record.kms_traveled else 0.0

    @api.onchange('origin_address_id')
    def _onchange_origin_address_id(self):
        """Actualizar el campo 'Origen' cuando cambie 'Dirección Origen'."""
        if self.origin_address_id:
            self.origin_place = self.origin_address_id
        else:
            self.origin_place = False

    @api.onchange('destination_address_id')
    def _onchange_destination_address_id(self):
        """Actualizar el campo 'Destino' cuando cambie 'Dirección Destino'."""
        if self.destination_address_id:
            self.destination_place = self.destination_address_id
        else:
            self.destination_place = False