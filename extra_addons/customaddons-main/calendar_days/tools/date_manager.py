# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime,timedelta
import time
import math
import pytz
FORMAT_TIMES="%Y-%m-%d %H:%M:%S"
FORMAT_TIMESF="%Y-%m-%d %H:%M:%S.%f"
FORMAT_DATE="%Y-%m-%d"
        
class DateManager(object):
    
    def __init__(self,date_format=FORMAT_DATE):
        self.date_format=date_format
        
    def create(self,year,month,day):
        return datetime(year, month, day)
    
    def now(self,date_format=False):
        if not date_format:
            date_format=self.date_format
        return time.strftime(date_format)
    
    def strf(self,dtDate,date_format=False):
        if not date_format:
            date_format=self.date_format
        return dtDate.strftime(date_format)
    
    def parse(self,str_date,date_format=False):
        if not date_format:
            date_format=self.date_format
        return datetime.strptime(str_date,date_format)
        
    def strDays(self,str_date_end,str_date_start,date_format=False):
        date_start = self.parse(str_date_start,date_format)
        date_end = self.parse(str_date_end,date_format)
        return self.days(date_end,date_start)
    
    def strMonths(self,str_date_end,str_date_start,date_format=False):
        date_start = self.parse(str_date_start,date_format)
        date_end = self.parse(str_date_end,date_format)
        return self.months(date_end,date_start)
    
    def strYears(self,str_date_end,str_date_start,date_format=False):
        date_start = self.parse(str_date_start,date_format)
        date_end = self.parse(str_date_end,date_format)
        return self.years(date_end,date_start)
        
    def days(self,date_end,date_start):
        date_dif = date_end - date_start
        days=date_dif.days
        return int(days)
    
    def months(self,date_end,date_start):
        date_dif = date_end - date_start
        days=date_dif.days
        return int(float(days)/12.00)
    
    def years(self,date_end,date_start):
        date_dif = date_end - date_start
        days=date_dif.days
        return int(math.floor(float(days)/365.00))
    
    def weekday(self,datevalue):
        return datevalue.weekday()
    
    def add(self,datevalue,value_add,type):
        if(type=="days"):
            return self.addDays(datevalue, value_add)
        if(type=="months"):
            return self.addMonths(datevalue, value_add)
        if(type=="years"):
            return self.addYears(datevalue, value_add)
        return None
    
    def addDays(self,datevalue,days):
        if(type(datevalue) in (str,)):
            datevalue=self.parse(datevalue)
        return datevalue+timedelta(days=days)
    
    def addMonths(self,datevalue,months):
        days=int(float(months)*30.00)
        return self.addDays(datevalue, days)
    
    def addYears(self,datevalue,years):
        days=int(float(years)*365.00)
        return self.addDays(datevalue, days)
    
    def toHHMMSS(self,timeValueFloat):
        hh="0"+str(int(timeValueFloat))
        mmTemp=(timeValueFloat-float((int(timeValueFloat))))
        mmTemp=round(((mmTemp*60.00)),0)
        mmTemp=(int(mmTemp)==60) and 0 or int(mmTemp)                
        mmTemp="0"+str(int(mmTemp))
        return "%s:%s:00" % (str(hh[hh.__len__()-2:]),str(mmTemp[mmTemp.__len__()-2:]))      
    
    def toDatetimeTZ(self,strDtTime,user_time_zone = pytz.UTC):
        if not user_time_zone:
            user_time_zone = pytz.UTC
        user_time = datetime.strptime(strDtTime, FORMAT_TIMES)
        user_time = user_time_zone.localize(user_time)
        user_time.replace(tzinfo=user_time_zone)
        return user_time.astimezone(pytz.UTC).strftime(FORMAT_TIMES)      
