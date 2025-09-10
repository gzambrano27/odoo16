# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from collections import defaultdict
from datetime import timedelta
from operator import itemgetter

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError,ValidationError
from odoo.osv import expression
from odoo.osv.expression import OR
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby
import pytz
from odoo.addons.stock.models.stock_move import StockMove as StockMoveUpdate

class StockMove(models.Model):
    _inherit="stock.move"
    
    adjust_id=fields.Many2one("inventory.document.adjust","Documento Ajuste",copy=False)
    adjust_line_id=fields.Many2one("inventory.document.adjust.line","Detalle de Ajuste",copy=False)
    adjust_account_id=fields.Many2one("account.account","Cuenta de Ajuste",copy=False)
    adjust_partner_id=fields.Many2one("res.partner","Contacto de Ajuste",copy=False)
    property_stock_account_inventory_id=fields.Many2one("account.account","Cuenta de Stock",copy=False)
    
    @api.model_create_multi
    def create(self, vals_list):
        values= super(StockMove,self).create(vals_list)
        if "acct_adjust_line_id" in self._context:
            for brw_each in values:
                brw_each._write({
                    "adjust_id":self._context.get("acct_adjust_id",False),
                    "adjust_line_id":self._context.get("acct_adjust_line_id",False),
                    "adjust_account_id":self._context.get("acct_account_id",False),
                    "adjust_partner_id":self._context.get("acct_partner_id",False),
                    "property_stock_account_inventory_id":self._context.get("acct_property_stock_account_inventory_id",False) 
                    })
        return values
    
    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        values=super(StockMove,self)._prepare_account_move_vals( credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        return values

    def _action_done(self, cancel_backorder=False):
        values = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        return values

    def get_approved_date(self):
        self.ensure_one()
        #approved_date=fields.Datetime.context_timestamp(self,fields.Datetime.now())
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        # Obtener la fecha y hora actual en UTC y convertirla a la zona horaria local
        current_datetime = fields.Datetime.now()  # fields.Datetime.now() ya está en UTC
        approved_date = current_datetime.astimezone(local_tz)  # Convertir a zona horaria local

        if self.picking_id:
            if self.picking_id.force_date:
                approved_date=self.picking_id.force_date
            elif self.picking_id.date_done:
                approved_date = self.picking_id.date_done
        # Convertir `approved_date` a naive datetime (eliminar zona horaria)
        if approved_date.tzinfo:
            approved_date = approved_date.replace(tzinfo=None)
        print(approved_date)
        return approved_date


def _new_action_done(self, cancel_backorder=False):
    moves = self.filtered(lambda move: move.state == 'draft')._action_confirm()  # MRP allows scrapping draft moves
    moves = (self | moves).exists().filtered(lambda x: x.state not in ('done', 'cancel'))
    moves_ids_todo = OrderedSet()

    # Cancel moves where necessary ; we should do it before creating the extra moves because
    # this operation could trigger a merge of moves.
    for move in moves:
        if move.quantity_done <= 0 and not move.is_inventory:
            if float_compare(move.product_uom_qty, 0.0, precision_rounding=move.product_uom.rounding) == 0 or cancel_backorder:
                move._action_cancel()

    # Create extra moves where necessary
    for move in moves:
        if move.state == 'cancel' or (move.quantity_done <= 0 and not move.is_inventory):
            continue

        moves_ids_todo |= move._create_extra_move().ids

    moves_todo = self.browse(moves_ids_todo)
    moves_todo._check_company()
    # Split moves where necessary and move quants
    backorder_moves_vals = []
    for move in moves_todo:
        # To know whether we need to create a backorder or not, round to the general product's
        # decimal precision and not the product's UOM.
        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
            # Need to do some kind of conversion here
            qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done, move.product_id.uom_id, rounding_method='HALF-UP')
            new_move_vals = move._split(qty_split)
            backorder_moves_vals += new_move_vals
    backorder_moves = self.env['stock.move'].create(backorder_moves_vals)
    # The backorder moves are not yet in their own picking. We do not want to check entire packs for those
    # ones as it could messed up the result_package_id of the moves being currently validated
    backorder_moves.with_context(bypass_entire_pack=True)._action_confirm(merge=False)
    if cancel_backorder:
        backorder_moves.with_context(moves_todo=moves_todo)._action_cancel()
    moves_todo.mapped('move_line_ids').sorted()._action_done()
    # Check the consistency of the result packages; there should be an unique location across
    # the contained quants.
    for result_package in moves_todo\
                .mapped('move_line_ids.result_package_id')\
                .filtered(lambda p: p.quant_ids and len(p.quant_ids) > 1):
        if len(result_package.quant_ids.filtered(lambda q: not float_is_zero(abs(q.quantity) + abs(q.reserved_quantity), precision_rounding=q.product_uom_id.rounding)).mapped('location_id')) > 1:
            raise UserError(_('You cannot move the same package content more than once in the same transfer or split the same package into two location.'))
    if any(ml.package_id and ml.package_id == ml.result_package_id for ml in moves_todo.move_line_ids):
        self.env['stock.quant']._unlink_zero_quants()
    picking = moves_todo.mapped('picking_id')
    for each_move in moves_todo:
        each_move.write({'state': 'done', 'date': each_move.get_approved_date()})

    new_push_moves = moves_todo.filtered(lambda m: m.picking_id.immediate_transfer)._push_apply()
    if new_push_moves:
        new_push_moves._action_confirm()
    move_dests_per_company = defaultdict(lambda: self.env['stock.move'])
    for move_dest in moves_todo.move_dest_ids:
        move_dests_per_company[move_dest.company_id.id] |= move_dest
    for company_id, move_dests in move_dests_per_company.items():
        move_dests.sudo().with_company(company_id)._action_assign()

    # We don't want to create back order for scrap moves
    # Replace by a kwarg in master
    if self.env.context.get('is_scrap'):
        return moves_todo

    if picking and not cancel_backorder:
        backorder = picking._create_backorder()
        if any([m.state == 'assigned' for m in backorder.move_ids]):
            backorder._check_entire_pack()
    return moves_todo

setattr(StockMoveUpdate,"_action_done",_new_action_done)