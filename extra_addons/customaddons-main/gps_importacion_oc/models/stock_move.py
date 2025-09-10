from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    # def _account_entry_move(self, qty, description, svl_id, cost):
    #     """
    #     Ajusta la contabilidad para usar cuentas transitorias en órdenes de compra de importación.
    #     """
    #     # Determinar si la orden de compra está marcada como importación
    #     is_import = self.purchase_line_id and self.purchase_line_id.order_id.importacion
    #     am_vals_list = super()._account_entry_move(qty, description, svl_id, cost)

    #     if not am_vals_list or not svl_id:
    #         return am_vals_list

    #     # Obtener la capa de valoración
    #     layer = self.env['stock.valuation.layer'].browse(svl_id)

    #     # Si es una importación, obtener la cuenta transitoria de la categoría del producto
    #     if is_import:
    #         category = self.product_id.categ_id
    #         transit_account_id = category.import_account_transit_debit.id

    #         if not transit_account_id:
    #             raise UserError(
    #                 "La categoría del producto '%s' no tiene configurada una cuenta transitoria de importación." 
    #                 % category.name
    #             )

    #         # Sobrescribir las cuentas contables con la cuenta transitoria
    #         company = self.env.company
    #         sm = self.with_company(company)
    #         accounts = sm.product_id.product_tmpl_id.get_product_accounts()
    #         acc_stock_in_id = transit_account_id
    #         acc_valuation_id = accounts['stock_valuation'].id
    #         journal_id = accounts['stock_journal'].id

    #         # Reemplazar los valores contables
    #         vals = sm._prepare_account_move_vals(
    #             acc_stock_in_id,
    #             acc_valuation_id,
    #             journal_id,
    #             qty,
    #             description,
    #             False,
    #             layer.value
    #         )
    #         am_vals_list.append(vals)

    #     return am_vals_list
    
    def _account_entry_move(self, qty, description, svl_id, cost):
        """
        Ajusta la contabilidad para órdenes de compra de importación y evita duplicar asientos.
        """
        # Determinar si es una importación
        is_import = self.purchase_line_id and self.purchase_line_id.order_id.importacion

        if is_import:
            # Obtener la cuenta transitoria de la categoría del producto
            category = self.product_id.categ_id
            transit_account_id = category.import_account_transit_debit.id

            if not transit_account_id:
                raise UserError(
                    "La categoría del producto '%s' no tiene configurada una cuenta transitoria de importación."
                    % category.name
                )

            # Reemplazar las cuentas contables en la configuración
            company = self.env.company
            sm = self.with_company(company)
            accounts = sm.product_id.product_tmpl_id.get_product_accounts()
            acc_stock_in_id = transit_account_id
            acc_valuation_id = accounts['stock_valuation'].id
            journal_id = accounts['stock_journal'].id

            # Crear el asiento contable solo para importación
            layer = self.env['stock.valuation.layer'].browse(svl_id)
            vals = sm._prepare_account_move_vals(
                acc_stock_in_id,
                acc_valuation_id,
                journal_id,
                qty,
                description,
                False,
                layer.value
            )
            return [vals]  # Retorna solo el asiento generado para importación

        # Si no es importación, utiliza la lógica estándar
        return super()._account_entry_move(qty, description, svl_id, cost)