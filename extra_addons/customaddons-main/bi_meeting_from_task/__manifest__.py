# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
{
    'name' : "Meeting from Task in Odoo",
    'version' : "16.0.0.3",
    'category' : "Project",
    'summary': 'App Create Meeting from Task Create Meeting from Task and navigate to meeting and meeting to task from meeting task schedule meeting from task create task from meeting quickly meeting from issue task to meeting for task convert meeting from task meeting',
    'description' : '''
            Create Meeting from Task and navigate to meeting and meeting to task.

        task from meeting 
        create meeting from task
        meeting task
        schedule meeting from task
        create task from meeting quickly
        meeting from issue
        meeting to task
        task to meeting
        meeting for task
        

    ''',
    'author' : "BROWSEINFO",
    'website': 'https://www.browseinfo.com/demo-request?app=bi_meeting_from_task&version=16&edition=Community',
    'depends' : ['base','project','calendar'],
    'data': [
                "security/ir.model.access.csv",
                "views/project_meeting_view.xml",
             ],
    'installable': True,
    'auto_install': False,
    'live_test_url': "https://www.browseinfo.com/demo-request?app=bi_meeting_from_task&version=16&edition=Community",
    "images":['static/description/Banner.gif'],
    'license': 'OPL-1',

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
