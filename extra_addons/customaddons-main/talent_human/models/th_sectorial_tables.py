from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ThSectorialComision(models.Model):
  _name = 'th.sectorial.commission'

  code = fields.Char('Code', size=16)
  name = fields.Char('Name', size=256)

  _sql_constraints = [('code_uniq', 'unique(code)','The code of the Sectorial Comision must be unique !'),
                      ('name_uniq', 'unique(name)','The name of the Sectorial Comision must be unique !'),
                      ]

class ThSectorialComisionTable(models.Model):
  _name = 'th.sectorial.commission.table'

  name = fields.Char('Name', size=256, required=True)
  basic_wages = fields.Float('Basic Wage', digits=(16,2), required=True, help="Basic Wage")
  sectorial_commission = fields.Many2one('th.sectorial.commission','Sectorial Comission', required=True)

class ThSectorialLegal(models.Model):
  _name = 'th.legal.wages'

  
  name = fields.Integer('Year')
  basic_wages = fields.Float('Basic Wage', digits=(16,2), help="Basic Wage")
  state = fields.Boolean('State')

  _sql_constraints = [
                      ('name_uniq', 'unique(name)','The code of the Legal Wages must be unique !'),
                      ('name_greater', 'check(name<2999)','Please enter a number into 1999 - 2999 !'),
                      ('name_lower', 'check(name>1999)','Please enter a number into 1999 - 2999 !'),
                      ]
