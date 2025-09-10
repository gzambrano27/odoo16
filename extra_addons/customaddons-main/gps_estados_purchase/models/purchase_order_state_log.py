from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrderStateLog(models.Model):
    _name = 'purchase.request.history.view'
    _description = 'Vista resumen de estados de requisiciones y órdenes'
    _order = 'documento_requisicion desc'

    documento_requisicion = fields.Many2one('purchase.request', string='Requisición')
    fecha_creacion_req = fields.Datetime('F. Creación Req.')
    usuario_creacion_req = fields.Char('Usuario Creación Req.')
    estado_creacion_req = fields.Char('Estado Creación Req.')
    fecha_envio_aprobacion_req = fields.Datetime('F. Envío Aprobación Req.')
    usuario_envio_aprobacion_req = fields.Char('Usuario Envío Req.')
    estado_envio_aprobacion_req = fields.Char('Estado Envío Req.')
    fecha_aprobacion_req = fields.Datetime('F. Aprobación Req.')
    usuario_aprobacion_req = fields.Char('Usuario Aprobación Req.')
    estado_aprobacion_req = fields.Char('Estado Aprobación Req.')

    documento_oc = fields.Char('Órdenes de Compra')
    fecha_creacion_oc = fields.Datetime('F. Creación OC')
    usuario_creacion_oc = fields.Char('Usuario Creación OC')
    estado_creacion_oc = fields.Char('Estado Creación OC')

    fecha_creacion_sdp = fields.Datetime('F. Creación SdP')
    usuario_creacion_sdp = fields.Char('Usuario Creación SdP')
    estado_creacion_sdp = fields.Char('Estado Creación SdP')

    fecha_control_presupuesto = fields.Datetime('F. Control Presupuesto')
    usuario_control_presupuesto = fields.Char('Usuario CP')
    estado_control_presupuesto = fields.Char('Estado CP')

    fecha_envio_aprobacion_oc = fields.Datetime('F. Envío Aprobación OC')
    usuario_envio_aprobacion_oc = fields.Char('Usuario Envío OC')
    estado_envio_aprobacion_oc = fields.Char('Estado Envío OC')

    fecha_aprobacion_oc = fields.Datetime('F. Aprobación OC')
    usuario_aprobacion_oc = fields.Char('Usuario Aprobación OC')
    estado_aprobacion_oc = fields.Char('Estado Aprobación OC')


    def sync_purchase_state_logs_by_date(self, date_str):
        """Sincroniza cambios de estado de requisiciones en un solo listado por cada res_id."""
        self.env['purchase.request.history.view'].search([]).unlink()
        try:
            start_dt = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            raise UserError("Formato de fecha inválido. Usa AAAA-MM-DD")

        end_dt = start_dt + timedelta(days=1)

        Message = self.env['mail.message']
        #PurchaseRequest = self.env['purchase.request']
        PurchaseRequest = self.env['purchase.request'].with_context(active_test=False).sudo()
        active_company_id = self.env.company.id

        # Obtener todos los mensajes del día y del modelo purchase.request
        messages = Message.sudo().search([
            ('model', '=', 'purchase.request'),
            #('date', '>=', start_dt),
            #('date', '<', end_dt),
            ('message_type', '=', 'notification'),
            #('res_id', '=', 4091),
        ], order="date asc")

        # Agrupar mensajes por requisición (res_id)
        grouped_msgs = {}
        for msg in messages:
            grouped_msgs.setdefault(msg.res_id, []).append(msg)

        # Procesar cada requisición
        for res_id, msg_list in grouped_msgs.items():
            #request = PurchaseRequest.browse(res_id)
            request = PurchaseRequest.browse(res_id).exists()
            if not request or request.company_id.id != active_company_id:
                continue

            data_row = {
                'documento_requisicion': res_id,
                'fecha_creacion_req': False,
                'usuario_creacion_req': False,
                'estado_creacion_req': '',
                'fecha_envio_aprobacion_req': False,
                'usuario_envio_aprobacion_req': '',
                'estado_envio_aprobacion_req': '',
                'fecha_aprobacion_req': False,
                'usuario_aprobacion_req': '',
                'estado_aprobacion_req': '',
                'documento_oc': False,
                'fecha_creacion_oc': False,
                'usuario_creacion_oc': False,
                'estado_creacion_oc': False,
                'fecha_creacion_sdp': False,
                'usuario_creacion_sdp': False,
                'estado_creacion_sdp': False,
                'fecha_control_presupuesto': False,
                'usuario_control_presupuesto': '',
                'estado_control_presupuesto': '',
                'fecha_envio_aprobacion_oc': False,
                'usuario_envio_aprobacion_oc': '',
                'estado_envio_aprobacion_oc': '',
                'fecha_aprobacion_oc': False,
                'usuario_aprobacion_oc': '',
                'estado_aprobacion_oc': '',
            }

            for msg in msg_list:
                for track in msg.tracking_value_ids.filtered(lambda t: t.field.name == 'state'):
                    try:
                        usr = self.env['res.users'].search([('partner_id', '=', msg.author_id.id)], limit=1)
                        if not usr:
                            continue

                        old = track.old_value_char
                        if old == 'Borrador' and not data_row['fecha_creacion_req']:
                            data_row['fecha_creacion_req'] = msg.date
                            data_row['usuario_creacion_req'] = usr.name
                            data_row['estado_creacion_req'] = old
                        elif old == 'Para ser aprobado' and not data_row['fecha_envio_aprobacion_req']:
                            data_row['fecha_envio_aprobacion_req'] = msg.date
                            data_row['usuario_envio_aprobacion_req'] = usr.name
                            data_row['estado_envio_aprobacion_req'] = old
                        elif old == 'Aprobado' and not data_row['fecha_aprobacion_req']:
                            data_row['fecha_aprobacion_req'] = msg.date
                            data_row['usuario_aprobacion_req'] = usr.name
                            data_row['estado_aprobacion_req'] = old
                    except Exception as e:
                        _logger.warning("Error procesando mensaje %s de requisición %s: %s", msg.id, res_id, str(e))

            #print(data_row)  # o agregar a una lista si deseas retornarlos todos juntos
            # --- Buscar órdenes de compra asociadas desde las líneas ---
            order_ids = request.line_ids.mapped('purchase_lines.order_id').filtered(
                lambda o: o.company_id.id == active_company_id
            )

            oc_ids = []  # lista de IDs como texto
            for order in order_ids:
                oc_ids.append(order.name)
                order_msgs = Message.sudo().search([
                    ('model', '=', 'purchase.order'),
                    ('res_id', '=', order.id),
                    #('date', '>=', start_dt),
                    #('date', '<', end_dt),
                    ('message_type', '=', 'notification'),
                ], order="date asc")

                for msg in order_msgs:
                    for track in msg.tracking_value_ids.filtered(lambda t: t.field.name == 'state'):
                        try:
                            usr = self.env['res.users'].search([('partner_id', '=', msg.author_id.id)], limit=1)
                            if not usr:
                                continue
                            old = track.old_value_char
                            if old == 'SdP' and not data_row['fecha_creacion_sdp']:
                                data_row['fecha_creacion_sdp'] = msg.date
                                data_row['usuario_creacion_sdp'] = usr.name
                                data_row['estado_creacion_sdp'] = old
                            elif old == 'Control Presupuesto' and not data_row['fecha_control_presupuesto']:
                                data_row['fecha_control_presupuesto'] = msg.date
                                data_row['usuario_control_presupuesto'] = usr.name
                                data_row['estado_control_presupuesto'] = old
                            elif old == 'Para aprobar' and not data_row['fecha_envio_aprobacion_oc']:
                                data_row['fecha_envio_aprobacion_oc'] = msg.date
                                data_row['usuario_envio_aprobacion_oc'] = usr.name
                                data_row['estado_envio_aprobacion_oc'] = old
                            elif old == 'Orden de Compra' and not data_row['fecha_aprobacion_oc']:
                                data_row['fecha_aprobacion_oc'] = msg.date
                                data_row['usuario_aprobacion_oc'] = usr.name
                                data_row['estado_aprobacion_oc'] = old
                        except Exception as e:
                            _logger.warning("Error en orden %s: %s", order.id, str(e))
                    # Detectar mensaje especial "Orden de compra creado"
                    if 'Orden de compra creado' in (msg.body or '') and not data_row['fecha_creacion_oc']:
                        try:
                            usr = self.env['res.users'].search([('partner_id', '=', msg.author_id.id)], limit=1)
                            data_row['fecha_creacion_oc'] = msg.date
                            data_row['usuario_creacion_oc'] = usr.name
                            data_row['estado_creacion_oc'] = 'Creado'  # o usa un estado especial si prefieres
                        except Exception as e:
                            _logger.warning("Error en mensaje de creación OC %s: %s", order.id, str(e))
            data_row['documento_oc'] = ', '.join(oc_ids) if oc_ids else False
            print(data_row)
            self.env['purchase.request.history.view'].create(data_row)



class PurchaseStateLogSyncWizard(models.TransientModel):
    _name = 'purchase.state.log.sync.wizard'
    _description = 'Sincronizar historial de estados por día'

    date = fields.Date(string='Fecha a revisar', required=True, default=fields.Date.today)

    def action_sync(self):
        self.env['purchase.request.history.view'].sync_purchase_state_logs_by_date(self.date.strftime('%Y-%m-%d'))