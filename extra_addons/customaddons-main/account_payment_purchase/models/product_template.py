# -*- coding: utf-8 -*-
# © <2024> <Washington Guijarro>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import random
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

#class ProductosSustitutos

class Product(models.Model):

    _inherit = 'product.template'
    
    verificado = fields.Boolean('Verificado?')
    referencia_anterior = fields.Char('Ref Anterior', index=True)
    referencia_company = fields.Char('Ref Interna para companias', index=True)
    nombre_alterno = fields.Char('Nombre Alterno')
    corridor = fields.Char(help="Define as the street")
    row = fields.Char(help="Define as the side within the street")
    rack = fields.Char(help="Define as the house number within the street")
    level = fields.Char(help="Define as the floor of the house")
    posx = fields.Integer(
        "Box (X)",
        help="Optional (X) coordinate of the bin if the location"
        " is split in several parts. (e.g. drawer storage)",
    )
    posy = fields.Integer(
        "Box (Y)",
        help="Optional (Y) coordinate of the bin if the location"
        " is split in several parts. (e.g. drawer storage)",
    )
    posz = fields.Integer(
        "Box (Z)",
        help="Optional (Z) coordinate of the bin if the location"
        " is split in several parts. (e.g. storage tray)",
    )
    descripcion_corta = fields.Char('Descripcion corta')
    #partida_arancelaria_id = fields.Many2one('partida_arancelaria','Partida Arancelaria')
    es_importado = fields.Boolean('Es Importado?')
    #abc_id = fields.Ma
    lead_time_fabrica = fields.Integer('Lead Time Fabrica')
    lead_time_transporte = fields.Integer('Lead Time Transporte')
    lead_time_total = fields.Integer('Lead Time Total', compute="_compute_lead_time")
    cant_minimo_pedido = fields.Integer('Cantidad Minimo Pedido')
    pais_origen = fields.Many2one('res.country','Pais Origen')

    _sql_constraints = [
        ('unique_referencia_anterior', 'unique(referencia_anterior)', 'La referencia anterior debe ser única.')
    ]

    @api.depends('lead_time_transporte', 'lead_time_fabrica')
    def _compute_lead_time(self):
        for record in self:
            try:
                # Ejemplo: lógica para calcular el valor
                record.lead_time_total = record.lead_time_fabrica + record.lead_time_transporte
            except Exception:
                record.lead_time_total = 0  # Valor predeterminado
    
    @api.onchange('referencia_anterior')
    def _onchange_referencia_anterior(self):
        # Elimina espacios en blanco en la referencia anterior al momento de ingresar el valor
        if self.referencia_anterior:
            self.referencia_anterior = self.referencia_anterior.replace(" ", "")
            
    @api.constrains('referencia_anterior')
    def _check_referencia_anterior_unique(self):
        for record in self:
            existing_references = self.search([
                ('referencia_anterior', '=', record.referencia_anterior),
                ('id', '!=', record.id)
            ])
            if existing_references:
                raise ValidationError("La referencia anterior debe ser única.")

    @api.model
    def create(self, vals):
        # Verificar si el código de referencia interna ('default_code') no está definido
        if not vals.get('default_code'):
            # Generar el código de referencia utilizando la secuencia
            sequence = self.env['ir.sequence'].next_by_code('product.internal.ref')
            vals['default_code'] = sequence  # Asignar el código secuencial al campo 'default_code'
            vals['referencia_company'] = sequence  # Asignar el código secuencial al campo 'default_code'
        if self.env.context.get("bypass_product_restrict"):
            return super(Product, self.with_context(bypass_product_restrict=True)).create(vals)
        # Llamar al método 'create' original
        return super(Product, self).create(vals)
    
    @api.model
    def generate_ean13(self, product_id):
        # Limitar el nombre del producto a 12 caracteres (EAN13 solo admite 12 dígitos)
        #random_number = ''.join([str(random.randint(0, 9)) for _ in range(12)])
        random_number = '1' + ''.join([str(random.randint(1, 9)) for _ in range(11)])

        # Calcular el dígito de control (checksum) para el número aleatorio

        evens = sum(int(random_number[i]) for i in range(1, 12, 2))
        odds = sum(int(random_number[i]) for i in range(0, 12, 2))
        checksum = (evens * 3 + odds) % 10

        if checksum != 0:
            checksum = 10 - checksum

        # Concatenar el dígito de control al número aleatorio para obtener el código completo
        ean13 = random_number + str(checksum)
        return ean13


    #comentario de generar codigo
    def generar_codigo_barra(self,product=None):
        if not product:
            filtro = """ and p.id = p.id"""
        else:
            filtro = """ and p.id = """+str(product)+""""""
        sql = """
            select p.id codproducto, 
                t.name producto,
                t.default_code,
                p.barcode,
                q.quantity cantidad
            from stock_quant q
            inner join stock_location l on q.location_id = l.id and l.usage ='internal'
            inner join product_product p on q.product_id = p.id
            inner join product_template t on t.id = p.product_tmpl_id
            where quantity>=0
            and q.in_date > '2024-01-01'
            and coalesce(product_id,0) != 0
            and p.barcode is null
            and p.active = True"""+filtro+"""
            order by 1
        """
        print(sql)
        self.env.cr.execute(sql)
        res_productos = self.env.cr.dictfetchall()
        obj_producto = self.env['product.product']
        if len(res_productos):
            for x in res_productos:
                #print 'para el producto '+x['producto']+'-'+str(x['codproducto'])+' el codigo es '+ self.generate_ean13(x['codproducto'])
                obj_producto.browse(x['codproducto']).write({'barcode':self.generate_ean13(x['codproducto'])})
        else:
            print('no hay nada a actualizar')

    def actualiza_cuenta_gasto(self):
        for x in self.env['product.template'].search([]):
            if x.property_account_expense_id.code=='AAA483' or x.property_account_expense_id.code=='2170212':
                x.property_account_expense_id = None

# class ProductProduct(models.Model):
#     _inherit = 'product.product'

#     def name_get(self):
#         """
#         Sobrescribe el método name_get para mostrar solo el nombre del producto sin el código de referencia (default_code).
#         """
#         result = []
#         for product in self:
#             # Solo usar el nombre del producto
#             name = product.name
#             result.append((product.id, name))
#         return result
    
class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_stock_account_input_categ_id_consumible = fields.Many2one(
        'account.account', 'Cuenta de Ingreso para MO - Consumible', company_dependent=True,
        domain=[('deprecated', '=', False)],
        help="Esta cuenta es usada para el ingreso en el proceso de Orden de Produccion dependiendo del tipo de producto a fabricar de tipo consumible")
    property_stock_account_output_categ_id_consumible = fields.Many2one(
        'account.account', 'Cuenta de Salida para Gastos MO - Consumible', company_dependent=True,
        domain=[('deprecated', '=', False)],
        help="Esta cuenta es usada para el gasto en el proceso de Orden de Produccion dependiendo del tipo de producto a fabricar de tipo consumible")
    property_stock_account_input_categ_id_suministro = fields.Many2one(
        'account.account', 'Cuenta de Ingreso para MO - Suministro', company_dependent=True,
        domain=[('deprecated', '=', False)],
        help="Esta cuenta es usada para el ingreso en el proceso de Orden de Produccion dependiendo del tipo de producto a fabricar de tipo suninistro")
    property_stock_account_output_categ_id_suministro = fields.Many2one(
        'account.account', 'Cuenta de Salida para Gastos MO - Suministro', company_dependent=True,
        domain=[('deprecated', '=', False)],
        help="Esta cuenta es usada para el gasto en el proceso de Orden de Produccion dependiendo del tipo de producto a fabricar de tipo suministro")