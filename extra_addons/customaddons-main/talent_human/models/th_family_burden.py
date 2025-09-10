from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class ThFamily(models.AbstractModel):
    
  _name = 'th.family'



  employee_id = fields.Many2one('hr.employee', 'Employee', ondelete="cascade")
  name = fields.Char('Name', size=256, required=True,)
  birth_date = fields.Date('Birth Date')
  age = fields.Integer(string='Age')
                
    

class ThFamilyBurden(models.Model):
  _inherit="th.family"
  _name="th.family.burden"
  
  
  
  relationship = fields.Selection([
                  ('child', 'Son/Daughter'),
                  ('wife_husband', 'Wife/Husband'),
                  ('father_mother', 'Father/Mother'),
                  ],'Parentesco', default='child')
  other_relationship = fields.Char('Otra Relacion', size=256)
  type_disability = fields.Many2one('hr.disability.type','Tipo de Discapacidad')
  percent_disability = fields.Float('% Discapacidad')
  working = fields.Boolean('Trabaja?')
  email_personal = fields.Char('EmailPersonal', size=256)
  work_place = fields.Char('Lugar de Trabajo', size=200)
  work_phone = fields.Char('Telefono de Trabajo', size=32)
  cell_phone = fields.Char('Celular', size=32)
  bonus = fields.Boolean('Bonos?')
  discapacidad = fields.Boolean('Discapacidad?')
  genero = fields.Selection([
                  ('Hombre', 'Hombre'),
                  ('Mujer', 'Mujer'),
                  ('Otro', 'Otro'),
                  ],'Sexo', default='Hombre')
  para_deduccion_gastos = fields.Boolean('Para Deduccion de G. Personales?', default='True')
          
    
    
    

class ThFamilySubstitute(models.Model):
  _inherit="th.family"
  _name="th.family.substitute"
  
  
  relationship = fields.Selection([
              ('child', 'Son/Daughter'),
              ('wife_husband', 'Wife/Husband'),
              ('parent', 'Father/Mother'),
              ('grandparent', 'Grandfather/Grandmother'),
              ('couple','Couple'),
              ('other','Other'),
              ],'Relacion', default='other')
  type_disability = fields.Many2one('hr.disability.type','Tipo de Discapacidad')
  percent_disability = fields.Float('% Discapacidad')
  other_relationship = fields.Char('Otra Relacion', size=256)
        
