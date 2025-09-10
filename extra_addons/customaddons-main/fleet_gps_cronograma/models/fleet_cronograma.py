# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

class FleetCronogramaTipo(models.Model):
    _name = 'fleet.cronograma.tipo'
    _description = 'Tipo de Maniobra'
    _order = 'name'
    _sql_constraints = [
        ('name_unique', 'unique(name)',
         'El nombre del tipo de maniobra debe ser único.'),
    ]

    name = fields.Char(string='Nombre', required=True)
    description = fields.Text(string='Descripción')
    color = fields.Integer(string='Color')

class FleetCronograma(models.Model):
    _name = 'fleet.cronograma'
    _description = 'Cronograma de Maniobras'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # -------------------------------------------------------------------------
    # CAMPOS
    # -------------------------------------------------------------------------
    sequence = fields.Char(
        string='Secuencia', readonly=True, copy=False, default=lambda self: _('Nuevo'))
    maniobra = fields.Char(string='Requerimiento', required=True)
    necesidad_entrega = fields.Date(string='Necesidad de entrega', required=True)
    numero_dias = fields.Integer(string='Número de días', default=1)

    proveedor_externo = fields.Boolean(string='Proveedor externo?')
    vehiculo_id = fields.Many2one('fleet.vehicle', string='Vehículo')
    vehicle_ref = fields.Char(
        string='Matrícula de Proveedor externo',
        tracking=True
    )

    origen = fields.Char(string='Origen')
    destino = fields.Char(string='Destino')

    peso_carga = fields.Float(string='Peso de carga')
    unidad_peso = fields.Selection(
        [('kg', 'kg'), ('ton', 'ton')], string='Unidad de peso')

    conductor_id = fields.Many2one('res.partner', string='Conductor')
    fecha_ejecucion = fields.Datetime(string='Fecha de ejecución')
    fecha_finalizacion = fields.Date(string='Fecha de finalización', readonly=True)

    tipo_ids = fields.Many2many('fleet.cronograma.tipo', string='Tipo de Maniobra')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('finalizado', 'Finalizado'),
    ], string='Estado', default='draft', tracking=True)

    fecha_estimada = fields.Date(
        string='Fecha estimada',
        compute='_compute_fecha_estimada',
        readonly=True,
        store=True,
    )
    date_stop2 = fields.Date(
        string='Fin (calendario)',
        compute='_compute_date_stop2',
        readonly=True,
        store=True,
    )
    start_readonly = fields.Date(related='necesidad_entrega', store=True, readonly=True)
    stop_readonly = fields.Date(related='date_stop2', store=True, readonly=True)

    vehicle_display = fields.Char(
        string='Vehículo / Matrícula proveedor',
        compute='_compute_vehicle_display',
        store=False,
    )
    color = fields.Integer(string='Color', compute='_compute_color', store=True)

    _COLOR_BY_STATE = {
        'draft': 2,      # amarillo
        'pending': 5,    # azul
        'approved': 3,   # verde
        'rejected': 0,   # rojo
        'finalizado': 6, # púrpura
    }
    observacion = fields.Selection(
        [(str(i), str(i)) for i in range(1, 11)],
        string='Observación',
        help="Calificación del 1 al 10"
    )
    entrega = fields.Selection(
        [('parcial', 'Parcial'), ('total', 'Total')],
        string='Entrega',
        help="Tipo de finalización"
    )
    @api.depends('state')
    def _compute_color(self):
        for rec in self:
            rec.color = self._COLOR_BY_STATE.get(rec.state, 9)

    @api.model
    def create(self, vals):
        if vals.get('sequence', _('Nuevo')) == _('Nuevo'):
            today = fields.Date.context_today(self)
            semana = f"{today.isocalendar()[1]:02}"
            mes = today.strftime('%m')
            anio = today.strftime('%y')
            vals['sequence'] = f"GPS-{semana}-{mes}-{anio}"
        rec = super().create(vals)
        rec._mail_to_admin()
        return rec

    @api.model
    def _campos_protegidos(self):
        return {
            'proveedor_externo', 'vehiculo_id', 'vehicle_ref',
            'origen', 'destino', 'peso_carga', 'unidad_peso',
            'conductor_id', 'fecha_ejecucion', 'fecha_finalizacion',
        }

    def write(self, vals):
        if not self.env.user.has_group('fleet_gps_cronograma.group_cronograma_admin'):
            protegidos = self._campos_protegidos()
            for f, v in vals.items():
                if f in protegidos and any(rec[f] != v for rec in self):
                    raise UserError(_('No tiene permisos para modificar estos campos.'))
        return super().write(vals)

    @api.depends('necesidad_entrega', 'numero_dias')
    def _compute_fecha_estimada(self):
        for rec in self:
            if rec.necesidad_entrega and rec.state != 'finalizado':
                extra = max(rec.numero_dias, 1) - 1
                rec.fecha_estimada = rec.necesidad_entrega + timedelta(days=extra)
            else:
                rec.fecha_estimada = False

    @api.depends('fecha_estimada', 'fecha_finalizacion')
    def _compute_date_stop2(self):
        for rec in self:
            rec.date_stop2 = rec.fecha_finalizacion or rec.fecha_estimada or False

    def action_send(self):
        self.write({'state': 'pending'})
        for rec in self:
            rec._mail_to_admin()

    def action_approve(self):
        self.write({'state': 'approved'})
        for rec in self:
            rec._mail_to_creator(approved=True)

    def action_reject(self):
        self.write({'state': 'rejected'})
        for rec in self:
            rec._mail_to_creator(approved=False)

    def action_finalize(self):
        vals = {'state': 'finalizado'}
        if not self.fecha_finalizacion:
            vals['fecha_finalizacion'] = fields.Datetime.now()
        self.write(vals)

    @api.constrains('numero_dias', 'tipo_ids')
    def _check_numero_dias(self):
        for rec in self:
            traslado = rec.tipo_ids.filtered(lambda t: t.name.lower() == 'traslado')
            if traslado and rec.numero_dias != 1:
                raise ValidationError(_('Si el tipo incluye "Traslado", el número de días debe ser 1.'))

    @api.depends('proveedor_externo', 'vehiculo_id', 'vehicle_ref')
    def _compute_vehicle_display(self):
        for rec in self:
            if rec.proveedor_externo:
                rec.vehicle_display = rec.vehicle_ref or ''
            else:
                rec.vehicle_display = rec.vehiculo_id.license_plate or ''

    def name_get(self):
        result = []
        for rec in self:
            tipos = ', '.join(rec.tipo_ids.mapped('name')) or _('Sin tipo')
            fecha = fields.Date.to_string(rec.necesidad_entrega) if rec.necesidad_entrega else ''
            result.append((rec.id, f"{rec.maniobra} – {tipos} – {fecha}"))
        return result

    # -------------------------------------------------------------------------
    # NOTIFICACIONES (helpers)
    # -------------------------------------------------------------------------
    def _get_mail_to(self, partner):
        if partner.email:
            return partner.email
        if getattr(partner, 'work_email', False):
            return partner.work_email
        emp = partner.employee_ids[:1]
        return emp and emp.work_email or False

    def _styled_email(self, inner_html):
        """Envuelve cualquier mail con el header, footer y el botón 'Ver registro'."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        record_url = f"{base_url}/web#id={self.id}&model=fleet.cronograma&view_type=form"
        return f"""
           <html>
             <head><meta charset="utf-8"/></head>
             <body style="font-family: Arial, sans-serif;">
               <div style="max-width:600px;margin:20px auto;
                           border:1px solid #ccc;border-radius:5px;
                           background:#F8F9FA;">
                 <div style="background:#8B0000;color:#FFF;
                             padding:15px;text-align:center;">
                   <h2 style="margin:0;font-size:22px;">Cronograma Logístico</h2>
                 </div>
                 <div style="padding:20px;color:#333;line-height:1.6;">
                   {inner_html}
                   <p><a href="{record_url}"
                         style="background:#8B0000;color:#FFF;
                                padding:10px 15px;text-decoration:none;
                                border-radius:4px;">
                        Ver registro
                      </a>
                   </p>
                 </div>
                 <div style="background:#ECECEC;text-align:center;
                             font-size:12px;color:#666;padding:10px;">
                   Mensaje automático – Cronograma Logístico
                 </div>
               </div>
             </body>
           </html>
           """

    def _styled_summary_email(self, inner_html):
        """
        Versión de _styled_email para el resumen diario:
        no incluye el botón 'Ver registro', solo envuelve tu tabla.
        """
        return f"""
        <html>
          <head><meta charset="utf-8"/></head>
          <body style="font-family: Arial, sans-serif;">
            <div style="max-width:600px;margin:20px auto;
                        border:1px solid #ccc;border-radius:5px;
                        background:#F8F9FA;">
              <div style="background:#8B0000;color:#FFF;
                          padding:15px;text-align:center;">
                <h2 style="margin:0;font-size:22px;">
                  Cronograma Logístico
                </h2>
              </div>
              <div style="padding:20px;color:#333;line-height:1.6;">
                {inner_html}
              </div>
              <div style="background:#ECECEC;text-align:center;
                          font-size:12px;color:#666;padding:10px;">
                Mensaje automático – Cronograma Logístico
              </div>
            </div>
          </body>
        </html>
        """

    def _send_email(self, subject, html_body, email_to):
        email_from = (
            self.env.user.partner_id.email
            or self.env.company.email
            or 'noreply@' + self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').split('//')[-1]
        )
        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': html_body,
            'email_to': email_to,
            'email_from': email_from,
            'author_id': self.env.user.partner_id.id,
            'auto_delete': True,
        })
        mail.sudo().send(raise_exception=False)

    # -------------------------------------------------------------------------
    # NOTIFICACIONES (al administrador y al creador)
    # -------------------------------------------------------------------------
    def _mail_to_admin(self):
        self.ensure_one()
        group = self.env.ref('fleet_gps_cronograma.group_cronograma_admin')
        emails = [u.partner_id.email for u in group.users if u.partner_id.email]
        if not emails:
            return
        subject = _('Nuevo requerimiento pendiente de aprobación')
        inner = _(
            "<p>Estimad@ Administrador/a,</p>"
            "<p>Se ha creado un nuevo <strong>requerimiento</strong> que necesita su aprobación:</p>"
            "<ul>"
            "<li><b>Requerimiento:</b> {req}</li>"
            "<li><b>Tipo(s):</b> {tipos}</li>"
            "<li><b>Necesidad de entrega:</b> {entrega}</li>"
            "<li><b>Solicitado por:</b> {creador}</li>"
            "</ul>"
        ).format(
            req=self.maniobra or _('(sin título)'),
            tipos=', '.join(self.tipo_ids.mapped('name')) or _('(sin tipo)'),
            entrega=fields.Date.to_string(self.necesidad_entrega) if self.necesidad_entrega else _('(no indica)'),
            creador=self.create_uid.name or _('Desconocido'),
        )
        self._send_email(subject, self._styled_email(inner), ','.join(emails))

    def _mail_to_creator(self, approved=True):
        self.ensure_one()
        partner = self.create_uid.partner_id
        email_to = partner.email or partner.work_email
        if not email_to:
            return
        estado = _('aprobado') if approved else _('rechazado')
        color = '#27AE60' if approved else '#C0392B'
        subject = _('Tu requerimiento ha sido %s') % estado
        inner = _(
            "<p>Hola <strong>{creador}</strong>,</p>"
            "<p>Tu requerimiento <strong>{req}</strong> ha sido "
            "<span style='color:{color};font-weight:bold;'>{estado}</span>.</p>"
            "<ul>"
            "<li><b>Tipo(s):</b> {tipos}</li>"
            "<li><b>Necesidad de entrega:</b> {entrega}</li>"
            "</ul>"
        ).format(
            creador=partner.name,
            req=self.maniobra or _('(sin título)'),
            color=color,
            estado=estado.capitalize(),
            tipos=', '.join(self.tipo_ids.mapped('name')) or _('(sin tipo)'),
            entrega=fields.Date.to_string(self.necesidad_entrega) if self.necesidad_entrega else _('(no indicada)'),
        )
        self._send_email(subject, self._styled_email(inner), email_to)

    @api.model
    def send_pending_finalization_email(self):
        """Envía un resumen diario de maniobras aprobadas pendientes de finalizar."""
        today = fields.Date.context_today(self)
        recs = self.search([
                            ('state', '=', 'approved'),
                             ('fecha_finalizacion', '=', False),
                              ('necesidad_entrega', '<=', today),
            ])
        if not recs:
            return
        group = self.env.ref('fleet_gps_cronograma.group_cronograma_admin')
        emails = [u.partner_id.email for u in group.users if u.partner_id.email]
        if not emails:
            return

        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url').rstrip('/')
        rows = ''
        for r in recs:
            overdue = r.fecha_estimada < today
            bg = 'background-color:#FFCCCC;' if overdue else ''
            url = f"{base}/fleet_cronograma/finalize/{r.id}"
            rows += f"""
                <tr>
                  <td style="…">{r.sequence}</td>
                  <td style="…">{r.maniobra}</td>
                  <td style="…">{fields.Date.to_string(r.necesidad_entrega)}</td>
                  <td style="…">{fields.Date.to_string(r.fecha_estimada)}</td>
                  <td style="border:1px solid #ccc;padding:4px;text-align:center;{bg}">
                    <a href="{url}?tipo=parcial"
                       style="background:#8B0000;color:#FFF;padding:6px 10px;
                              text-decoration:none;border-radius:4px;font-size:0.9em;margin-right:4px;">
                       Finalizar parcial
                    </a>
                    <a href="{url}?tipo=total"
                       style="background:#8B0000;color:#FFF;padding:6px 10px;
                              text-decoration:none;border-radius:4px;font-size:0.9em;">
                       Finalizar total
                    </a>
                  </td>
                </tr>
            """

        inner = f"""
            <p>Estimado/a Administrador/a,</p>
            <p>Maniobras aprobadas y pendientes de finalizar hoy:</p>
            <table style="width:100%;border-collapse:collapse;">
              <thead>
                <tr>
                  <th style="border:1px solid #ccc;padding:6px;background:#ECECEC;">Secuencia</th>
                  <th style="border:1px solid #ccc;padding:6px;background:#ECECEC;">Maniobra</th>
                  <th style="border:1px solid #ccc;padding:6px;background:#ECECEC;">Necesidad</th>
                  <th style="border:1px solid #ccc;padding:6px;background:#ECECEC;">Estimada</th>
                  <th style="border:1px solid #ccc;padding:6px;background:#ECECEC;">Acción</th>
                </tr>
              </thead>
              <tbody>{rows}</tbody>
            </table>
            """

        html = self._styled_summary_email(inner)
        self._send_email(_('Pendientes de finalización'), html, ','.join(emails))
