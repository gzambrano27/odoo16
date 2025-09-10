from odoo.addons import decimal_precision as dp
from odoo import exceptions, _
from odoo import api, fields, models, _
from datetime import datetime


class TradeImportation(models.Model):
    _name = 'trade.importation'
    _description = 'Importations'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc, creation_date desc'

    state = fields.Selection([
        ('draft', 'BORRADOR'),
        ('confirmed', 'CONFIRMADO'),
        ('distribution', 'DISTRIBUCIÓN DE VALORES'),
        ('liquidacion', 'LIQUIDACIÓN DE COSTOS'),
        ('completed', 'COMPLETADO')
    ], 'Import Status', readonly=True, tracking=True, default='draft')

    active = fields.Boolean('Activo', default=True)

    name = fields.Char('Referencia')
    #company_id = fields.Many2one('res.company', string="Compañía", default=lambda self: self.env.user.company_id)
    company_id = fields.Many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]},default = lambda self: self.env['res.company']._company_default_get('trade.importation'))
    partner_id = fields.Many2one('res.partner', string="Proveedor", required=True)

    purchase_ids = fields.One2many('purchase.order', 'importation_id', string='Ordenes de Compra',
                                   domain="[('state','=', 'purchase'), ('partner_id', '=', partner_id)]")

    purchase_count = fields.Integer(compute='_compute_picking', string='Compras', default=0)
    country_id = fields.Many2one('res.country', string='País de Origen', tracking=True)
    regime_type_id = fields.Many2one('trade.regime', 'Regimen Aduanero',
                                     default=lambda self: self.env.ref('ecua_foreign_purchase.regime_1'), tracking=True)
    incoterm_id = fields.Many2one('account.incoterms',
                                  default=lambda self: self.env['account.incoterms'].search([('code', '=', 'CIF')],
                                                                                            limit=1), string='INCOTERM',
                                  tracking=True)
    via_id = fields.Many2one('trade.transportation.mean', 'Vía', tracking=True)
    via_id = fields.Many2one('trade.transportation.mean', 'Vía', tracking=True)
    port_id = fields.Many2one('trade.transportation.waypoint', 'Puerto de Embarque', tracking=True)
    destination_port_id = fields.Many2one('trade.transportation.waypoint', 'Puerto de Destino', tracking=True)
    weight_net = fields.Float('Peso (Kgs)', digits=dp.get_precision('Import calculations'), tracking=True)
    container_info = fields.Char('Contenedor', tracking=True)
    creation_date = fields.Date('Fecha Creación', default=fields.date.today())
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self: self.env.user, required=True)
    date_deadline = fields.Date('Fecha límite', tracking=True)
    dau_number = fields.Char('Num. DAI', help="Single Customs Declaration Number", tracking=True)

    invoice_ids = fields.One2many('account.move', 'importation_id', 'Invoices')
    invoice_count = fields.Float('Total Invoiced', compute='_compute_inv_ids')

    invoices_ids = fields.One2many('purchase.invoice', 'importation_id', 'Invoices')
    voucher_ids = fields.One2many('purchase.voucher', 'importation_id', 'Receipts')

    total_only_foreign = fields.Float(string='Total FOB', digits=dp.get_precision('Account'),
                                      compute="_compute_total_fob_values", tracking=True)
    amount_import = fields.Float(string='Cantidad Importada', tracking=True)

    importation_rnote_ids = fields.One2many('trade.importation.line', 'importation_id', 'Lineas de Pedidos')

    picking_count = fields.Integer(compute='_compute_picking', string='Recepciones', default=0)
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking', string='Receptions', copy=False)
    expenses_ids = fields.One2many('import.expense', 'importation_id', 'Gastos')
    gastos_origen = fields.Float(string='Gastos Origen', digits=dp.get_precision('Import calculations'))

    @api.depends('importation_rnote_ids')
    def _compute_total_fob_values(self):
        for record in self:
            record.total_only_foreign = sum(record.importation_rnote_ids.mapped('price_subtotal'))
            record.amount_import = sum(record.importation_rnote_ids.mapped('product_qty'))

    @api.depends('importation_rnote_ids', 'insurance_total')
    def _compute_calculate_insurance_factor(self):
        for rec in self:
            fob_total = sum(rec.importation_rnote_ids.mapped('price_subtotal'))
            rec.factor_seguro = 0.0
            if fob_total != 0.00:
                rec.factor_seguro = rec.insurance_total / fob_total

    @api.depends('importation_rnote_ids', 'freight_total')
    def _compute_calculate_factor_freight(self):
        for rec in self:
            fob_total = sum(rec.importation_rnote_ids.mapped('price_subtotal'))
            rec.factor_freight = 0.0
            if fob_total != 0.00:
                rec.factor_freight = rec.freight_total / fob_total

    @api.depends('total_only_foreign', 'insurance_total')
    def _compute_calculate_factor_distri(self):
        for record in self:
            if record.total_only_foreign != 0.00:
                record.ins_factor_distri = record.insurance_total / record.total_only_foreign
            else:
                record.ins_factor_distri = 0.00

    @api.depends('freight_total', 'total_only_foreign')
    def _compute_calculate_freight_factor_distri(self):
        for record in self:
            if record.total_only_foreign != 0.00:
                record.freight_factor_distri = record.freight_total / record.total_only_foreign
            else:
                record.freight_factor_distri = 0.0

    @api.depends('aranceles_line_ids', 'freight_total')
    def _compute_factor_freight_dist(self):
        fobtotal = 0.0
        for record in self:
            for line in record.aranceles_line_ids:
                fobtotal += line.def_fob_recibido  # def_fob_item
            if fobtotal != 0.00:
                record.def_factor_freight_distribution = record.freight_total / fobtotal
            else:
                record.def_factor_freight_distribution = 0.0

    @api.depends('aranceles_line_ids', 'insurance_total')
    def _compute_def_factor_seguro_dist(self):
        fobtotal = 0.0
        for record in self:
            for line in record.aranceles_line_ids:
                fobtotal += line.def_fob_item
            if fobtotal != 0.00:
                record.def_factor_seguro_distribution = record.insurance_total / fobtotal
            else:
                record.def_factor_seguro_distribution = 0.0

    @api.depends('aranceles_line_ids', 'aranceles_line_ids.def_advalorem_usd', 'aranceles_line_ids.def_fob_item')
    def _compute_aranceles_distribution(self):
        aranceles = 0.0
        fob = 0.0
        for record in self:
            for line in record.aranceles_line_ids:
                aranceles += line.def_saveadv_usd
                fob += line.def_fob_item
            record.total_arancel_amount_distribution = aranceles
            record.total_fob_amount_distribution = fob

    @api.depends('expenses_ids')
    def _compute_total_gastos(self):
        tot = 0
        for record in self:
            for line in record.expenses_ids:
                tot = tot + line.value
        record.tot_gastos = tot

    @api.depends('total_arancel_amount_distribution', 'total_fob_amount_distribution')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost_import = record.total_arancel_amount_distribution + record.total_fob_amount_distribution
    
    @api.onchange('flete_internacional')
    def _onchange_flete_internacional(self):
        """
        Recalcula el flete internacional en las líneas de detalle en base a la participación,
        asegurándose de no duplicar valores ya existentes.
        """
        if not self.importation_rnote_ids:
            return  # No hay líneas para actualizar.

        if self.costo_tot_mercaderia == 0:
            raise exceptions.UserError(
                _("El costo total de la mercadería no puede ser 0. Por favor, verifique los datos ingresados.")
            )

        for line in self.importation_rnote_ids:
            # Verificar si la línea tiene una participación válida
            if not line.participation:
                raise exceptions.UserError(
                    _("La línea de detalle del producto %s no tiene definida una participación. "
                    "Por favor, calcule primero los porcentajes de participación.")
                    % line.product_id.display_name
                )

            # Evitar la duplicación: recalcula solo si es necesario
            nuevo_flete_internacional = self.flete_internacional * line.participation
            if line.flete_internacional != nuevo_flete_internacional:
                line.flete_internacional = nuevo_flete_internacional

    @api.onchange('seguro_aduana')
    def _onchange_seguro_aduana(self):
        """
        Recalcula el seguro de aduana en las líneas de detalle en base a la participación,
        asegurándose de no duplicar valores ya existentes.
        """
        if not self.importation_rnote_ids:
            return  # No hay líneas para actualizar.

        if self.costo_tot_mercaderia == 0:
            raise exceptions.UserError(
                _("El costo total de la mercadería no puede ser 0. Por favor, verifique los datos ingresados.")
            )

        for line in self.importation_rnote_ids:
            # Verificar si la línea tiene una participación válida
            if not line.participation:
                raise exceptions.UserError(
                    _("La línea de detalle del producto %s no tiene definida una participación. "
                    "Por favor, calcule primero los porcentajes de participación.")
                    % line.product_id.display_name
                )

            # Evitar la duplicación: recalcula solo si es necesario
            nuevo_seguro_aduana = self.seguro_aduana * line.participation
            if line.seguro_aduana != nuevo_seguro_aduana:
                line.seguro_aduana = nuevo_seguro_aduana

    @api.onchange('tot_gastos')
    def _onchange_tot_gastos(self):
        """
        Recalcula el seguro de aduana en las líneas de detalle en base a la participación,
        asegurándose de no duplicar valores ya existentes.
        """
        if not self.importation_rnote_ids:
            return  # No hay líneas para actualizar.

        if self.costo_tot_mercaderia == 0:
            raise exceptions.UserError(
                _("El costo total de la mercadería no puede ser 0. Por favor, verifique los datos ingresados.")
            )

        for line in self.importation_rnote_ids:
            # Verificar si la línea tiene una participación válida
            if not line.participation:
                raise exceptions.UserError(
                    _("La línea de detalle del producto %s no tiene definida una participación. "
                    "Por favor, calcule primero los porcentajes de participación.")
                    % line.product_id.display_name
                )

            # Evitar la duplicación: recalcula solo si es necesario
            nuevo_tot_gastos = self.tot_gastos * line.participation
            if line.gastos_total != nuevo_tot_gastos:
                line.gastos_total = nuevo_tot_gastos

    @api.depends('importation_rnote_ids','gastos_origen')
    def _compute_tot_mercaderia(self):
        for record in self:
            tot = sum(line.price_subtotal for line in record.importation_rnote_ids) + record.gastos_origen
            record.costo_tot_mercaderia = tot

            if record.costo_tot_mercaderia == 0:
                continue  # Evita divisiones por 0

            # Cálculo de costos para cada línea
            for line in record.importation_rnote_ids:
                # Verificar si ya existe el porcentaje de participación
                if not line.participation:
                    participacion = line.price_subtotal / record.costo_tot_mercaderia
                    line.participation = participacion  # Guardar el porcentaje calculado
                else:
                    participacion = line.participation  # Usar el porcentaje existente

                # Cálculo de costos proporcionales
                flete_internacional = record.flete_internacional * participacion
                seguro_aduana = record.seguro_aduana * participacion
                gastos_tot = record.tot_gastos * participacion
                gastos_fob = record.gastos_origen * participacion

                # Inicialización de aranceles
                advalorem = 0
                fodinfa = 0
                arancel_total = fodinfa + advalorem

                # Actualización de la línea
                line.write({
                    'participation': participacion,
                    'flete_internacional': flete_internacional,
                    'seguro_aduana': seguro_aduana,
                    'gastos_fob': gastos_fob,
                    'gastos_total': gastos_tot,
                    'arancel': 0,
                    'advalorem': advalorem,
                    'fodinfa': fodinfa,
                    'arancel_total': arancel_total,
                })



    @api.depends('liq_fob', 'liq_flete')
    def _compute_liq_cyf(self):
        for record in self:
            record.liq_cyf = record.liq_fob + record.liq_flete

    @api.depends('liq_cyf', 'liq_insurance')
    def _compute_liq_cif(self):
        for record in self:
            record.liq_cif = record.liq_cyf + record.liq_insurance

    @api.depends('liq_cif')
    def _compute_total_liq_fodinfa(self):
        for record in self:
            record.total_liq_fodinfa = 0.005 * record.liq_cif

    @api.depends('aranceles_line_ids', 'insurance_total', 'freight_total')
    def _compute_liq_aranceles(self):  # modificar
        for record in self:
            adv = 0.00
            save = 0.00
            for line in record.aranceles_line_ids:
                adv += line.def_advalorem_usd
                save += line.def_save_usd
            record.liq_adv = adv
            record.liq_salva = save

    @api.depends('liq_adv', 'liq_salva', 'liq_cost_sa')
    def _compute_liq_total_iva(self):
        for record in self:
            record.liq_total_cost_s_iva = record.liq_cost_sa

    @api.depends('liquidation_line_ids')
    def _compute_liq_cost_sa(self):
        for record in self:
            subtotal = 0.00
            if record.liquidation_line_ids:
                for line in record.liquidation_line_ids:
                    subtotal += line.amount
            record.liq_cost_sa = subtotal

    @api.depends('liq_cif', 'liq_adv', 'liq_salva', 'total_liq_fodinfa', 'liquidation_line_ids')
    def _compute_liq_iva(self):
        for record in self:
            iva = 0.00
            if record.liquidation_line_ids:
                for line in record.liquidation_line_ids:
                    iva += line.tax
            iva_base = record.liq_cif + record.total_liq_fodinfa + record.liq_adv + record.liq_salva
            iva_import = 0.15 * iva_base
            record.liq_iva_import = iva_import
            record.liq_iva = iva_import + iva

    @api.depends('liq_total_cost_s_iva', 'liq_iva', )
    def _compute_liq_total_cost(self):
        for record in self:
            if record.liq_total_cost_s_iva and record.liq_iva:
                record.liq_total_cost = record.liq_total_cost_s_iva + record.liq_iva
            else:
                record.liq_total_cost = 0.0

    insurance_total = fields.Float('Total Insurance Value', digits=dp.get_precision('Account'), tracking=True)
    freight_total = fields.Float('Valor Flete Total', digits=dp.get_precision('Account'), tracking=True)

    factor_seguro = fields.Float('Total Freight Value', compute='_compute_calculate_insurance_factor',
                                 digits=dp.get_precision('Import factors'))
    factor_freight = fields.Float('Freight Factor',
                                  compute='_compute_calculate_factor_freight',
                                  digits=dp.get_precision('Import factors'))

    aranceles_line_ids = fields.One2many('purchase.aranceles', 'importation_id', 'Tariff Distribution')

    ins_factor_distri = fields.Float('Factor Insurance Distribution',
                                     compute='_compute_calculate_factor_distri',
                                     digits=dp.get_precision('Import factors'), )

    freight_factor_distri = fields.Float('Freight Factor',
                                         compute='_compute_calculate_freight_factor_distri',
                                         digits=dp.get_precision('Import factors'))

    def_factor_freight_distribution = fields.Float('Freight Factor',
                                                   compute='_compute_factor_freight_dist',
                                                   help='Valor Flete Definitivo/FOB Total ',
                                                   digits=dp.get_precision('Import factors'))

    def_factor_seguro_distribution = fields.Float('Insurance Factor',
                                                  compute='_compute_def_factor_seguro_dist',
                                                  help='Valor Seguro Definitivo/FOB Total ',
                                                  digits=dp.get_precision('Import factors'))

    total_arancel_amount_distribution = fields.Float('Total Tariffs', compute='_compute_aranceles_distribution',
                                                     help='Total amount tariffs',
                                                     digits=dp.get_precision('Import calculations'))

    total_fob_amount_distribution = fields.Float('Total FOB', compute='_compute_aranceles_distribution',
                                                 help='Total Amount Fob Invoice',
                                                 digits=dp.get_precision('Import calculations'))

    total_cost_import = fields.Float('Total Import Cost', compute='_compute_total_cost',
                                     digits=dp.get_precision('Import calculations'))

    # liquidacion costos
    liq_fob = fields.Float('FOB', digits=dp.get_precision('Import calculations'))
    costo_tot_mercaderia = fields.Float('Costo Tot Mercaderia', compute='_compute_tot_mercaderia', store = True, digits=dp.get_precision('Import calculations'))
    liq_flete = fields.Float('Freight', digits=dp.get_precision('Import calculations'))
    flete_internacional = fields.Float('Flete Internacional', digits=dp.get_precision('Import calculations'))
    liq_cyf = fields.Float('FOB+Freight', compute='_compute_liq_cyf',
                           help='FOB Value + Freight Value',
                           digits=dp.get_precision('Import calculations'))
    liq_insurance = fields.Float('Insurance', digits=dp.get_precision('Import calculations'))
    seguro_aduana = fields.Float('Seguro Aduana', digits=dp.get_precision('Import calculations'))
    tot_gastos = fields.Float('Gastos', compute='_compute_total_gastos', digits=dp.get_precision('Import calculations'), store = True)
    liq_cif = fields.Float('CIF', compute='_compute_liq_cif',
                           help='FOB Value + Freight + Insurance', digits=dp.get_precision('Import calculations'))

    liq_date = fields.Date('Settlement Date', tracking=True)
    liquidation_line_ids = fields.One2many('purchase.liquidation', 'importation_id', 'Settlement Lines')

    total_liq_fodinfa = fields.Float('FODINFA', compute='_compute_total_liq_fodinfa',
                                     help='0.5% of the CIF value',
                                     digits=dp.get_precision('Import calculations'))

    liq_adv = fields.Float('Total advalorem', compute='_compute_liq_aranceles',
                           digits=dp.get_precision('Import calculations'))

    liq_salva = fields.Float('Total safeguard', compute='_compute_liq_advsave',
                             digits=dp.get_precision('Import calculations'))

    liq_total_cost_s_iva = fields.Float('Total costo sin IVA ', compute='_compute_liq_total_iva',
                                        help='Subtotals without VAT',
                                        digits=dp.get_precision('Import calculations'))

    liq_cost_sa = fields.Float('Total Cost without Tariffs', compute='_compute_liq_cost_sa',
                               digits=dp.get_precision('Import calculations'))

    liq_iva_import = fields.Float('VAT Import', compute='_compute_liq_iva',
                                  help='15% of CIF + FODINFA Value + Total Tariffs',
                                  store=1, digits=dp.get_precision('Import calculations'))

    liq_iva = fields.Float('Total VAT ', compute='_compute_liq_iva',
                           help='15% of CIF + FODINFA Value + Total Tariffs + VAT on additional expenses',
                           digits=dp.get_precision('Import calculations'))

    liq_total_cost = fields.Float('Total Cost', compute='_compute_liq_total_cost',
                                  help='Total Cost + VAT',
                                  digits=dp.get_precision('Import calculations'))

    def _get_default_stock_account(self):
        return self.company_id.account_importation_id

    stock_input = fields.Many2one('account.account', 'Cuenta de Ingreso de Stock',
                                  help='Puede modificar la cuenta para la importación',
                                  default=lambda self: self.env.user.company_id.account_importation_id.id,
                                  tracking=True)

    landed_cost_id = fields.Many2one('stock.landed.cost', 'Landed Cost')

    clase_importacion = fields.Many2one('clase.importacion', 'Clase Importacion')

    def carga_documentos_invoice(self):
        inv = self.env['account.move'].search([('importation_id','=',self.id)])
        for x in inv:
            if x.move_type == 'in_invoice' and x.l10n_latam_document_type_id.name=='Factura':
                line_ids = x.line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note') and l.product_id)
                product =  [i.product_id.id for i in x.line_ids.filtered(lambda l: l.product_id)]
                concepto = self.env['purchase.concept.bill'].search([('product_id','=',product)])
                
                if concepto.id not in [i.concept_id.id for i in self.invoices_ids]:
                    for line in line_ids:
                        # Aquí puedes usar el ID de la línea de factura según sea necesario
                        self.env['purchase.invoice'].create({
                            'invoice_id': x.id,
                            'importation_id': self.id,
                            'invoice_date': x.invoice_date,
                            'invoice_number': x.l10n_latam_document_number,
                            'concept_id': concepto.id,  # Ejemplo: agregar el ID de la línea
                        })
            if x.move_type == 'in_receipt':
                line_ids = x.line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note') and l.product_id)
                product =  [i.product_id.id for i in x.line_ids.filtered(lambda l: l.product_id)]
                concepto = self.env['purchase.concept.bill'].search([('product_id','=',product)])
                
                if concepto.id not in [i.concept_id.id for i in self.invoices_ids]:
                    for line in line_ids:
                        # Aquí puedes usar el ID de la línea de factura según sea necesario
                        self.env['purchase.voucher'].create({
                            'voucher_id': x.id,
                            'importation_id': self.id,
                            'payment_date': x.invoice_date,
                            'amount': x.amount_residual,
                            'concept_id': concepto.id,  # Ejemplo: agregar el ID de la línea
                        })
            

    def confirmed_importation(self):
        for order in self:
            order.write({'state': 'confirmed'})

    @api.onchange('purchase_ids')
    def onchange_purchase_ids(self):
        list = []
        self.importation_rnote_ids = [(5, 0, 0)]
        if self.purchase_ids:
            for po in self.purchase_ids:
                if not any(picking.state == 'done' for picking in po.picking_ids):
                    raise exceptions.UserError(f"La orden de compra '{po.name}' no tiene recepciones confirmadas. No se puede cargar.")
                if po.order_line:
                    for line in po.order_line:
                        prod_id = line.product_id

                        domain = []
                        domain += [('purchase_line_id', '=', line.id.origin),
                                   ('product_id', '=', prod_id.id)]

                        if self.id:
                            domain += [('importation_id', '!=', self.id)]

                        # buscar si producto ya existe en importaciones anteriores
                        po_ids = self.env['trade.importation.line'].search(domain)
                        cant_rec = 0
                        if po_ids:
                            cant_rec = sum(po_ids.mapped('product_qty'))

                        cant_pen = line.qty_received - cant_rec

                        if prod_id.type == 'product' and cant_pen > 0:
                            imp_line_data = {'orden_compra_id':line.order_id.id,
                                            'product_id': prod_id.id,
                                             'product_qty': cant_pen,
                                             'qty_total': line.product_qty,
                                             'price': line.price_unit,
                                             'tariff_id': prod_id.purchase_tariff_id.id,
                                             'purchase_line_id': line._origin.id,
                                             }
                            list.append((0, 0, imp_line_data))                            

            self.importation_rnote_ids = list
        else:
            self.importation_rnote_ids = []

    def update_purchase_ids(self):
        list = []
        self.importation_rnote_ids = [(5, 0, 0)]
        if self.purchase_ids:
            for po in self.purchase_ids:
                if po.order_line:
                    for line in po.order_line:
                        prod_id = line.product_id

                        domain = []
                        domain += [('purchase_line_id', '=', line.id),
                                   ('product_id', '=', prod_id.id)]

                        if self.id:
                            domain += [('importation_id', '!=', self.id)]

                        # buscar si producto ya existe en importaciones anteriores
                        po_ids = self.env['trade.importation.line'].search(domain)
                        cant_rec = 0
                        if po_ids:
                            cant_rec = sum(po_ids.mapped('product_qty'))

                        cant_pen = line.qty_received - cant_rec

                        if prod_id.type == 'product' and cant_pen > 0:
                            imp_line_data = {'product_id': prod_id.id,
                                             'product_qty': cant_pen,
                                             'qty_total': line.product_qty,
                                             'price': line.price_unit,
                                             'tariff_id': prod_id.purchase_tariff_id.id,
                                             'purchase_line_id': line._origin.id,
                                             }
                            list.append((0, 0, imp_line_data))

            self.importation_rnote_ids = list
        else:
            self.importation_rnote_ids = []

    def reverse_cost(self):
        def reverse_lines():
            lines = []
            for record in self.landed_cost_id.cost_lines:
                lines.append((0, 0, {
                    "product_id": record.product_id.id,
                    "name": record.product_id.name,
                    "account_id": record.account_id.id,
                    "split_method": record.split_method,
                    "price_unit": record.price_unit * -1
                },))
            return lines

        lines = reverse_lines()
        picking_ids = self.landed_cost_id.picking_ids
        landed_data = {"picking_ids": picking_ids, "cost_lines": lines, 'date': self.liq_date}
        landed = self.env["stock.landed.cost"].create(landed_data)
        landed.button_validate()
        return landed

    def set_reset_foreign(self):
        rev_cost = self.reverse_cost()
        self.write({'state': 'liquidacion', 'landed_cost_id': rev_cost.id})

    def set_print_report(self):
        return self.env.ref('ecua_foreign_purchase.report_foreign_trade').report_action(self)

    def generar_distribucion_aranceles(self):
        account_import = self.stock_input.id
        if not account_import:
            raise exceptions.UserError(
                "Seleccione una cuenta de importación")

        for record in self.importation_rnote_ids:
            print('calculos')
            participacion = (record.price_subtotal / self.costo_tot_mercaderia)
            flete_internacional = self.flete_internacional * participacion
            seguro_aduana = self.seguro_aduana * participacion
            gastos_tot = self.tot_gastos * participacion
            gastos_fob = self.gastos_origen * participacion
            advalorem = 0
            fodinfa = 0
            arancel_total = fodinfa + advalorem
            record.write({'participation': participacion,
                          'flete_internacional': flete_internacional,
                          'seguro_aduana': seguro_aduana,
                          'gastos_fob': gastos_fob,
                          'gastos_total': gastos_tot,
                          'arancel': 0,
                          'advalorem': 0,
                          'fodinfa': 0,
                          'arancel_total': arancel_total,
                          })

        self.write({'state': 'distribution'})

    def calcular_costos_importacion(self):

        if not self.stock_input:
            msg = 'Por favor ingrese la cuenta contable a la que afecta esta importación.'
            raise exceptions.UserError(msg)

        conceptos = []
        data = []
        self.liq_fob = self.total_fob_amount_distribution
        self.liq_flete = self.freight_total
        self.liq_insurance = self.insurance_total
        self.liquidation_line_ids.unlink()

        # obtener facturas asociadas a esta importacion
        po_ids = self.env['purchase.invoice'].search([('importation_id', '=', self.id)])

        # crear lineas de liquidacion por cada factura
        for invoice in po_ids:
            if invoice.concept_id:
                if invoice.concept_id.has_tax:
                    tax = 15.00
                else:
                    tax = 0.00
                liq_line_data = {
                    'concept_id': invoice.concept_id.id,
                    'amount': invoice.amount,
                    'tax_percent': tax,
                    'importation_id': self.id,
                }
                liq_id = self.env['purchase.liquidation'].create(liq_line_data)
                data.append(liq_id.id)
                conceptos.append(invoice.concept_id.id)

        # obtener recibos asociados a esta importacion
        re_ids = self.env['purchase.voucher'].search([('importation_id', '=', self.id)])

        # crear lineas de liquidacion por cada recibo
        for rec in re_ids:
            if rec.concept_id and not rec.exclude:
                if rec.concept_id.has_tax:
                    tax = 15.00
                else:
                    tax = 0.00
                liq_line_data = {
                    'concept_id': rec.concept_id.id,
                    'amount': rec.amount,
                    'tax_percent': tax,
                    'importation_id': self.id,
                }
                liq_id = self.env['purchase.liquidation'].create(liq_line_data)
                data.append(liq_id.id)
                conceptos.append(rec.concept_id.id)

        # crear linea de liquidacion para flete
        concept_freight = self.env.ref('ecua_foreign_purchase.cconcepto_2')
        if concept_freight.id not in conceptos:
            if concept_freight.has_tax:
                tax = 15.00
            else:
                tax = 0.00
            liq_line_data_freight = {
                'concept_id': concept_freight.id,
                'amount': self.liq_flete,
                'tax_percent': tax,
                'importation_id': self.id,
            }
            freight = self.env['purchase.liquidation'].create(liq_line_data_freight)
            data.append(freight.id)
            conceptos.append(concept_freight.id)

        # crear linea de liquidacion para seguro
        concept_insurance = self.env.ref('ecua_foreign_purchase.cconcepto_3')
        if concept_insurance.id not in conceptos:
            if concept_insurance.has_tax:
                tax = 15.00
            else:
                tax = 0.00
            liq_line_data_insurance = {
                'concept_id': concept_insurance.id,
                'amount': self.liq_insurance,
                'tax_percent': tax,
                'importation_id': self.id,
            }
            insurance = self.env['purchase.liquidation'].create(liq_line_data_insurance)
            data.append(insurance.id)
            conceptos.append(concept_insurance.id)
        #
        # # crear linea de liquidacion para ajustes
        # if self.adjustment_amount_fob:
        #     concept_adjust = self.env.ref('l10n_trading_ec.conc_12')
        #     liq_line_data_adjust = {
        #         'concept_id': concept_adjust.id,
        #         'amount': self.adjustment_amount_fob,
        #         'tax_percent': 0,
        #         'importation_id': self.id,
        #     }
        #     adjust = self.env['purchase.liquidation'].create(liq_line_data_adjust)
        #     data.append(adjust.id)

        # crear linea de liquidacion para FODINFA
        if self.total_liq_fodinfa:
            concept_fodinfa = self.env.ref('ecua_foreign_purchase.cconcepto_5')
            if concept_fodinfa.id not in conceptos:
                if concept_fodinfa.has_tax:
                    tax = 15.00
                else:
                    tax = 0.00
                liq_line_data_fodinfa = {
                    'concept_id': concept_fodinfa.id,
                    'amount': self.total_liq_fodinfa,
                    'tax_percent': tax,
                    'importation_id': self.id,
                }
                fodinfa = self.env['purchase.liquidation'].create(liq_line_data_fodinfa)
                data.append(fodinfa.id)
                conceptos.append(concept_fodinfa.id)

        # crear linea de liquidacion para aranceles
        if self.liq_adv:
            concept_adv = self.env.ref('ecua_foreign_purchase.cconcepto_13')
            if concept_adv.id not in conceptos:
                if concept_adv.has_tax:
                    tax = 15.00
                else:
                    tax = 0.00
                liq_line_data_adv = {
                    'concept_id': concept_adv.id,
                    'amount': self.liq_adv + self.liq_salva,
                    'tax_percent': tax,
                    'importation_id': self.id,
                }
                adv = self.env['purchase.liquidation'].create(liq_line_data_adv)
                data.append(adv.id)
                conceptos.append(concept_adv.id)

        # asociar lineas de liquidacion a la importacion
        self.liquidation_line_ids = [(6, 0, data)]

        # cambiar de estado la importacion a Liquidacion
        set_liq_date = self.liq_date or datetime.today()
        self.write({'state': 'liquidacion', 'liq_date': set_liq_date})

    def confirm_foreign(self):
        for rec in self:
            # Actualizar el costo de los productos
            for line in rec.importation_rnote_ids:
                if line.product_id:
                    # Actualizar el costo estándar del producto
                    line.product_id.standard_price = line.costo_unitario

            self.write({'state': 'completed'})

    def obtener_costos_productos(self):
        costos_total = self.landed_cost_id.valuation_adjustment_lines
        for rec in self.importation_rnote_ids:
            costos_prod = costos_total.filtered(lambda x: x.product_id == rec.product_id)
            valor = sum(costos_prod.mapped('additional_landed_cost')) / rec.product_qty
            total = valor + rec.price
            rec.price_unit_import = total
            rec.price_total_import = total * rec.product_qty

    def _generar_costos_destino_line(self):
        lines = []
        account = self.stock_input
        for record in self.liquidation_line_ids:
            if not record.concept_id.is_landed_cost:
                continue

            lines.append((0, 0, {
                "product_id": record.concept_id.product_id.id,
                "name": record.concept_id.product_id.name,
                "account_id": account.id,
                "split_method": record.split_method,
                "price_unit": record.amount
            },))
        return lines

    def _generar_costos_destino(self):
        picking_ids = self.picking_ids
        lines = self._generar_costos_destino_line()

        landed_data = {
            "picking_ids": picking_ids,
        }
        landed_data.update({"cost_lines": lines, 'date': self.liq_date, 'class_id': self.clase_importacion.id})
        landed = self.env["stock.landed.cost"].create(landed_data)
        landed.button_validate()
        self.landed_cost_id = landed.id

    def cambiar_cuenta_picking(self):
        for purchase in self:
            moves = purchase.mapped('picking_ids').mapped('move_ids').mapped('account_move_ids')
            moves.write({'state': 'draft'})
            for line in moves.mapped('line_ids'):
                if line.reconciled:
                    line.remove_move_reconcile()
                if line.credit > 0:
                    line.with_context(check_move_validity=False).account_id = self.stock_input.id
            moves.action_post()

    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        pick_ids = sum([order.picking_ids.ids for order in self], [])
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result

    def _compute_inv_ids(self):
        for rec in self:
            rec.invoice_count = 0
            moves = self.env['account.move']
            for inv in rec.invoices_ids:
                moves |= inv.invoice_id
                rec.invoice_count += inv.amount

            for inv in rec.voucher_ids:
                moves |= inv.voucher_id
                rec.invoice_count += inv.amount

    @api.depends('purchase_ids')
    def _compute_picking(self):
        for record in self:
            invoices = []
            invoiced = 0
            if record.purchase_ids:
                pickings = self.env['stock.picking']
                for order in record.purchase_ids:
                    for line in order.order_line:
                        # We keep a limited scope on purpose. Ideally, we should also use move_orig_ids and
                        # do some recursive search, but that could be prohibitive if not done correctly.
                        moves = line.move_ids | line.move_ids.mapped('returned_move_ids')
                        moves = moves.filtered(lambda r: r.state != 'cancel')
                        pickings |= moves.mapped('picking_id').filtered(lambda l: l.state == 'done')

                record.picking_ids = pickings
                record.picking_count = len(pickings)
                record.purchase_count = len(record.purchase_ids)
            else:
                record.picking_ids = []
                record.picking_count = 0
                record.purchase_count = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('trade.importation') or ('New')

        result = super().create(vals_list)

        return result


class ImportationTradeLine(models.Model):
    _name = 'trade.importation.line'

    @api.depends('price', 'product_qty')
    def _compute_fob_item(self):
        for record in self:
            record.price_subtotal = float(record.price * record.product_qty)

    orden_compra_id = fields.Many2one('purchase.order.line', 'Orden')
    product_id = fields.Many2one('product.product', 'Producto', domain="[('from_trade','=',True)]")
    partida_arancelaria = fields.Char(string='Partida Arancelaria')
    description = fields.Char(string='Description')
    qty_total = fields.Float('Cantidad Pedido', required=True)
    product_qty = fields.Float('Cantidad Recibida', required=True)
    price = fields.Float('P. Unit', digits=dp.get_precision('Import calculations'))
    price_subtotal = fields.Float('P. Total', compute='_compute_fob_item',
                                  digits=dp.get_precision('Import calculations'),
                                  store=True)
    tariff_id = fields.Many2one('purchase.tariff', 'Subpartida', related='product_id.purchase_tariff_id')
    importation_id = fields.Many2one('trade.importation', invisible=True, ondelete='cascade')
    purchase_line_id = fields.Many2one('purchase.order.line', invisible=True, ondelete='cascade')

    price_unit_import = fields.Float('P. Unit Total', digits=dp.get_precision('Import calculations'))
    price_total_import = fields.Float('P. Costo Total', digits=dp.get_precision('Import calculations'))
    participation = fields.Float(string='Participacion', digits=dp.get_precision('Import calculations'))
    
    gastos_fob = fields.Float(string='Gastos FOB', digits=dp.get_precision('Import calculations'))
    flete_internacional = fields.Float(string='Flete Internacional', digits=dp.get_precision('Import calculations'))
    seguro_aduana = fields.Float(string='Seguro Aduana', digits=dp.get_precision('Import calculations'))
    gastos_total = fields.Float(string='Gastos Total', digits=dp.get_precision('Import calculations'))
    arancel = fields.Float(string='Arancel', digits=dp.get_precision('Import calculations'), store=True)
    advalorem = fields.Float(string='Advalorem', compute='_compute_advalorem',  digits=dp.get_precision('Import calculations'), store=True)
    fodinfa = fields.Float(string='Fodinfa',  compute='_compute_advalorem', store=True, digits=dp.get_precision('Import calculations'))
    arancel_total = fields.Float(string='Arancel Total', digits=dp.get_precision('Import calculations'), compute='_compute_arancel_total', store=True)
    cif_total = fields.Float(string='CIF Total', compute='_compute_advalorem', store=True, digits=dp.get_precision('Import calculations'))
    costo_antes_isd = fields.Float(string='Costo Antes ISD', digits=dp.get_precision('Import calculations'), compute='_compute_costo_antes_isd', store=True)
    total_isd = fields.Float(string='Total ISD', digits=dp.get_precision('Import calculations'), compute='_compute_total_isd', store=True)
    costo_despues_isd = fields.Float(string='Costo Despues ISD', digits=dp.get_precision('Import calculations'), compute='_compute_costo_despues_isd', store=True)
    factor = fields.Float(string='Factor', digits=dp.get_precision('Import calculations'), compute='_compute_factor', store=True)
    costo_unitario = fields.Float(string='Costo Unitario', compute='_compute_costo_unitario', store=True, digits=dp.get_precision('Import calculations'))

    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    fob_unit_price = fields.Float(string='FOB Unit Price')
    fob_total = fields.Float(string='FOB Total', compute='_compute_fob_total', store=True, digits=dp.get_precision('Import calculations'))

    @api.depends('costo_despues_isd', 'product_qty')
    def _compute_costo_unitario(self):
        """
        Calcula el factor como la división de costo_despues_isd entre fob_total.
        """
        for line in self:
            if line.product_qty and line.product_qty != 0.0:
                line.costo_unitario = line.costo_despues_isd / line.product_qty
            else:
                line.costo_unitario = 0.0  # Evitar divisiones por cero

    @api.depends('costo_despues_isd', 'fob_total')
    def _compute_factor(self):
        """
        Calcula el factor como la división de costo_despues_isd entre fob_total.
        """
        for line in self:
            if line.fob_total and line.fob_total != 0.0:
                line.factor = line.costo_despues_isd / line.fob_total
            else:
                line.factor = 0.0  # Evitar divisiones por cero
                
    @api.depends('costo_antes_isd', 'total_isd')
    def _compute_costo_despues_isd(self):
        """
        Calcula el costo después del ISD como la suma de costo_antes_isd y total_isd.
        """
        for line in self:
            line.costo_despues_isd = (line.costo_antes_isd or 0.0) + (line.total_isd or 0.0)
            
    @api.depends('fob_total')
    def _compute_total_isd(self):
        """
        Calcula el total del ISD como el 5% del valor FOB Total.
        """
        for line in self:
            line.total_isd = (line.fob_total or 0.0) * 0.05
            
    @api.depends('gastos_total', 'fob_total', 'arancel_total')
    def _compute_costo_antes_isd(self):
        """
        Calcula el costo antes del ISD como la suma de gastos_total, fob_total y arancel_total.
        """
        for line in self:
            line.costo_antes_isd = (line.gastos_total or 0.0) + (line.fob_total or 0.0) + (line.arancel_total or 0.0)
            
    @api.depends('advalorem', 'fodinfa')
    def _compute_arancel_total(self):
        """
        Calcula el arancel total como la suma de advalorem y fodinfa.
        """
        for line in self:
            line.arancel_total = (line.advalorem or 0.0) + (line.fodinfa or 0.0)
            
    # @api.onchange('arancel','cif_total')
    # def _onchange_arancel(self):
    #     """
    #     Recalcula el campo 'advalorem' cuando cambia el campo 'arancel'.
    #     """
    #     for line in self:
    #         line.advalorem = (line.arancel * line.cif_total)/100

    @api.depends('arancel', 'fob_total', 'flete_internacional', 'seguro_aduana')
    def _compute_advalorem(self):
        for line in self:  # Iterar sobre cada registro en self
            cif = (line.fob_total or 0.0) + (line.flete_internacional or 0.0) + (line.seguro_aduana or 0.0)
            line.cif_total = cif
            line.advalorem = (line.arancel * cif) / 100 if line.arancel else 0.0
            line.fodinfa = cif * 0.5/100
            

    @api.depends('price_subtotal', 'gastos_fob')
    def _compute_fob_total(self):
        """
        Calcula el FOB Total como la suma de price_subtotal y gastos_fob.
        """
        for line in self:
            line.fob_total = line.price_subtotal + line.gastos_fob

    @api.depends('fob_total', 'flete_internacional','seguro_aduana')
    def _compute_cif_total(self):
        """
        Calcula el CIF Total como la suma de price_subtotal y gastos_fob.
        """
        for line in self:
            line.cif_total = line.fob_total + line.flete_internacional + line.seguro_aduana

    #def_adval_percents = fields.Float('Advalorem')




class ImportExpense(models.Model):
    _name = 'import.expense'
    _description = 'Import Expenses'

    importation_id = fields.Many2one('trade.importation', string='Import Order', required=True, ondelete='cascade')
    product_id =  fields.Many2one('product.product', string='Producto', domain="[('landed_cost_ok', '=', True)]") 
    invoice_number = fields.Char(string='Invoice Number')
    proveedor = fields.Many2one('res.partner', string='Proveedor')
    value = fields.Float(string='Value')


class PurchaseInvoice(models.Model):
    _name = 'purchase.invoice'

    @api.onchange('invoice_id')
    def onchange_invoice(self):
        for obj in self:
            if obj.invoice_id:
                obj.invoice_date = obj.invoice_id.invoice_date
                obj.invoice_number = obj.invoice_id.l10n_latam_document_number

    importation_id = fields.Many2one('trade.importation', 'Purchase Order', invisible=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', 'Invoice', required=True)
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        string='Supplier',
        store=True
    )
    invoice_date = fields.Date('Invoice Date', required=True)
    invoice_number = fields.Char('Invoice Number', required=True)
    percent = fields.Float('Percentage Application', default=100.00)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    amount = fields.Monetary(related='invoice_id.amount_total', string='Total with VAT', store=True, )

    concept_id = fields.Many2one('purchase.concept.bill', 'Description')


class PurchasePayment(models.Model):
    _name = 'purchase.voucher'

    importation_id = fields.Many2one('trade.importation', 'Purchase Order', invisible=True, ondelete='cascade')
    voucher_id = fields.Many2one('account.move', 'Receipts', required=True, domain="[('move_type', '=', 'in_receipt')]")
    partner_id = fields.Many2one(
        related='voucher_id.partner_id',
        string='Supplier',
        store=True
    )
    payment_date = fields.Date(related='voucher_id.invoice_date', store=True)
    percent = fields.Float('Percentage Application', default=100.00)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    amount = fields.Monetary(related='voucher_id.amount_total', string='Total', store=True,
                             digits=dp.get_precision('Account'))
    exclude = fields.Boolean('Exclude', help='Do not include in total sum')

    concept_id = fields.Many2one('purchase.concept.bill', 'Description')


class PurchaseAranceles(models.Model):
    _name = 'purchase.aranceles'

    def _get_fob_recibido(self):
        for record in self:
            return record.subtotal

    def _get_default_fob_recibido(self):
        for record in self:
            return record.def_fob_item

    @api.depends('def_fob_recibido', 'def_factor_freight_distribution', 'tariff_id')
    def _compute_def_freight(self):
        for record in self:
            record.def_freight = record.def_fob_recibido * record.def_factor_freight_distribution

    @api.depends('def_fob_recibido', 'def_factor_seguro_distribution', 'def_factor_freight_distribution')
    def _compute_def_insurance(self):
        for record in self:
            record.def_insurance = record.def_fob_recibido * record.def_factor_seguro_distribution

    @api.depends('def_insurance', 'def_fob_item', 'def_fob_recibido')
    def _compute_cif_distribution(self):
        for record in self:
            record.def_cif = float(record.def_insurance + record.def_fob_recibido)

    @api.depends('def_cif')
    def _compute_fodinfa(self):
        for record in self:
            record.def_fodinfa = float(0.005 * record.def_cif)

    @api.depends('product_id', 'def_cif', 'def_adval_percents', 'def_salva_percents')
    def _compute_save_usd_def(self):
        for record in self:
            adv = 0.0
            sav = 0.0
            if record.def_adval_percents:
                adv = record.def_cif * record.def_adval_percents / 100
            record.def_advalorem_usd = adv

            if record.def_salva_percents:
                sav = record.def_cif * record.def_salva_percents / 100
            record.def_save_usd = sav

            record.def_saveadv_usd = record.def_advalorem_usd + record.def_save_usd

    importation_id = fields.Many2one('trade.importation', 'Purchase Order', invisible=True, ondelete='cascade')

    importation_line = fields.Many2one('trade.importation.line', 'Lineas de Importacion')
    product_id = fields.Many2one('product.product', 'Product', related='importation_line.product_id', store=True, readonly=False)
    tariff_id = fields.Many2one('purchase.tariff', 'Tariff Subheading',
                                related='importation_line.product_id.purchase_tariff_id')
    qty = fields.Float('Quantity', digits=dp.get_precision('Import calculations'),
                       related='importation_line.product_qty')

    subtotal = fields.Float('FOB', digits=dp.get_precision('Import calculations'))
    subtotal_real = fields.Float('FOB Adjustment', digits=dp.get_precision('Import calculations'),
                                 default=_get_fob_recibido)

    def_salva_percents = fields.Float('Safeguard')
    def_adval_percents = fields.Float('Advalorem')

    def_freight = fields.Float('Freight/Item', digits=dp.get_precision('Import calculations'),
                               compute='_compute_def_freight')
    def_insurance = fields.Float('Ins/Item', digits=dp.get_precision('Import calculations'),
                                 compute='_compute_def_insurance')
    def_cif = fields.Float('CIF', digits=dp.get_precision('Import calculations'), compute='_compute_cif_distribution')
    def_fodinfa = fields.Float('FODINFA', digits=dp.get_precision('Import calculations'), compute='_compute_fodinfa')
    def_advalorem_usd = fields.Float('ARANC.', digits=dp.get_precision('Import calculations'),
                                     compute='_compute_save_usd_def')
    def_save_usd = fields.Float('SALVAG.', digits=dp.get_precision('Import calculations'),
                                compute='_compute_save_usd_def')

    def_saveadv_usd = fields.Float('ARANCELES', digits=dp.get_precision('Import calculations'),
                                   compute='_compute_save_usd_def')

    def_fob_item = fields.Float('FOB', digits=dp.get_precision('Import calculations'))
    def_fob_recibido = fields.Float('FOB Adjustment', digits=dp.get_precision('Import calculations'),
                                    default=_get_default_fob_recibido)
    def_factor_seguro_distribution = fields.Float('Insurance Factor', digits=dp.get_precision('Import factors'),
                                                  related='importation_id.def_factor_seguro_distribution',
                                                  help='Definitive Insurance Value/FOB Total ')
    def_factor_freight_distribution = fields.Float('Freight Factor', digits=dp.get_precision('Import factors'),
                                                   related='importation_id.def_factor_freight_distribution',
                                                   help='Definitive Freight Value/FOB Total')


class PurchaseLiquidation(models.Model):
    _name = 'purchase.liquidation'

    @api.depends('amount', 'tax')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.amount + record.tax

    def _get_iva_percent(self):
        for record in self:
            if record.concept_id.has_tax:
                def_tax = 15.0
            else:
                def_tax = 0.00
            return def_tax

    @api.depends('tax_percent', 'amount')
    def _compute_iva(self):
        for record in self:
            record.tax = record.tax_percent * record.amount / 100

    @api.onchange('concept_id')
    def _onchange_concept_id(self):
        for record in self:
            amount = record.concept_id and record.concept_id.default_value or 0.0
            record.amount = amount

            if record.concept_id.has_tax:
                record.tax_percent = 15.0
            else:
                record.tax_percent = 0.00

    concept_id = fields.Many2one('purchase.concept.bill', 'Description')
    amount = fields.Float('Amount', digits=dp.get_precision('Import calculations'))
    tax_percent = fields.Float('% VAT', default=_get_iva_percent, digits=dp.get_precision('Import calculations'))
    tax = fields.Float('VAT', compute='_compute_iva', digits=dp.get_precision('Import calculations'))
    total_amount = fields.Float('Total Value', compute='_compute_total_amount',
                                digits=dp.get_precision('Import calculations'))
    importation_id = fields.Many2one('trade.importation', invisible=True, ondelete='cascade')
    notes = fields.Text('Notes')
    split_method = fields.Selection([
        ('equal', 'Equal'),
        ('by_quantity', 'By Quantity'),
        ('by_current_cost_price', 'By Current Cost Price'),
        ('by_weight', 'By Weight'),
        ('by_volume', 'By Volume'),
    ], string="Division Method", default="by_current_cost_price")


class ImportationConcept(models.Model):
    _name = 'purchase.concept.bill'

    name = fields.Char('Description')
    has_tax = fields.Boolean('Has Taxes?', default=True)
    is_landed_cost = fields.Boolean('Is Landed Cost?', default=True,
                                    help='Affects the costs of imported products')
    default_value = fields.Float('Default value')

    product_id = fields.Many2one("product.product",
                                 string="Related Product")

    @api.model
    def create(self, vals):
        result = super(ImportationConcept, self).create(vals)
        record = {
            "name": result.name,
            "type": "service",
            "landed_cost_ok": True,
            "from_trade": True
        }
        product_id = self.env["product.product"].create(record)
        result.write({"product_id": product_id.id})
        return result

    @api.model
    def update_item(self):
        concept_ids = self.search([])
        for concept in concept_ids:
            if not concept.product_id:
                record = {"name": concept.name, "type": "service", "from_trade": True, "default_code": concept.name[:5]}
                product_id = self.env["product.product"].create(record)

                concept.write({"product_id": product_id.id})


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    importation_id = fields.Many2one('trade.importation', 'Importation', ondelete='SET NULL', copy=False)
    state_confirmed = fields.Boolean('Importación Completa', default=False, copy=False)
