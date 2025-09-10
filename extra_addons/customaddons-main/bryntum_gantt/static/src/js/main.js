/* !
 *
 * Bryntum Gantt for Odoo 5.5.0
 * Copyright(c) 2021 Bryntum AB
 * https://bryntum.com/contact
 * https://www.bryntum.com/legal/Bryntum-Odoo-Apps-EUL.pdf
 * The source code may NOT be used outside the Bryntum Gantt for Odoo app
 */

odoo.define("bryntum.gantt.widget", function (require) {
    "use strict";

    const view_registry = require("web.view_registry");
    const BasicView = require("web.BasicView");
    const BasicController = require("web.BasicController");
    const BasicRenderer = require("web.BasicRenderer");
    require("web.ajax");

    const BryntumGanttController = BasicController.extend({
        jsLibs: [
            "bryntum_gantt/static/gantt_src/js/app.js?v16.0.2.1.21",
            "bryntum_gantt/static/gantt_src/js/chunk-vendors.js?v16.0.2.1.21",
        ],
        start: function () {
            const response = this._super.apply(this, arguments);
            response
                .then(() => {
                    this.$el
                        .find(
                            ".o_cp_searchview, .o_search_options, .o_cp_pager, .o_cp_left, .o_cp_bottom_left"
                        )
                        .addClass("d-none");
                    this.$el
                        .find(".o_control_panel")
                        .addClass("d-flex justify-content-between");
                    this.$el.find(".o_cp_top").css("min-width", "250px");
                    this.$el.find(".breadcrumb").css("width", "600px");
                    this.$el
                        .find(".o_cp_bottom_right")
                        .css("justify-content", "normal");

                    this._rpc({
                        model: "project.project",
                        method: "get_bryntum_values",
                        args: [],
                    })
                        .then((br_vals) => {
                            try {
                                const week_start = parseInt(br_vals.week_start, 10);
                                if (!isNaN(week_start)) {
                                    window.o_gantt.week_start = week_start;
                                }
                                window.o_gantt.readOnly =
                                    br_vals.bryntum_readonly_project;
                                window.o_gantt.saveWbs = br_vals.bryntum_save_wbs;
                                // TODO UNDERSTAND IF THIS EVAL IS NECESSARY
                                // eslint-disable-next-line
                                eval(
                                    "window.o_gantt.config = " +
                                        br_vals.bryntum_gantt_config
                                );
                                window.o_gantt.bryntum_auto_scheduling =
                                    br_vals.bryntum_auto_scheduling;
                            } catch (err) {
                                console.log("Gantt configuration object not valid");
                            }
                            var ganttContainer = document.getElementById(
                                "bryntum-scheduler-component"
                            );
                            window.o_gantt.create_all_elements(ganttContainer);
                        })
                        .catch((err) => {
                            console.log(err);
                            var ganttContainer = document.getElementById(
                                "bryntum-scheduler-component"
                            );
                            window.o_gantt.create_all_elements(ganttContainer);
                        });
                })
                .catch((err) => {
                    console.log(err);
                    var ganttContainer = document.getElementById(
                        "bryntum-scheduler-component"
                    );
                    window.o_gantt.create_all_elements(ganttContainer);
                });
            return response;
        },
    });

    const BryntumGanttRenderer = BasicRenderer.extend({
        jsLibs: [
            "bryntum_gantt/static/gantt_src/js/app.js?v16.0.2.1.21",
            "bryntum_gantt/static/gantt_src/js/chunk-vendors.js?v16.0.2.1.21",
        ],
        init: function (parent, state) {
            this.state = state;
            return this._super.apply(this, arguments);
        },
        start: function () {
            const response = this._super.apply(this, arguments);

            const domain = this.state.domain
                ? this.state.domain.filter((el) => el[0].indexOf("project_id") !== -1)
                : [];

            this.$el.attr("id", "bryntum-scheduler-component");

            if (domain && domain.length) {
                window.o_gantt.projectID = this.get_project_id(domain);
                window.action_from_odoo = true;
            } else {
                window.o_gantt.projectID = 0;
                window.action_from_odoo = false;
            }

            if (this.state && this.state.context) {
                window.o_gantt.lang = this.state.context.lang;
            }

            return response;
        },
        updateState: function (state) {
            this.state = state;
            const response = this._super.apply(this, arguments);
            const domain = this.state.domain
                ? this.state.domain.filter((el) => el[0].indexOf("project_id") !== -1)
                : [];

            if (domain && domain.length) {
                window.o_gantt.projectID = this.get_project_id(domain);
                window.action_from_odoo = true;
            } else {
                window.o_gantt.projectID = 0;
                window.action_from_odoo = false;
            }

            return response;
        },
        destroy: function () {
            var ganttContainer = this.$el;
            if (window.o_gantt !== undefined) {
                // Linter did not accept window.x && window.x.destroy
                if (window.o_gantt.histogram) {
                    window.o_gantt.histogram.destroy();
                }
                if (window.o_gantt.gantt) {
                    window.o_gantt.gantt.destroy();
                }
                if (window.o_gantt.splitter) {
                    window.o_gantt.splitter.destroy();
                }
            }
            if (ganttContainer !== undefined) {
                while (ganttContainer.firstChild) {
                    ganttContainer.removeChild(ganttContainer.firstChild);
                }
            }
            return this._super.apply(this, arguments);
        },
        get_project_id: function (propsdomain) {
            // A very limited implementation to fetch the currently loaded project_ids
            // from odoo to gantt_view. Does not cover all possible domains.
            // normal odoo views will understand the domain as-is, while gantt-view , just
            // needs to know the ids of projects in a list. this translation is far from
            // complete , but will cover common cases, and will not fail in case of weird
            // domains, it will just load gantt without projects selected.
            var only_prj_leafs = propsdomain.filter((value) => {
                return (
                    value.length === 3 &&
                    (value[0] === "project_id" || value[0] === "display_project_id")
                );
            });
            var project_ids = [];
            only_prj_leafs.forEach((leaf) => {
                if (leaf[1] === "=") {
                    project_ids.push(leaf[2]);
                }
                if (leaf[1] === "in" && leaf[2].constructor === Array) {
                    project_ids.concat(leaf[2]);
                }
            });
            return project_ids;
        },
    });

    const BryntumGantt = BasicView.extend({
        display_name: "Bryntum Gantt",
        icon: "fa-solid fa-chart-gantt width_button",
        viewType: "BryntumGantt",
        jsLibs: [
            "bryntum_gantt/static/gantt_src/js/app.js?v16.0.2.1.21",
            "bryntum_gantt/static/gantt_src/js/chunk-vendors.js?v16.0.2.1.21",
        ],
        config: _.extend({}, BasicView.prototype.config, {
            Controller: BryntumGanttController,
            Renderer: BryntumGanttRenderer,
        }),
    });

    view_registry.add("BryntumGantt", BryntumGantt);

    return {
        Gantt: BryntumGantt,
        Renderer: BryntumGanttRenderer,
        Controller: BryntumGanttController,
    };
});
