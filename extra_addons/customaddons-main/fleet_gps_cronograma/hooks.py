from odoo import api, fields, SUPERUSER_ID
from datetime import datetime

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # 1) Busca el modelo fleet.cronograma
    model = env['ir.model'].search([('model', '=', 'fleet.cronograma')], limit=1)
    if not model:
        return

    # 2) Busca si ya existe el cron
    cron = env['ir.cron'].search([
        ('model_id', '=', model.id),
        ('code', '=', 'model.send_pending_finalization_email()'),
    ], limit=1)

    # 3) Valores que queremos
    #    Próxima ejecución: hoy a las 03:00 (servidor). Ajústalo si lo deseas.
    nextcall = fields.Datetime.context_timestamp(
        env.user, fields.Datetime.now()
    ).replace(hour=3, minute=0, second=0).strftime('%Y-%m-%d %H:%M:%S')

    vals = {
        'name': 'Enviar resumen de finalizaciones pendientes',
        'model_id': model.id,
        'state': 'code',
        'code': 'model.send_pending_finalization_email()',
        'interval_number': 1,
        'interval_type': 'days',
        'numbercall': -1,
        'nextcall': nextcall,
        'active': True,
        'user_id': env.ref('base.user_root').id,
    }

    if cron:
        cron.write(vals)
    else:
        env['ir.cron'].create(vals)
