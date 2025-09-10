# fleet_gps_cronograma/controllers/fleet_cronograma_controller.py
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class FleetCronogramaController(http.Controller):

    @http.route(
        ['/fleet_cronograma/finalize/<int:cron_id>'],
        type='http', auth='public', methods=['GET'], csrf=False)
    def finalize(self, cron_id, tipo=None, **kw):
        rec = request.env['fleet.cronograma'].sudo().browse(cron_id)
        if not rec or rec.state != 'approved':
            return request.make_response(
                "No se pudo finalizar: registro no existe o no está aprobado",
                headers=[('Content-Type', 'text/plain')])
        # Si vienen tipo=parcial o tipo=total, lo guardamos:
        if tipo in ('parcial', 'total'):
            rec.sudo().write({'entrega': tipo})
        # Luego hacemos la finalización habitual:
        rec.sudo().action_finalize()
        return request.redirect(
            f"/web#id={rec.id}&model=fleet.cronograma&view_type=form&menu_id="
        )
