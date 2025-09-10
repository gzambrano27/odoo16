# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ..tools import CalendarManager
    
class MonthManager(object):
    
    def __init__(self,year,month):
        self.calendar_object=CalendarManager()
        self.year=year
        self.month=month
        
    def get_dict_days(self):
        return self.calendar_object.get_dict_days(self.year, self.month)
    
    def get_weeks(self):
        return self.calendar_object.get_weeks(self.year, self.month)
    
    def days(self):
        return self.calendar_object.days(self.year, self.month)
    
    def get_report_days(self):
        return self.calendar_object.get_report_days(self.year, self.month)
    
    def get_weekend_days(self):
        values=self.get_report_days()
        return values["weekend_days"]
    
    def get_worked_days(self):
        values=self.get_report_days()
        return values["worked_days"]