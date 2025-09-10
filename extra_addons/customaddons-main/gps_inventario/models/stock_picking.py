# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
from odoo.exceptions import ValidationError,UserError
from odoo import api, fields, models, _
import pytz
from datetime import datetime


class StockPicking(models.Model):
    _inherit="stock.picking"

    @api.model
    def _get_default_enable_import(self):
        return 'contact_display' in self._context

    enable_import=fields.Boolean(string="Habilitar Importación",default=_get_default_enable_import)
    force_date=fields.Datetime(copy=False,default=None,string="Fecha Recepción")
    supervisor_id = fields.Many2one('res.users', string="Supervisor")
    recibido_por = fields.Many2one('res.users', string="Recibido Por")

    def button_validate(self):
        for brw_each in self:
            if 'return' in (brw_each.picking_type_id.barcode or '').lower():
                grupo_id = self.env.ref('gps_inventario.group_devoluciones').id
                if grupo_id not in self.env.user.groups_id.ids:
                    raise ValidationError(_("No tiene permisos para validar devoluciones."))
            if 'internal' in (brw_each.picking_type_id.code or '').lower():
                grupo_id = self.env.ref('gps_inventario.group_transferencias').id
                if grupo_id not in self.env.user.groups_id.ids:
                    raise ValidationError(_("No tiene permisos para validar transferencias."))
            if 'outgoing' in (brw_each.picking_type_id.code or '').lower():
                grupo_id = self.env.ref('gps_inventario.group_despachos').id
                if grupo_id not in self.env.user.groups_id.ids:
                    raise ValidationError(_("No tiene permisos para validar despachos."))
            if not brw_each.force_date:
                raise ValidationError(_("Debes definir la Fecha de Recepción para %s") % (brw_each.name,))
            else:
                if brw_each.force_date > datetime.now():
                    raise ValidationError(_("La fecha de recepción no puede ser mayor a la fecha actual."))
            #brw_each.date_done = brw_each.force_date
            #brw_each.date_done = fields.Datetime.to_string(brw_each.force_date.replace(tzinfo=None))
            user_tz = self.env.user.tz or 'UTC'
            local_tz = pytz.timezone(user_tz)
            #brw_each.date_done = pytz.utc.localize(brw_each.force_date).astimezone(local_tz)

            # Convertir la fecha de usuario a UTC
            localized_date = brw_each.force_date.astimezone(pytz.utc)

            # Eliminar la zona horaria para que sea naive
            naive_date = localized_date.replace(tzinfo=None)

            brw_each.date_done = naive_date  # Asignar fecha sin zona horari

            # Obtener la fecha y hora actual en UTC y convertirla a la zona horaria local
            # move_line_ids_without_package = brw_each.move_line_ids_without_package
            # line_operations_to_update = move_line_ids_without_package.filtered(
            #     lambda op: op.product_id and op.qty_done != 0.00)
            # line_operations_to_update.write({"date": brw_each.force_date})
            # move_ids_without_package = brw_each.move_ids_without_package
            # operations_to_update = move_ids_without_package.filtered(lambda op: op.product_id and op.quantity_done!=0.00)
            # operations_to_update.write({"date": brw_each.force_date})
        values=super(StockPicking,self).button_validate()
        return values

    def _action_done(self):
        values=super(StockPicking,self)._action_done()
        return values

    def action_pack_operation_auto_fill(self):
        values=super(StockPicking,self).action_pack_operation_auto_fill()
        return values

    analytic_account_names = fields.Char(
        string='Cuentas Analíticas',
        compute='_compute_analytic_account_names',
        store=True
    )

    @api.depends('analytic_distribution')
    def _compute_analytic_account_names(self):
        for line in self:
            if isinstance(line.analytic_distribution, dict):
                # Obtiene los IDs de las cuentas analíticas
                analytic_account_ids = list(line.analytic_distribution.keys())
                # Busca los nombres de las cuentas analíticas utilizando esos IDs
                analytic_accounts = self.env['account.analytic.account'].search([('id', 'in', analytic_account_ids)])
                line.analytic_account_names = ', '.join(analytic_accounts.mapped('name'))
            else:
                line.analytic_account_names = ''
