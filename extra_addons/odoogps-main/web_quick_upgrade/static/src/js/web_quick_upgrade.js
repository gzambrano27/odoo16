odoo.define('web_quick_upgrade.module', function(require) {
    "use strict";

    var core = require('web.core');
    var mixins = require('web.mixins');
    var rpc = require('web.rpc');
    var Session = require('web.Session');
    var QWeb = core.qweb;
    var _t = core._t;
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');

    var QuickUpgradeModule = Widget.extend({
      template: 'QuickUpgradeModule',
      events: {
        "click .oe_quick_upgrade_module": "oe_quick_upgrade_module",
      },

      oe_quick_upgrade_module: function (event) {
        event.preventDefault();
        var self = this;
        var res = rpc.query({
          model: 'quick.model.upgrade',
          method: 'action_get',
        }).then(function(result) {
          if (result) {
            self.do_action(result);
          }
        });
      },
    });

    rpc.query({
        model: 'res.users',
        method: 'has_group',
        args: ['base.group_system']
    })
    .then(function(is_employee) {
        console.log(is_employee);
        if (is_employee) {
            SystrayMenu.Items.push(QuickUpgradeModule);
        }
    });
});
