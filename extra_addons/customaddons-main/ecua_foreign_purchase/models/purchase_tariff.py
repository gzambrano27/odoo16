from odoo import exceptions, _
from odoo import api, fields, models, _


class PurchaseTariff(models.Model):
    _name = 'purchase.tariff'
    _description = 'Importation tariffs'
    _rec_name = 'ref'

    name = fields.Char('Nombre')
    ref = fields.Char('Código')
    observation = fields.Char('Observations')
    arancel_ids = fields.Many2many('type.arancel', 'tariff_purchase_rel', 'tariff_id', 'arancel_id',
                                   'Tarifa Arancelaria')


class TypeArancel(models.Model):
    _name = 'type.arancel'
    _description = 'Arancel'
    _order = "code desc"

    code = fields.Char('Code', size=50)
    name = fields.Char('Name', required=True)
    type = fields.Selection([('arancel', 'Tariff'), ('recargo', 'Surcharge'), ('iva', 'IVA')], 'Type')

    type_arancel = fields.Selection([('adv', 'Advalorem'),
                                     ('advspe', 'Specific Advalorem'),
                                     ('svg', 'Salvage'),
                                     ('svgesp', 'Specific Salvage'),
                                     ('antidumping', 'Antidumping'),
                                     ('fodinfa', 'FODINFA')
                                     ],
                                    'Tariff Type', default='adv', required=True)
    value_type = fields.Selection([
        ('fix', 'Fix'),
        ('percent', 'Percentage')], 'Type of value', default='percent', required=True)
    percent = fields.Float('Percentage', digits=(16, 4))
    value = fields.Float('Amount', digits=(16, 4))


class TipoRegimen(models.Model):
    _name = 'trade.regime.type'
    _description = 'Tipo de R\xc3\xa9gimen de Importaci\xc3\xb3n'
    _order = 'id desc'

    name = fields.Char('Nombre')
    date = fields.Date('Fecha')
    description = fields.Text('Observaciones')
    regime_ids = fields.One2many('trade.regime', 'regime_type_id', 'Reg\xc3\xadmenes')


class Regimen(models.Model):
    _name = 'trade.regime'
    _description = 'Tipo de R\xc3\xa9gimen de Importaci\xc3\xb3n'
    _order = 'id desc'

    name = fields.Char('Nombre')
    date = fields.Date('Fecha')
    description = fields.Text('Observaciones')
    regime_type_id = fields.Many2one('trade.regime.type', 'Tipo')


WAYPOINT_TYPE = [('port', 'Puerto'), ('aerport', 'Aeropuerto'), ('busstation', 'Estación de Bus'), ('dock', 'Muelle')]


class TransportationWayPoint(models.Model):
    _name = 'trade.transportation.waypoint'
    _order = 'id desc'

    name = fields.Char('Nombre')
    code = fields.Char('Código')
    country_id = fields.Many2one('res.country', string='País')
    type = fields.Selection(WAYPOINT_TYPE, string='Tipo')
    address = fields.Char('Dirección')


class TransportationMean(models.Model):
    _name = 'trade.transportation.mean'
    _order = 'id desc'

    name = fields.Char('Nombre')
    code = fields.Char('Código')
    waypoint_type = fields.Selection(WAYPOINT_TYPE, 'Tipo')


class ImportationRoute(models.Model):
    _name = 'trade.importation.route'
    _order = 'order asc'

    name = fields.Char('Ruta')
    transportation_mean_id = fields.Many2one('trade.transportation.mean', 'Transportation mean')
    type = fields.Selection(WAYPOINT_TYPE,
                            related='transportation_mean_id.waypoint_type', string='Tipo de embarque')
    country_origin_id = fields.Many2one('res.country', string='País Origen', required=True)
    waypoint_origin_id = fields.Many2one('trade.transportation.waypoint', string='Puerto de Embarque',
                                         required=True)
    country_destination_id = fields.Many2one('res.country', string='País Destino', required=True)
    waypoint_destination_id = fields.Many2one('trade.transportation.waypoint', string='Puerto Destino',
                                              required=True)
    order = fields.Integer('Sequence', help='Indica el orden para implementar las rutas', default=1)
    description = fields.Text('Observaciones')
