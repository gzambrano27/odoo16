from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    day = fields.Integer('provision days')
    provision_date = fields.Date('provision date')
    week = fields.Integer ('week')
    year = fields.Integer('year')
    
    
    # @api.model
    # def _get_anio(self):
    #     currentDateTime = datetime.now()
    #     date = currentDateTime.date()
    #     year = date.strftime("%Y")
    #     return self.env['registro.anio.exportacion'].search([('name','=',str(year))]).id
        
    
    # @api.onchange('anio')
    # def changeanio(self):
    #     s = datetime.now().isocalendar()[1]
    #     sema = 0
    #     res={}
    #     if self.anio:
    #         sema = self.env['periodo.exportacion'].search([('name','=',str(s)),('anioexportacion_id','=',self.anio.id)]).id
    #         res['semana'] = sema
    #     return {'value':res}
    
      
    # @api.multi
    # def provisionar(self):
    #     self.ensure_one()
    #     date = self.fecha_provisionar if self.fecha_provisionar else datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
    #     dias = self.dias
    #     prov_move = self.copy(default={
    #         'date': date,
    #         'journal_id': self.journal_id.id,
    #         'ref': _('PROVISION DE: ') + self.name})
    #     for acm_line in prov_move.line_ids.with_context(check_move_validity=False):
    #         acm_line.write({
    #             'debit': acm_line.debit/30 * dias if acm_line.debit > 0 else 0,
    #             'credit': acm_line.credit/30 * dias if acm_line.credit > 0 else 0,
    #             'date_maturity': date
    #         })
    #     return {
    
    #             'name': _('Precio Operaciones'),
    #             'view_type': 'form',
    #             'view_mode': 'form',
    #             'view_id': self.env.ref('account.view_move_form').id,
    #             'res_model': 'account.move',
    #             'res_id': prov_move
    #             .id,
    #             'context': "{}",
    #     }