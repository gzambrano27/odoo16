# -*- coding: utf-8 -*-
# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import calendar

class CalendarManager(object):
    MONDAY,TUESDAY,WEDNESDAY,THURSDAY,FRIDAY,SATURDAY,SUNDAY=0,1,2,3,4,5,6
    
    def __init__(self):
        self.cal=calendar.Calendar()
    
    def dow(self,datevalue):
        value= datevalue.weekday()
        dows={self.MONDAY:1, self.TUESDAY:2,self.WEDNESDAY:3,self.THURSDAY:4,self.FRIDAY:5,self.SATURDAY:6,self.SUNDAY:0}
        return dows[value]
            
    def get_dict_days(self,year, month):
        all_weeks=self.cal.monthdays2calendar(year, month)
        join_days=[]
        for each_week in all_weeks:
            join_days.extend(each_week)
        join_days=dict(join_days)
        if join_days.has_key(0):
            del join_days[0]        
        return join_days
    
    def get_weeks(self,year, month):
        all_weeks=self.cal.monthdayscalendar(year, month)
        dict_days=self.get_dict_days(year, month)
        weeks=[]
        index=1
        for each_week in all_weeks:
            new_week=[]
            weekend_days=0
            for each_day in each_week:
                if each_day:
                    new_week.append(each_day)
                    if (dict_days[each_day] in (self.SATURDAY,self.SUNDAY)):
                        weekend_days+=1
            if new_week:
                worked_days=new_week.__len__()-weekend_days 
                weeks.append({"week":new_week,
                              "weekend_days":weekend_days,
                              "worked_days":worked_days,
                              "all_days":worked_days+weekend_days,
                              "sequence":index,
                              "year":year,
                              "month":month})
            index+=1
        return weeks
    
    def days(self,year,month):
        month_range=calendar.monthrange(year, month)
        return month_range[1]
    
    def get_report_days(self,year,month):
        all_weeks=self.get_weeks(year, month)
        weekend_days=0
        worked_days=0
        for each_week in all_weeks: 
            weekend_days+=each_week["weekend_days"]
            worked_days+=each_week["worked_days"]
        return {"weekend_days":weekend_days,"worked_days":worked_days}
    