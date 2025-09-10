from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class ThEducationArea(models.Model):
    _name = 'th.education.area'       
    
    name = fields.Char('Name', size=255, )
                      

class ThEducationLevel(models.Model):
    _name="th.education.level"
    
    title = fields.Char('Titulo', size=255)
    country_id = fields.Many2one('res.country', 'Country')
    institution = fields.Char('Institucion', size=255, )
    start_date = fields.Date('Fecha Inicio')
    end_date = fields.Date('Fecha Fin')
    level = fields.Selection([
        ('primary','Primary education'),
        ('secondary','Secondary education'),
        ('higher','Higher education'),
        ('bachelor',"Bachelor's"),
        ('master',"Master's"),
        ('phd',"Ph.D."),
         ],    'Nivel de Educacion', default='primary' )
    status = fields.Selection([
        ('graduated','Graduated'),
        ('ongoing','Ongoing'),
        ('abandoned','Abandoned'),
        ],    'Estado', default='ongoing')
    education_area_id = fields.Many2one('th.education.area', 'Area de Educacion', )
    employee_id = fields.Many2one('hr.employee', 'Employee',)
    
    
    
    

