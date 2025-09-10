(function () {
    var e = {
        6668: function (e, t, n) {
            "use strict";
            var a = n(9755);
            n(4114);
            class o {
                constructor(e) {
                    this.toProcess = e;
                    this.resourceCalendars = {};
                }
                getDayString(e) {
                    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][parseInt(e)];
                }
                getDateString(e, t = 0) {
                    const n = a.rVz.parse(`${e || "1970-01-01"}`, "YYYY-MM-DD");
                    n.setHours(parseInt(t));
                    n.setMinutes(parseInt(Math.round(t % 1 * 60)));
                    return a.rVz.format(n, "YYYY-MM-DDTHH:mm:ss");
                }
                getHourString(e) {
                    const t = a.rVz.parse(e, "YYYY-MM-DDTHH:mm:ss");
                    return a.rVz.format(t, "HH:mm");
                }
                getCalendars() {
                    const e = [];
                    for (let t = 0; t < this.toProcess.length; t++) {
                        const n = this.toProcess[t];
                        if (n.active) {
                            const t = {},
                                a = n.working_intervals;
                            for (let e = 0; e < a.length; e++) {
                                const n = a[e],
                                    o = !!n.date_from,
                                    r = o ? n.name : this.getDayString(n.day_of_week),
                                    s = this.getDateString(n.date_from, n.hour_from),
                                    i = this.getDateString(n.date_to, n.hour_to),
                                    l = n.resource_id ? "r_" + n.resource_id : "-",
                                    d = n.resource_name ? n.resource_name : "-";
                                let c = s + "|" + i + "|" + l + "|" + d;
                                if (!t[c]) {
                                    t[c] = { isWorking: !0 };
                                    if (!o) {
                                        t[c].dayNames = [];
                                    }
                                }
                                c = t[c];
                                if (o) {
                                    c.startDate = s;
                                    c.endDate = i;
                                } else if (!c.dayNames.includes(r)) {
                                    c.dayNames.push(r);
                                    c.recurrentStartDate = `On ${c.dayNames.join(", ")} at ${this.getHourString(s)}`;
                                    c.recurrentEndDate = `On ${c.dayNames.join(", ")} at ${this.getHourString(i)}`;
                                }
                            }
                            const o = n.leave_intervals;
                            for (let e = 0; e < o.length; e++) {
                                const n = o[e],
                                    a = n.date_from,
                                    r = n.date_to,
                                    s = n.resource_id ? "r_" + n.resource_id : "-",
                                    i = n.resource_name ? n.resource_name : "-";
                                let l = a + "|" + r + "|" + s + "|" + i;
                                if (!t[l]) {
                                    t[l] = { isWorking: !1 };
                                }
                                l = t[l];
                                l.startDate = a;
                                l.endDate = r;
                            }
                            const r = Object.keys(t);
                            n.intervals = [];
                            n.children = [];
                            const s = {};
                            let i = 1;
                            for (let e = 0; e < r.length; e++) {
                                const a = r[e],
                                    o = t[a],
                                    l = a.split("|"),
                                    d = l[2],
                                    c = l[3];
                                if ("-" !== d) {
                                    if (!s[d]) {
                                        s[d] = {
                                            id: n.id + "_" + i,
                                            name: c + " (" + i + ")",
                                            intervals: []
                                        };
                                        n.children.push(s[d]);
                                        this.resourceCalendars[d] = {};
                                        i++;
                                    }
                                    s[d].intervals.push(o);
                                } else {
                                    n.intervals.push(o);
                                }
                            }
                            delete n.working_intervals;
                            delete n.leave_intervals;
                            n.unspecifiedTimeIsWorking = !1;
                            e.push(n);
                        }
                    }
                    return e;
                }
            }
            n(4979);
            class r extends a.dmw {
                static get fields() {
                    return [
                        { name: "wbsValue", type: "wbs", persist: !0, alwaysWrite: !0 },
                        { name: "startDate", type: "date", alwaysWrite: !0 },
                        { name: "endDate", type: "date", alwaysWrite: !0 },
                        { name: "date_deadline", type: "date", persist: !0 },
                        { name: "isReadOnly", type: "boolean", defaultValue: !1 },
                        { name: "note", convert: e => !1 === e ? "" : e },
                        { name: "effort", defaultValue: 0, convert: e => e > 0 ? e : 0 },
                        { name: "baselineUpdates", defaultValue: 0, type: "number" },
                        { name: "project_id" },
                        { name: "state" },
                        { name: "stageId" },
                        { name: "tagIds" },
                        {
                            name: "constraintType",
                            defaultValue: null,
                            convert: e => null === e || "False" === e ? null : e
                        },
                        // Agrega los nuevos campos:
                        { name: "cost", type: "number", defaultValue: 0 },
                        { name: "quantity", type: "number", defaultValue: 0 },
                        { name: "field_1" },
                        { name: "field_2" },
                        { name: "field_3" },
                        { name: "field_4" },
                        { name: "field_5" },
                        { name: "number_field_1", type: "number" },
                        { name: "number_field_2", type: "number" },
                        { name: "number_field_3", type: "number" },
                        { name: "number_field_4", type: "number" },
                        { name: "number_field_5", type: "number" },
                        { name: "date_field_1", type: "date" },
                        { name: "date_field_2", type: "date" },
                        { name: "date_field_3", type: "date" },
                        { name: "date_field_4", type: "date" },
                        { name: "date_field_5", type: "date" },
                        { name: "bool_field_1", type: "boolean" },
                        { name: "bool_field_2", type: "boolean" },
                        { name: "bool_field_3", type: "boolean" },
                        { name: "bool_field_4", type: "boolean" },
                        { name: "bool_field_5", type: "boolean" }
                    ];
                }
                // Suma recursiva del costo
                get aggregatedCost() {
                    let total = this.cost || 0;
                    if (this.children && this.children.length) {
                        this.children.forEach(child => {
                            // Se suma el valor agregado del hijo (que a su vez suma los de sus hijos)
                            total += child.aggregatedCost;
                        });
                    }
                    return total;
                }

                // Suma recursiva de la cantidad
                get aggregatedQuantity() {
                    let total = this.quantity || 0;
                    if (this.children && this.children.length) {
                        this.children.forEach(child => {
                            total += child.aggregatedQuantity;
                        });
                    }
                    return total;
                }
                isEditable(e) {
                    return !this.isReadOnly && super.isEditable(e);
                }
                setBaseline(e) {
                    if (!this.parentId) return;
                    super.setBaseline(e);
                    const t = this.baselines;
                    if (t.count) {
                        this.baselineUpdates++;
                        t.commit();
                    }
                }
                get isLate() {
                    return this.date_deadline && Date.now() > this.date_deadline;
                }
                get isTask() {
                    return !0;
                }
                get modificationDataToWrite() {
                    const e = this.constructor.alwaysWriteFields,
                        t = this.modificationData || {};
                    e.forEach(e => {
                        t[this.getFieldDefinition(e).dataSource] = this.getFieldPersistentValue(e);
                    });
                    return t;
                }
            }
            var s = n(2505),
                i = n.n(s);
            class l extends a.NNt {
                construct(...e) {
                    super.construct(...e);
                    this.projectIds = window.o_gantt.projectID === [] ? [] : window.o_gantt.projectID || [];
                    this.loadProjectsOnly = !1;
                    this.assignmentStore.on("load", this.cleanUpAssignments);
                    this.validateResponse = !1;
                }
                onLoad({ source: e, response: t, responseOptions: n }) {
                    this.adjustStartDate(e.project, e.taskStore, !1);
                }
                cleanUpAssignments(e) {
                    const t = this.resourceStore,
                        n = [];
                    this.forEach(e => {
                        if (!t.getById(e.resourceId)) {
                            n.push(e);
                        }
                    });
                    if (n.length > 0) {
                        this.remove(n, !0);
                        this.project.clearChanges();
                    }
                }
                jsonRpc(e, t) {
                    return new Promise((n, a) => {
                        if (t.length > 0 || t.project_ids) {
                            i()
                                .post(e, {
                                    jsonrpc: "2.0",
                                    method: "call",
                                    params: { data: JSON.stringify(t) },
                                    id: parseInt(Math.random() * 10 ** 12)
                                })
                                .then(e => {
                                    if (200 === e.status && e.data.result) {
                                        if (e.data.result.success) {
                                            n(e.data.result);
                                        } else {
                                            a(e.data.result);
                                        }
                                    } else if (e.data.error) {
                                        a(e.data.error);
                                    } else {
                                        a("Something went wrong!");
                                    }
                                })
                                .catch(a);
                        } else {
                            n();
                        }
                    });
                }
                static get defaultConfig() {
                    return {
                        taskModelClass: r,
                        autoSync: !0,
                        transport: {
                            load: { url: "/bryntum_gantt/load" },
                            sync: {
                                create: "/bryntum_gantt/send/create",
                                update: "/bryntum_gantt/send/update",
                                remove: "/bryntum_gantt/send/remove"
                            }
                        },
                        listeners: {
                            change: ({ records: e, action: t, store: n, source: a, isExpand: o }) => {
                                const r = n.project?.suspendChangeEvent;
                                if ("add" !== t || r) {
                                    // no action
                                } else {
                                    if (n.isTaskStore && !o) {
                                        e.forEach(e => {
                                            const t = a.projects.getById(e.parent.project_id);
                                            if (t) {
                                                e.set("project_id", e.parent.project_id, !0);
                                                e.set("manuallyScheduled", t.realManuallyScheduled, !0);
                                            }
                                        });
                                    }
                                    if (n.isDependencyStore && ("add" === t || "update" === t)) {
                                        e.forEach(e => {
                                            if (e.fromEvent && e.toEvent) {
                                                e.set("active", e.fromEvent.project_id === e.toEvent.project_id, !0);
                                            }
                                        });
                                    }
                                    if (t && !r && n.isTaskStore && !o) {
                                        a.project.adjustStartDate(a.project, n, e);
                                    }
                                }
                            }
                        },
                        stm: { autoRecord: !0 },
                        resetUndoRedoQueuesAfterLoad: !0
                    };
                }
                sendRequest(e) {
                    const t = this,
                        n = e.type,
                        o = e.success,
                        r = e.failure,
                        s = e.data,
                        i = { success: !0, type: s.type, requestId: s.requestId },
                        l = { text: async () => i };
                    let d = {};
                    const c = e => {
                        i.success = !1;
                        i.message = e.message;
                        a.y8.show(("load" === n ? "Load error" : "Save error: ") + e.message);
                        if ("load" !== n) {
                            t.clearChanges();
                        }
                        return { error: e.message, cancelled: !0 };
                    };
                    let u;
                    if ("load" === n) {
                        d = t.transport.load.params;
                        u = new Promise((e, n) => {
                            this.jsonRpc(t.transport.load.url, d)
                                .then(t => {
                                    Object.assign(i, t);
                                    e(i);
                                })
                                .catch(n);
                        });
                    } else {
                        const e = s.updated,
                            n = s.removed,
                            a = s.added;
                        d = { updated: e, removed: n, created: a };
                        u = new Promise((o, r) => {
                            this.jsonRpc(t.transport.sync.create, a)
                                .then(a => {
                                    i.created = a;
                                    this.jsonRpc(t.transport.sync.update, e)
                                        .then(e => {
                                            i.updated = e;
                                            this.jsonRpc(t.transport.sync.remove, n)
                                                .then(e => {
                                                    i.removed = e;
                                                    t.acceptChanges();
                                                    o(i);
                                                })
                                                .catch(r);
                                        })
                                        .catch(r);
                                })
                                .catch(r);
                        });
                    }
                    return u
                        .catch(c)
                        .then(n => {
                            if (n.success) {
                                o?.call(e.thisObj || t, l, d, e);
                            } else {
                                r?.call(e.thisObj || t, l, d, e);
                            }
                        }),
                        u.abort = () => {},
                        u;
                }
                cancelRequest(e, t) {}
                encode(e) {
                    if ("load" === e.type) return e;
                    {
                        const t = e.tasks,
                            n = e.assignments,
                            o = e.dependencies,
                            r = [],
                            s = [],
                            i = [],
                            l = e => {
                                const t = r.filter(t => t.id === e)[0] || { model: { id: e }, newData: {} };
                                r.push(t);
                                return t;
                            },
                            d = e => s.indexOf(e) > -1;
                        if (t) {
                            if (t.added) {
                                [].push.apply(
                                    i,
                                    t.added.map(e => {
                                        if ("false" === e.schedulingMode) {
                                            delete e.schedulingMode;
                                        }
                                        e.id = e.$PhantomId;
                                        return e;
                                    })
                                );
                            }
                            if (t.updated) {
                                [].push.apply(
                                    r,
                                    t.updated.map(e => {
                                        const t = this.taskStore.getById(e.id);
                                        if ("false" !== e.schedulingMode && !1 !== e.schedulingMode) {
                                            // no action
                                        } else {
                                            delete e.schedulingMode;
                                        }
                                        if (!e.startDate && !e.endDate) {
                                            delete e.startDate;
                                            delete e.endDate;
                                        }
                                        if (e.baselineUpdates) {
                                            delete e.baselineUpdates;
                                            delete e.startDate;
                                            delete e.endDate;
                                            if (t && 0 !== t.duration && t.startDate && t.endDate) {
                                                e.baselines = t.baselines.map(e => {
                                                    const t = a.rVz.defaultFormat;
                                                    return {
                                                        startDate: a.rVz.format(e.startDate, t),
                                                        endDate: a.rVz.format(e.endDate, t),
                                                        name: e.name
                                                    };
                                                });
                                            }
                                        } else {
                                            delete e.baselines;
                                        }
                                        const n = e.segments || t.segments;
                                        if (n) {
                                            const t = n.map(e => {
                                                const t = a.rVz.defaultFormat;
                                                return {
                                                    startDate: a.rVz.format(e.startDate, t),
                                                    endDate: a.rVz.format(e.endDate, t),
                                                    name: e.name
                                                };
                                            });
                                            e.segments = t;
                                        } else if (null === e.segments) {
                                            e.segments = [];
                                        }
                                        return { model: { id: e.id }, newData: e };
                                    })
                                );
                            }
                            if (t.removed) {
                                [].push.apply(s, t.removed.map(e => [e.id]));
                            }
                        }
                        const c = e => {
                            if (e && !d(e.to && e.toTask)) {
                                const t = e.toTask.incomingDeps,
                                    n = l(e.to);
                                n.newData.taskLinks = [];
                                if (t) {
                                    t.forEach(e => {
                                        n.newData.taskLinks.push({
                                            from: e.from,
                                            lag: e.lag,
                                            lagUnit: e.lagUnit,
                                            to: e.to,
                                            type: e.type,
                                            active: e.active
                                        });
                                    });
                                }
                            }
                        };
                        if (o) {
                            if (o.added) {
                                o.added.forEach(e => {
                                    e.toTask = this.taskStore.getById(e.to);
                                    c(e);
                                    delete e.toTask;
                                });
                            }
                            if (o.removed) {
                                o.removed.forEach(e => {
                                    const t = this.dependencyStore.removed.idMap[e.id];
                                    c(t);
                                });
                            }
                            if (o.updated) {
                                o.updated.forEach(e => {
                                    const t = this.dependencyStore.getById(e.id);
                                    c(t);
                                });
                            }
                            this.dependencyStore.commit();
                        }
                        const u = e => {
                            if (e && !d(e.eventId)) {
                                const t = this.taskStore.getById(e.eventId);
                                if (t) {
                                    const n = t.assignments || [],
                                        a = l(e.eventId);
                                    a.newData.assignedList = null;
                                    a.newData.assignedResources = n.map(e => ({
                                        task_id: t.id,
                                        resource_id: e.resourceId,
                                        units: e.units
                                    }));
                                    a.newData.assignedResources =
                                        0 === a.newData.assignedResources.length ? [] : a.newData.assignedResources;
                                }
                            }
                        };
                        if (n) {
                            if (n.added) {
                                n.added.forEach(e => {
                                    u(e);
                                });
                            }
                            if (n.removed) {
                                n.removed.forEach(e => {
                                    const t = this.assignmentStore.removed.idMap[e.id];
                                    u(t);
                                });
                            }
                            if (n.updated) {
                                n.updated.forEach(e => {
                                    const t = this.assignmentStore.getById(e.id);
                                    u(t);
                                });
                            }
                            this.assignmentStore.commit();
                        }
                        return { added: i, removed: s, updated: r, type: e.type, requestId: e.requestId };
                    }
                }
                decode(e) {
                    if ("sync" === e.type) {
                        delete e.updated;
                        delete e.removed;
                        if (e.created) {
                            e.tasks = { rows: [] };
                            e.created.ids.forEach(t => {
                                e.tasks.rows.push({ $PhantomId: t[0], id: t[1] });
                            });
                            delete e.created;
                        }
                        return e;
                    } else {
                        const t = e;
                        if (!t) {
                            console.log(e);
                            return;
                        }
                        if (this.loadProjectsOnly) {
                            delete t.projects;
                            delete t.resources;
                            delete t.calendars;
                        } else {
                            t.projects.rows.forEach(e => {
                                e.taskTypes = new a.ilR({ data: e.taskTypes });
                                e.taskStates = new a.ilR({ data: e.taskStates });
                                e.taskTags = new a.ilR({ data: e.taskTags });
                            });
                            const eObj = t.calendars,
                                nObj = new o(eObj.toProcess);
                            delete eObj.toProcess;
                            [].push.apply(eObj.rows, nObj.getCalendars());
                            const r = (t.resources && t.resources.rows) || [];
                            r.forEach(e => {
                                if (e.avatar) {
                                    e.imageUrl = "data:image/png;base64," + atob(e.avatar);
                                    delete e.avatar;
                                }
                                e.calendar = nObj[e.id];
                            });
                        }
                        const n = (t.tasks && t.tasks.rows && t.tasks.rows) || [];
                        n.forEach(e => {
                            this.readProject(e);
                        });
                        return t;
                    }
                }
                readProject(e) {
                    const t = {};
                    t[e.id] = e;
                    e.isReadOnly = !0;
                    const n = e.id;
                    a.rVz.defaultFormat;
                    if (e.children) {
                        e.children.forEach(e => {
                            if ("project-task_0" === e.parentId) {
                                e.parentId = n;
                            }
                            if (e.schedulingMode === !1) {
                                delete e.schedulingMode;
                            }
                            if (e.segments === null) {
                                delete e.segments;
                            }
                            t[e.id] = e;
                            if (e.duration === -1) {
                                delete e.duration;
                            }
                            if (e.baselines && e.baselines.length === 0) {
                                e.baselines = [1, 2, 3].map(t => {
                                    return {
                                        name: "Version " + t,
                                        startDate: e.startDate,
                                        endDate: e.endDate
                                    };
                                });
                            }
                        });
                    }
                    e.children = [];
                    for (let a in t) {
                        let e = t[a];
                        if (!e.startDate) {
                            delete e.duration;
                        }
                        if (e.startDate && e.endDate) {
                            delete e.duration;
                        }
                        const n = t[e.parentId];
                        if (n) {
                            if (!n.children) {
                                n.children = [];
                            }
                            n.children.push(e);
                            n.children = n.children.sort((e, t) =>
                                e.parentIndex < t.parentIndex ? -1 : e.parentIndex > t.parentIndex ? 1 : 0
                            );
                        }
                    }
                    return e;
                }
                adjustStartDate(e, t, n) {
                    var o = e.getStartDate();
                    if (n !== !1) {
                        n.forEach(e => {
                            if (void 0 !== e.getStartDate()) {
                                o = e.getStartDate();
                            }
                        });
                    }
                    var r = t.min("startDate");
                    if (void 0 !== o) {
                        if (0 !== r) {
                            o = a.rVz.min(r, o);
                            e.setStartDate(o);
                        } else {
                            e.setStartDate(o);
                        }
                    } else {
                        if (0 == r) return;
                        e.setStartDate(r);
                    }
                }
            }
            class d extends a.Mzb {
                static get $name() {
                    return "TagField";
                }
                static get type() {
                    return "tagField";
                }
                static get defaultConfig() {
                    return { valueField: "id", displayField: "name", editable: !1, store: null };
                }
                get value() {
                    if (void 0 !== this.parent.project.projects._data[0]) {
                        this.store = this.parent.project.projects._data[0].taskTags;
                    }
                    let e = super.value;
                    return e;
                }
                set value(e) {
                    super.value = e;
                }
            }
            d.initClass();
            d._$name = "TagField";
            class c extends a.Mzb {
                static get $name() {
                    return "StateField";
                }
                static get type() {
                    return "stateField";
                }
                static get defaultConfig() {
                    return { valueField: "id", displayField: "name", editable: !1, store: null };
                }
                get value() {
                    if (void 0 === this.parent.project.projects._data[0] || this.store) {
                    } else {
                        this.store = this.parent.project.projects._data[0].taskStates;
                    }
                    const e = this,
                        { valueCollection: t, valueField: n } = e;
                    if (n == null) return;
                    let a;
                    a = t.count ? t.first[n] : e._lastValue;
                    return a;
                }
                set value(e) {
                    super.value = e;
                }
            }
            c.initClass();
            c._$name = "StateField";
            n(9596);
            n(298);
            n(4524);
            n(509);
            n(8136);
            n(5988);
            n(5852);
            n(7518);
            n(7827);
            n(4866);
            n(6329);
            n(9647);
            n(8343);
            n(3538);
            n(9888);
            n(324);
            n(6102);
            n(7826);
            n(6839);
            n(3665);
            n(6830);
            n(3448);
            const u = {
                localeName: "Nl",
                localeDesc: "Nederlands",
                localeCode: "nl",
                Baselines: {
                    baseline: "basis lijn",
                    Complete: "Gedaan",
                    "Delayed start by": "Uitgestelde start met",
                    Duration: "Duur",
                    End: "Einde",
                    "Overrun by": "Overschreden met",
                    Start: "Begin"
                },
                Button: {
                    Create: "Creëer",
                    "Critical paths": "Kritieke paden",
                    Edit: "Bewerk",
                    "Export to PDF": "Exporteren naar PDF",
                    Features: "Kenmerken",
                    Settings: "Instellingen"
                },
                DateColumn: { Deadline: "Deadline" },
                Field: {
                    "Find tasks by name": "Zoek taken op naam",
                    "Project start": "Start van het project"
                },
                GanttToolbar: {
                    "First select the task you want to edit":
                        "Selecteer eerst de taak die u wilt bewerken",
                    "New task": "Nieuwe taak",
                    "Pick a project": "Selecteer een project"
                },
                Indicators: { Indicators: "Indicatoren", constraintDate: "Beperking" },
                MenuItem: {
                    "Draw dependencies": "Teken afhankelijkheden",
                    "Enable cell editing": "Schakel celbewerking in",
                    "Hide schedule": "Verberg schema",
                    "Highlight non-working time": "Markeer niet-werkende tijd",
                    "Project lines": "Projectlijnen",
                    "Show baselines": "Toon basislijnen",
                    "Show progress line": "Toon voortgangslijn",
                    "Show rollups": "Rollups weergeven",
                    "Task labels": "Taaklabels"
                },
                Slider: {
                    "Animation duration ": "Animatieduur",
                    "Bar margin": "Staafmarge",
                    "Row height": "Rijhoogte"
                },
                StartDateColumn: { "Start date": "Startdatum" },
                StatusColumn: { Status: "Toestand" },
                TaskTooltip: {
                    "Scheduling Mode": "Planningsmodus",
                    Calendar: "Kalender",
                    Critical: "Kritisch"
                },
                Tooltip: {
                    "Adjust settings": "Pas instellingen aan",
                    "Collapse all": "Alles inklappen",
                    "Create new task": "Maak een nieuwe taak",
                    "Edit selected task": "Bewerk de geselecteerde taak",
                    "Expand all": "Alles uitvouwen",
                    "Highlight critical paths": "Markeer kritieke paden",
                    "Next time span": "Volgende tijdspanne",
                    "Previous time span": "Vorige tijdspanne",
                    "Toggle features": "Schakel tussen functies",
                    "Zoom in": "In zoomen",
                    "Zoom out": "Uitzoomen",
                    "Zoom to fit": "Zoom in om te passen"
                }
            };
            a.NBd.publishLocale(u);
            const p = {
                localeName: "FrFr",
                localeDesc: "Français (France)",
                localeCode: "fr-FR",
                Baselines: {
                    baseline: "Point de comparaison",
                    Complete: "Terminé",
                    "Delayed start by": "Début différe de",
                    Duration: "Durée",
                    End: "Fin",
                    "Overrun by": "Dépassé par",
                    Start: "Début"
                },
                Button: {
                    Create: "Créer",
                    "Critical paths": "Chemins critiques",
                    Edit: "Éditer",
                    "Export to PDF": "Exporter en PDF",
                    Features: "Fonctionnalités",
                    Settings: "Paramètres"
                },
                DateColumn: { Deadline: "Date limite" },
                Field: {
                    "Find tasks by name": "Chercher les tâches par nom",
                    "Project start": "Début du projet"
                },
                GanttToolbar: {
                    "First select the task you want to edit":
                        "Sélectionnez d'abord la tâche que vous souaitez éditer",
                    "New task": "Nouvelle tâche",
                    "Pick a project": "Choisissez un projet"
                },
                Indicators: { Indicators: "Indicateurs", lateDates: "Début/Fin retardé", constraintDate: "Contraintes" },
                MenuItem: {
                    "Draw dependencies": "Tracer les dépendances",
                    "Enable cell editing": "Autoriser la modification des cellules",
                    "Hide schedule": "Masquer le calendrier",
                    "Highlight non-working time": "Afficher les périodes non-travaillées",
                    "Project lines": "Bornages du projet",
                    "Show baselines": "Afficher les comparaisons",
                    "Show progress line": "Afficher l'avancement",
                    "Show rollups": "Afficher les cumuls",
                    "Task labels": "Nom des tâches"
                },
                Slider: {
                    "Animation duration ": "Durée d'animation",
                    "Bar margin": "Largeur de la barre",
                    "Row height": "Hauteur de ligne"
                },
                StartDateColumn: { "Start date": "Date de début" },
                StatusColumn: { Status: "Status" },
                TaskTooltip: {
                    "Scheduling Mode": "Mode de planification",
                    Calendar: "Calendrier",
                    Critical: "Critique"
                },
                Tooltip: {
                    "Adjust settings": "Régler les paramètres",
                    "Collapse all": "Tout réduire",
                    "Create new task": "Créer une nouvelle tâche",
                    "Edit selected task": "Éditer la tâche sélectionnée",
                    "Expand all": "Tout afficher",
                    "Highlight critical paths": "Afficher le chemin critique",
                    "Next time span": "Laps de temps suivant",
                    "Previous time span": "Laps de temps précédent",
                    "Toggle features": "Activer/Désactiver les fonctionnalités",
                    "Zoom in": "Zoomer",
                    "Zoom out": "Dézoomer",
                    "Zoom to fit": "Ajuster à la page"
                }
            };
            a.NBd.publishLocale(p);
            const h = {
                localeName: "De",
                localeDesc: "Deutsch",
                localeCode: "de-DE",
                DateConstraintIntervalDescription: {
                    constraintTypeTpl: { startnoearlierthan: "Darf nicht früher starten als" }
                },
                ConstraintTypePicker: { startnoearlierthan: "Darf nicht früher als starten" },
                AdvancedTab: { honor: "Einhalten" }
            };
            a.NBd.publishLocale(h);
            const g = {
                ar_001: "Ar",
                cs_CZ: "Cs",
                da_DK: "Da",
                el_GR: "El",
                de_DE: "De",
                de_CH: "De",
                et_EE: "Et",
                es_AR: "Es",
                es_BO: "Es",
                es_CL: "Es",
                es_CO: "Es",
                es_CR: "Es",
                es_DO: "Es",
                es_EC: "Es",
                es_GT: "Es",
                es_MX: "Es",
                es_PA: "Es",
                es_PE: "Es",
                es_PY: "Es",
                es_UY: "Es",
                es_VE: "Es",
                es_ES: "Es",
                fr_BE: "FrFr",
                fr_CA: "FrFr",
                fr_CH: "FrFr",
                fr_FR: "FrFr",
                it_IT: "It",
                ja_JP: "Ja",
                nl_NL: "Nl",
                nl_BE: "Nl",
                pl_PL: "Pl",
                pt_AO: "Pt",
                pt_BR: "Pt",
                pt_PT: "Pt",
                ro_RO: "Ro",
                ru_RU: "Ru",
                sl_SI: "Sl",
                sv_SE: "SvSE",
                th_TH: "Th",
                tr_TR: "Tr",
                vi_VN: "Vi",
                zh_HK: "ZhCn",
                zh_CN: "ZhCn",
                zh_TW: "ZhCn"
            };
            var m = g;
            class f extends a.M7E {
                static get type() {
                    return "gantttoolbar";
                }
                static get $name() {
                    return "GanttToolbar";
                }
                static get configurable() {
                    return {
                        items: [
                            {
                                type: "buttonGroup",
                                items: [
                                    {
                                        color: "b-green",
                                        ref: "addTaskButton",
                                        icon: "b-fa b-fa-plus",
                                        text: "Create",
                                        tooltip: "Create new task",
                                        onAction: "up.onAddTaskClick"
                                    },
                                    {
                                        type: "button",
                                        ref: "printButton",
                                        icon: "b-fa-print",
                                        text: "Print",
                                        onAction: "up.onPrintPdfClick"
                                    }
                                ]
                            },
                            { ref: "undoRedo", type: "undoredo", items: { transactionsCombo: null } },
                            {
                                type: "buttonGroup",
                                items: [
                                    {
                                        ref: "expandAllButton",
                                        icon: "b-fa b-fa-angle-double-down",
                                        tooltip: "Expand all",
                                        onAction: "up.onExpandAllClick"
                                    },
                                    {
                                        ref: "collapseAllButton",
                                        icon: "b-fa b-fa-angle-double-up",
                                        tooltip: "Collapse all",
                                        onAction: "up.onCollapseAllClick"
                                    }
                                ]
                            },
                            {
                                type: "buttonGroup",
                                items: [
                                    {
                                        ref: "zoomInButton",
                                        icon: "b-fa b-fa-search-plus",
                                        tooltip: "Zoom in",
                                        onAction: "up.onZoomInClick"
                                    },
                                    {
                                        ref: "zoomOutButton",
                                        icon: "b-fa b-fa-search-minus",
                                        tooltip: "Zoom out",
                                        onAction: "up.onZoomOutClick"
                                    },
                                    {
                                        ref: "zoomToFitButton",
                                        icon: "b-fa b-fa-compress-arrows-alt",
                                        tooltip: "Zoom to fit",
                                        onAction: "up.onZoomToFitClick"
                                    },
                                    {
                                        ref: "previousButton",
                                        icon: "b-fa b-fa-angle-left",
                                        tooltip: "Previous time span",
                                        onAction: "up.onShiftPreviousClick"
                                    },
                                    {
                                        ref: "nextButton",
                                        icon: "b-fa b-fa-angle-right",
                                        tooltip: "Next time span",
                                        onAction: "up.onShiftNextClick"
                                    }
                                ]
                            },
                            {
                                type: "buttonGroup",
                                ref: "baseLineButtons",
                                hidden: !0,
                                items: [
                                    {
                                        type: "button",
                                        text: "Set baseline",
                                        icon: "b-fa-bars",
                                        iconAlign: "end",
                                        menu: [
                                            { text: "Set baseline 1", onItem() { this.up("gantttoolbar").setBaseline(1); } },
                                            { text: "Set baseline 2", onItem() { this.up("gantttoolbar").setBaseline(2); } },
                                            { text: "Set baseline 3", onItem() { this.up("gantttoolbar").setBaseline(3); } }
                                        ]
                                    },
                                    {
                                        type: "button",
                                        text: "Show baseline",
                                        icon: "b-fa-bars",
                                        iconAlign: "end",
                                        menu: [
                                            { checked: !0, text: "Baseline 1", onToggle({ checked: e }) { this.up("gantttoolbar").toggleBaselineVisible(1, e); } },
                                            { checked: !0, text: "Baseline 2", onToggle({ checked: e }) { this.up("gantttoolbar").toggleBaselineVisible(2, e); } },
                                            { checked: !0, text: "Baseline 3", onToggle({ checked: e }) { this.up("gantttoolbar").toggleBaselineVisible(3, e); } }
                                        ]
                                    }
                                ]
                            },
                            {
                                type: "button",
                                ref: "featuresButton",
                                icon: "b-fa b-fa-tasks",
                                text: "Settings",
                                tooltip: "Toggle features",
                                toggleable: !0,
                                menu: {
                                    onItem: "up.onFeaturesClick",
                                    onBeforeShow: "up.onFeaturesShow",
                                    items: [
                                        {
                                            text: "UI settings",
                                            icon: "b-fa-sliders-h",
                                            menu: {
                                                type: "popup",
                                                anchor: !0,
                                                cls: "settings-menu",
                                                layoutStyle: { flexDirection: "column" },
                                                onBeforeShow: "up.onSettingsShow",
                                                items: [
                                                    { type: "slider", ref: "rowHeight", text: "Row height", width: "12em", showValue: !0, min: 30, max: 70, onInput: "up.onRowHeightChange" },
                                                    { type: "slider", ref: "barMargin", text: "Bar margin", width: "12em", showValue: !0, min: 0, max: 10, onInput: "up.onBarMarginChange" },
                                                    { type: "slider", ref: "duration", text: "Animation duration ", width: "12em", min: 0, max: 2000, step: 100, showValue: !0, onInput: "up.onAnimationDurationChange" }
                                                ]
                                            }
                                        },
                                        { text: "Draw dependencies", feature: "dependencies", checked: !1 },
                                        { text: "Task labels", feature: "labels", checked: !1 },
                                        { text: "Critical paths", feature: "criticalPaths", tooltip: "Highlight critical paths", checked: !1 },
                                        { text: "Project lines", feature: "projectLines", checked: !1 },
                                        { text: "Highlight non-working time", feature: "nonWorkingTime", checked: !1 },
                                        { text: "Enable cell editing", feature: "cellEdit", checked: !1 },
                                        { text: "Show baselines", feature: "baselines", checked: !1 },
                                        { text: "Show rollups", feature: "rollups", checked: !1 },
                                        { text: "Export to MSP", feature: "mspExport", checked: !1 },
                                        { text: "Export to Excel", feature: "excelExporter", checked: !1 },
                                        { text: "Show progress line", feature: "progressLine", checked: !1 },
                                        { text: "Show resource utilization", subGrid: "partner", checked: !1 },
                                        { text: "Hide schedule", cls: "b-separator", subGrid: "normal", checked: !1 }
                                    ]
                                }
                            },
                            {
                                type: "datefield",
                                ref: "startDateField",
                                label: "Project start",
                                flex: "0 0 18em",
                                listeners: { change: "up.onStartDateChange" }
                            },
                            {
                                type: "combo",
                                ref: "projectPicker",
                                displayField: "name",
                                minWidth: "300px",
                                width: "auto",
                                placeholder: "Pick a project",
                                multiSelect: !0,
                                listeners: { change: "up.onProjectChange" }
                            },
                            "->",
                            {
                                type: "button",
                                text: "Export to MSP",
                                hidden: !0,
                                ref: "mspExportButton",
                                icon: "b-fa-file-export",
                                onAction: "up.onMSPExport"
                            },
                            {
                                type: "button",
                                text: "Export as .xslx",
                                hidden: !0,
                                ref: "excelExportButton",
                                icon: "b-fa-file-export",
                                onAction: "up.onExcelExport"
                            },
                            {
                                type: "textfield",
                                ref: "filterByName",
                                cls: "filter-by-name",
                                flex: "0 0 13.5em",
                                label: "Find tasks by name",
                                tooltip: "Find tasks by name",
                                clearable: !0,
                                keyStrokeChangeDelay: 100,
                                triggers: {
                                    filter: { align: "end", cls: "b-fa b-fa-filter" }
                                },
                                onChange: "up.onFilterChange"
                            },
                            {
                                type: "buttonGroup",
                                items: [
                                    {
                                        ref: "addFullscreenButton",
                                        icon: "b-fa b-fa-maximize",
                                        tooltip: "Fullscreen on/off",
                                        onAction: "up.onFullscreen"
                                    }
                                ]
                            }
                        ]
                    };
                }
                onFullscreen() {
                    a.glU.isFullscreen
                        ? this.gantt.exitFullscreen()
                        : this.gantt.requestFullscreen();
                }
                updateParent(e, t) {
                    super.updateParent(e, t);
                    this.gantt = e;
                    const n = this.widgetMap.addTaskButton;
                    if (n) {
                        n.text = this.gantt.L("New task");
                    }
                    const a = this.widgetMap.startDateField,
                        o = this.gantt.features.projectLines;
                    if (o && a) {
                        a.label = o.L("Project Start");
                    }
                    e.project.on({ load: "onProjectload", refresh: "updateStartDateField", thisObj: this });
                    this.styleNode = document.createElement("style");
                    document.head.appendChild(this.styleNode);
                }
                syncOverflowMenuButton(e) {
                    const t = e.find(e => "projectPicker" === e.ref);
                    if (t) {
                        t.initialConfig.store = this.gantt.project.projects;
                    }
                    super.syncOverflowMenuButton(e);
                }
                onProjectload() {
                    this.updateStartDateField();
                    const { projectPicker: e } = this.widgetMap,
                        t = this.gantt.project;
                    try {
                        localStorage.setItem("b-gantt-project-ids", JSON.stringify(t.projectIds));
                    } catch (n) {
                        console.log(n);
                    }
                    if (t.loadProjectsOnly) {
                        t.loadProjectsOnly = !1;
                        e.disabled = !1;
                    } else {
                        e.store = t.projects;
                        const n = [];
                        if (this.gantt.project.root.children) {
                            this.gantt.project.root.children.forEach(e => {
                                n.push(e.id);
                            });
                        }
                        e.placeholder = n.length === 0 ? this.L("Pick a project") : "";
                        e.value = n;
                    }
                }
                setAnimationDuration(e) {
                    const t = this,
                        n = `.b-animating .b-gantt-task-wrap { transition-duration: ${e / 1e3}s !important; }`;
                    t.gantt.transitionDuration = e;
                    if (t.transitionRule) {
                        t.transitionRule.cssText = n;
                    } else {
                        t.transitionRule = a.kHD.insertRule(n);
                    }
                }
                updateStartDateField() {
                    try {
                        const { startDateField: e } = this.widgetMap;
                        if (this.gantt.project && this.gantt.project.startDate) {
                            e.value = this.gantt.project.startDate;
                        }
                    } catch (e) {
                        console.error(e);
                    }
                }
                async onAddTaskClick() {
                    const { gantt: e } = this;
                    if (e.taskStore.rootNode.children.length) {
                        const t = e.selectedRecord || e.taskStore.first;
                        if (t) {
                            const n = t.appendChild({
                                name: e.L("New task"),
                                duration: 1,
                                isReadOnly: !1,
                                project_id: t.project_id
                            });
                            await e.project.propagateAsync();
                            await e.scrollRowIntoView(n);
                            e.features.cellEdit.startEditing({ record: n, field: "name" });
                        }
                    }
                }
                onEditTaskClick() {
                    const { gantt: e } = this;
                    if (e.selectedRecord) {
                        e.editTask(e.selectedRecord);
                    } else {
                        a.y8.show(this.L("First select the task you want to edit"));
                    }
                }
                onExpandAllClick() {
                    this.gantt.expandAll();
                }
                onCollapseAllClick() {
                    this.gantt.collapseAll();
                }
                onZoomInClick() {
                    this.gantt.zoomIn();
                }
                onZoomOutClick() {
                    this.gantt.zoomOut();
                }
                onZoomToFitClick() {
                    this.gantt.zoomToFit({ leftMargin: 50, rightMargin: 50 });
                }
                onShiftPreviousClick() {
                    this.gantt.shiftPrevious();
                }
                onShiftNextClick() {
                    this.gantt.shiftNext();
                }
                onStartDateChange({ value: e, oldValue: t }) {
                    try {
                        if (!t) return;
                        this.gantt.startDate = a.rVz.add(e, -1, "week");
                        this.gantt.project.setStartDate(e);
                    } catch (n) {
                        console.log(n);
                    }
                }
                onFilterChange({ value: e }) {
                    if ("" === e) {
                        this.gantt.taskStore.clearFilters();
                    } else {
                        e = e.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
                        this.gantt.taskStore.filter({
                            filters: t => t.name && t.name.match(new RegExp(e, "i")),
                            replace: !0
                        });
                    }
                }
                onFeaturesClick({ source: e }) {
                    const { gantt: t } = this,
                        n = window.o_gantt.histogram;
                    if (e.feature) {
                        const n = t.features[e.feature];
                        n.disabled = !n.disabled;
                        if ("baselines" === e.feature) {
                            this.widgetMap["baseLineButtons"].hidden = n.disabled;
                        }
                        if ("mspExport" === e.feature) {
                            this.widgetMap["mspExportButton"].hidden = n.disabled;
                        }
                        if ("excelExporter" === e.feature) {
                            this.widgetMap["excelExportButton"].hidden = n.disabled;
                        }
                    } else if (e.subGrid) {
                        if ("normal" === e.subGrid) {
                            const n = t.subGrids[e.subGrid];
                            n.collapsed = !n.collapsed;
                        }
                        if ("partner" === e.subGrid) {
                            if (n.collapsed) {
                                n.minHeight = n._prevMinHeight;
                                n.maxHeight = "50%";
                            } else {
                                n._prevMinHeight = n.minHeight;
                                n.minHeight = "unset";
                                n.maxHeight = "50%";
                            }
                            n.collapse(!n.collapsed);
                        }
                    }
                }
                onFeaturesShow({ source: e }) {
                    const { gantt: t } = this,
                        n = window.o_gantt.histogram;
                    e.items.map(e => {
                        const { feature: a } = e;
                        if (a) {
                            if (t.features[a]) {
                                e.checked = !t.features[a].disabled;
                            } else {
                                e.hide();
                            }
                        } else if (e.subGrid) {
                            if ("normal" === e.subGrid) {
                                e.checked = t.subGrids[e.subGrid].collapsed;
                            }
                            if ("partner" === e.subGrid) {
                                e.checked = !n.collapsed;
                            }
                        }
                    });
                }
                onSettingsShow({ source: e }) {
                    const { gantt: t } = this,
                        { rowHeight: n, barMargin: a, duration: o } = e.widgetMap;
                    n.value = t.rowHeight;
                    a.value = t.barMargin;
                    a.max = t.rowHeight / 2 - 5;
                    o.value = t.transitionDuration;
                }
                onRowHeightChange({ value: e, source: t }) {
                    this.gantt.rowHeight = e;
                    t.owner.widgetMap.barMargin.max = e / 2 - 5;
                }
                onBarMarginChange({ value: e }) {
                    this.gantt.barMargin = e;
                }
                onAnimationDurationChange({ value: e }) {
                    this.gantt.transitionDuration = e;
                    this.styleNode.innerHTML = `.b-animating .b-gantt-task-wrap { transition-duration: ${e / 1e3}s !important; }`;
                }
                onCriticalPathsClick({ source: e }) {
                    this.gantt.features.criticalPaths.disabled = !e.pressed;
                }
                setBaseline(e) {
                    this.gantt.taskStore.setBaseline(e);
                }
                toggleBaselineVisible(e, t) {
                    this.gantt.element.classList[t ? "remove" : "add"](`b-hide-baseline-${e}`);
                }
                onFieldCloneChange({ source: e, value: t, userAction: n }) {
                    if ("projectPicker" === e.ref) {
                        e._toolbarOverflowOriginal.userAction = n;
                    }
                    e._toolbarOverflowOriginal.value = t;
                }
                onProjectChange(e) {
                    try {
                        const t = e.value || [],
                            n = this,
                            a = this.gantt.project;
                        if (n.isLoading) return;
                        const { addTaskButton: o, projectPicker: r } = this.widgetMap;
                        o.disabled = t.length === 0;
                        if (e.userAction || e.source.userAction) {
                            n.isLoading = !0;
                            e.source.userAction = !1;
                            e.source.disabled = !0;
                            a.projectIds = t.map(e => e.substring(e.indexOf("_") + 1));
                            r.placeholder = t.length === 0 ? this.L("Pick a project") : "";
                            a.loadProjectsOnly = !0;
                            a.transport.load.params = { project_ids: a.projectIds, only_projects: a.loadProjectsOnly };
                            a.suspendAutoSync();
                            a.taskStore.clear();
                            a.assignmentStore.clear();
                            a.dependencyStore.clear();
                            a.suspendChangeEvent = !0;
                            a.load().then(() => {
                                n.isLoading = !1;
                                a.acceptChanges();
                                a.resumeAutoSync();
                                a.suspendChangeEvent = !1;
                            });
                        }
                    } catch (t) {
                        console.log(t);
                    }
                }
                onMSPExport() {
                    const e = this.gantt.project.taskStore.first && `${this.gantt.project.taskStore.first.name}.xml`;
                    this.gantt.features.mspExport.export({ filename: e });
                }
                onExcelExport() {
                    const e = this.gantt.project.taskStore.first && `${this.gantt.project.taskStore.first.name}.xslx`;
                    this.gantt.features.excelExporter.export({ filename: e });
                }
                onPrintPdfClick() {
                    this.gantt.features.print.showPrintDialog();
                }
            }
            f.initClass();
            var b = n(8670);
            const y = {
                dependencyIdField: "wbsCode",
                resourceImageFolderPath: "users/",
                syncMask: null,
                removePartner: () => {},
                scrollTaskIntoViewOnCellClick: !0,
                columns: [
                    { type: "wbs", persist: !0, id: "br_column_1" },
                    { type: "name", width: 250, id: "br_column_2" },
                    { type: "startdate", id: "br_column_3" },
                    // Nueva columna para End Date (asumiendo que existe un tipo "enddate")
                    { type: "enddate", id: "br_column_enddate" },
                    { type: "duration", id: "br_column_4_1" },
                    {
                        text: "Tags",
                        field: "tagIds",
                        editor: { multiSelect: !0, type: "combo", valueField: "id", displayField: "name" },
                        renderer: function ({ grid: e, record: t, column: n, value: a, row: o }) {
                            const r = e.project.projects?.getById(t.project_id);
                            let s = "";
                            if (r && a) {
                                for (let i = 0; i < a.length; i++) {
                                    let e = r.taskTags.find(e => e.id === a[i])?.name;
                                    if (e !== void 0) {
                                        if (s !== "") {
                                            s += ", ";
                                        }
                                        s += e;
                                    }
                                }
                            }
                            return { class: "rounded-pill", children: [{ tag: "div", text: s }] };
                        },
                        filterable: ({ record: e, value: t, operator: n, property: a }) => {
                            const o = new RegExp(t, "i"),
                                r = e.project.projects?.getById(e.project_id);
                            if (r) {
                                const t = r.taskTags.find(e => o.test(e.name));
                                if (t && e.tagIds !== void 0) {
                                    return e.tagIds.includes(t.id);
                                }
                            }
                            return !1;
                        },
                        id: "br_column_4_3"
                    },
                    // Nueva columna para "Costo"
                    {
                        text: "Costo",
                        field: "cost",
                        width: 100,
                        id: "br_column_cost",
                        renderer: ({ record }) => {
                            return record.children && record.children.length ? record.aggregatedCost : record.cost;
                        },
                        editor: { type: "numberfield" },
                        //hidden: true,             // Esta propiedad oculta la columna inicialmente
                    },
                    // Nueva columna para "Cantidad"
                    {
                        text: "Cantidad",
                        field: "quantity",
                        width: 100,
                        id: "br_column_quantity",
                        renderer: ({ record }) => {
                            return record.children && record.children.length ? record.aggregatedQuantity : record.quantity;
                        },
                        editor: { type: "numberfield" },
                        //hidden: true,             // Esta propiedad oculta la columna inicialmente
                    },
                    { type: "resourceassignment", width: 120, showAvatars: !0, id: "br_column_5" },
                    { type: "percentdone", showCircle: !0, width: 70, id: "br_column_6", readonly: true, editor: false },
                    { type: "predecessor", width: 112, id: "br_column_7", dependencyIdField: "wbsCode" },
                    { type: "successor", width: 112, id: "br_column_8", dependencyIdField: "wbsCode" },
                    {
                        text: "State",
                        field: "state",
                        editor: { type: "combo", valueField: "id", displayField: "name" },
                        renderer: function ({ value: e, record: t, grid: n }) {
                            const a = n.project.projects?.getById(t.project_id);
                            if (a)
                                return a.taskStates.getById(e)?.name;
                        },
                        filterable: ({ record: e, value: t, operator: n, property: a }) => {
                            const o = new RegExp(t, "i"),
                                r = e.project.projects?.getById(e.project_id);
                            if (r) {
                                const t = r.taskStates.find(e => o.test(e.name));
                                if (t && e.state)
                                    return e.state === t.id;
                            }
                            return !1;
                        },
                        id: "br_column_14_1"
                    },
                    { type: "addnew", id: "br_column_13" }
                ],
                subGridConfigs: { locked: { flex: 3 }, normal: { flex: 4 } },
                columnLines: !1,
                features: {
                    dependencies: {
                        onTimeSpanMouseLeave: function (e) {
                            const t = e[`${this.eventName}Element`],
                                n = e.event.relatedTarget,
                                o = this.creationData?.timeSpanElement;
                            let r = !1;
                            try {
                                r = a.nq2.isDescendant(o, n);
                            } catch (s) {}
                            if (!(this.creationData && o && r)) {
                                this.hideTerminals(t);
                            }
                            if (this.creationData && !this.creationData.finalizing) {
                                this.creationData.timeSpanElement = null;
                                this.onOverNewTargetWhileCreating();
                            }
                        }
                    },
                    cellTooltip: {
                        tooltipRenderer: ({ record: e, column: t, cellElement: n, cellTooltip: a, event: o }) => {
                            if (["successors", "predecessors", "tagIds"].includes(t.data.field)) {
                                let e = n.valueOf().textContent;
                                if (e) {
                                    return { class: "rounded-pill", children: [{ tag: "div", text: e }] };
                                }
                            }
                        },
                        hoverDelay: 100
                    },
                    cellEdit: { addNewAtEnd: !1 },
                    taskEdit: {
                        callOnFunctions: !0,
                        onHide: () => {},
                        items: {
                            generalTab: {
                                items: {
                                    startDate: { type: "datetime", timeField: { format: "HH:mm" }, flex: "1 0 100%", cls: "start-date-edit" },
                                    endDate: { type: "datetime", timeField: { format: "HH:mm" }, flex: "1 0 100%", cls: "end-date-edit" },
                                    state: { type: "stateField", weight: 350, label: "State", name: "state", multiSelect: !1 },
                                    tagIds: { type: "tagField", weight: 710, label: "Tags", name: "tagIds", multiSelect: !0, field: "tagIds" }
                                }
                            }
                        }
                    },
                    taskMenu: { items: { add: { menu: { subtask: { at: "end" }, addTaskAbove: !1, addTaskBelow: !1, successor: !1, predecessor: !1 } } } },
                    rollups: { disabled: !0 },
                    baselines: {
                        disabled: !0,
                        template(e) {
                            const t = this,
                                { baseline: n } = e,
                                { task: o } = n,
                                r = o.startDate > n.startDate,
                                s = o.durationMS > n.durationMS;
                            let { decimalPrecision: i } = t;
                            if (i == null) {
                                i = t.client.durationDisplayPrecision;
                            }
                            const l = Math.pow(10, i),
                                d = Math.round(n.duration * l) / l;
                            return `
                    <div class="b-gantt-task-title">${a.MZC.encodeHtml(o.name)} (${n.name})</div>
                    <table>
                    <tr><td>${t.L("Start")}:</td><td>${e.startClockHtml}</td></tr>
                    ${n.milestone ? "" : `
                        <tr><td>Start:</td><td>${e.endClockHtml}</td></tr>
                        <tr><td>Duration:</td><td class="b-right">${d + " " + a.rVz.getLocalizedNameOfUnit(n.durationUnit, 1 !== n.duration)}</td></tr>
                    `}
                    </table>
                    ${r ? `
                        <h4 class="statusmessage b-baseline-delay"><i class="statusicon b-fa b-fa-exclamation-triangle"></i>Delayed start by ${a.rVz.formatDelta(o.startDate - n.startDate)}</h4>
                    ` : ""}
                    ${s ? `
                        <h4 class="statusmessage b-baseline-overrun"><i class="statusicon b-fa b-fa-exclamation-triangle"></i>Overrun by ${a.rVz.formatDelta(o.durationMS - n.durationMS)}</h4>
                    ` : ""}
                    `;
                        }
                    },
                    progressLine: { disabled: !0 },
                    filter: {
                        filters: {
                            stageId: { type: "string", operator: "contains" },
                            state: { type: "string", operator: "contains" },
                            tagIds: { type: "string", operator: "contains" }
                        }
                    },
                    dependencyEdit: !0,
                    mspExport: { filename: "Gantt MSP Export", disabled: !0 },
                    excelExporter: { disabled: !0, zipcelx: b.A },
                    print: {
                        disabled: !1,
                        footerTpl: () => `<h3>© ${(new Date).getFullYear()} Bryntum AB</h3></div>`,
                        headerTpl: ({ currentPage: e, totalPages: t }) => `
                <dl>
                    <dt>Date: ${a.rVz.format(new Date, "ll LT")}</dt>
                    <dd>${t ? `Page: ${e + 1}/${t}` : ""}</dd>
                </dl> `
                    },
                    timeRanges: { showCurrentTimeLine: !0 },
                    labels: { left: { field: "name", editor: { type: "textfield" } } }
                },
                listeners: {
                    gridRowDrag: ({ context: e }) => {
                        const { startRecord: t, parent: n } = e;
                        e.valid = !!(n && t && (n.project_id === t.project_id || n.id === t.project_id));
                    },
                    taskMenuBeforeShow: ({ taskRecord: e }) => !e.isReadOnly,
                    beforeCellEditStart: function({ editorContext: e }) {
                        const { record: t, editor: n, column: a } = e;
                        // Si el campo es "cost" o "quantity" y la tarea tiene hijos, se cancela la edición
                        if ((a.field === "cost" || a.field === "quantity") &&
                            t.children && t.children.length > 0) {
                            return false; // Cancela el inicio de la edición
                        }
                        if (a.field === "stageId") {
                            const proj = this.project.projects?.getById(t.project_id);
                            if (!proj) return false;
                            n.store = proj.taskTypes;
                        }
                        if (a.field === "state") {
                            const proj = this.project.projects?.getById(t.project_id);
                            if (!proj) return false;
                            n.store = proj.taskStates;
                        }
                        if (a.field === "tagIds") {
                            const proj = this.project.projects?.getById(t.project_id);
                            if (!proj) return false;
                            n.store = proj.taskTags;
                        }
                    }
                },
                tbar: { type: "gantttoolbar", overflow: "scroll" }
            };
            var w = y;
            class k extends a.M7E {
                static get type() {
                    return "histogramtoolbar";
                }
                static get $name() {
                    return "HistogramToolbar";
                }
                static get configurable() {
                    return {
                        items: [
                            {
                                type: "checkbox",
                                ref: "showBarText",
                                text: "Show bar texts",
                                tooltip: "Check to show resource allocation in the bars",
                                checked: !1,
                                onAction: "up.onShowBarTextToggle"
                            },
                            {
                                type: "checkbox",
                                ref: "showMaxEffort",
                                text: "Show max allocation",
                                tooltip: "Check to display max resource allocation line",
                                checked: !0,
                                onAction: "up.onShowMaxAllocationToggle"
                            }
                        ]
                    };
                }
                updateParent(e, t) {
                    super.updateParent(e, t);
                    this.histogram = e;
                }
                onShowBarTextToggle({ source: e }) {
                    this.histogram.showBarText = e.checked;
                }
                onShowMaxAllocationToggle({ source: e }) {
                    this.histogram.showMaxEffort = e.checked;
                }
            }
            k.initClass();
            const _ = {
                hideHeaders: !1,
                rowHeight: 50,
                showBarTip: !0,
                ref: "histogram",
                syncMask: null,
                header: !1,
                collapsible: !0,
                collapsed: !0,
                minHeight: 0,
                weekStartDay: 1,
                columns: [{ type: "resourceInfo", showImage: !1, text: "Name", field: "name", showEventCount: !1, flex: 1 }],
                tbar: { type: "histogramtoolbar" }
            };
            var v = _;
            const S = { silenceInitialCommit: !0, week_start: 1, hoursPerDay: 8, taskModelClass: r, taskStore: { wbsMode: "auto" } };
            var D = S;
            window.o_gantt = { _isRun: !1, moduleID: "#bryntum-gantt", config: {}, projectID: 0, mountTimes: 0 };
            const j = window.project = new l(D);
            window.o_gantt.create_all_elements = function (e) {
                w.appendTo = e;
                w.project = j;
                w.readOnly = !!window.o_gantt.readOnly;
                w.silenceInitialCommit = !window.o_gantt.saveWbs;
                const t = window.o_gantt.config || {};
                Object.assign(w.features, t.features);
                Object.assign(w, t);
                const n = new a.NI(w);
                window.splitter = new a.O3W({ appendTo: e });
                v.appendTo = e;
                v.partner = n;
                v.project = j;
                Object.assign(t, { weekStartDay: t.weekStartDay !== void 0 ? t.weekStartDay : window.o_gantt.week_start });
                v.weekStartDay = t.weekStartDay;
                const o = new a.HRC(v);
                j.addCrudStore({ storeId: "projects", store: new a.ilR({ fields: ["id", "name"] }) });
                j.projects = j.getStoreDescriptor("projects").store;
                window.o_gantt.update = function () { j.load(); };
                window.o_gantt.gantt = n;
                window.o_gantt.histogram = o;
                const r = j.stm;
                try {
                    var s = [];
                    if (!0 !== window.action_from_odoo) {
                        s = JSON.parse(localStorage.getItem("b-gantt-project-ids")) || [];
                        if (s.constructor === Number) {
                            s = [s];
                        }
                    } else {
                        s = window.o_gantt.projectID || [];
                    }
                    if (s) {
                        j.projectIds = s;
                        j.transport.load.params = { project_ids: j.projectIds, only_projects: !1 };
                    }
                } catch (l) {}
                window.project = j;
                j.load().then(() => { r.enable(); r.autoRecord = !0; });
                a.OZi.locale = m[window.o_gantt.lang] || "En";
                const i = window.onerror;
                if (i) {
                    window.onerror = function (e, t, n, a, o) {
                        if (o) {
                            i(e, t, n, a, o);
                        }
                    };
                }
            };
        },
        4255: function (e, t, n) {
            "use strict";
            n.r(t);
            var a = n(1601),
                o = n.n(a),
                r = n(6314),
                s = n.n(r),
                i = s()(o());
            i.push([
                e.id,
                '/**\n * Application global styles (compiled from existing files)\n */\n\n.b-sch-event .b-sch-event-content {\n    font-size : 12px;\n}\n\n.b-theme-stockholm .b-sch-event {\n    border-radius : 2px;\n}\n\n.b-percent-bar-cell .b-percent-bar-outer {\n    height        : 1em;\n    border-radius : 1em;\n\n    .b-percent-bar {\n        border-radius    : 1em;\n        background-color : #8ee997;\n    }\n}\n\n.b-gantt {\n    > .b-toolbar {\n        > .b-content-element {\n            > .b-widget:not(.b-last-visible-child) {\n                margin-right: 1em;\n            }\n\n            .b-button {\n                min-width: 3.5em;\n            }\n        }\n    }\n}\n\n.b-widget label {\n    margin-bottom: unset !important;\n}\n\n.filter-by-name label {\n    display: none;\n}\n\n.b-theme-stockholm .b-gantt > .b-toolbar {\n    border-bottom-color: #d8d9da;\n}\n\n.b-theme-classic .b-gantt > .b-toolbar {\n    background-color: #f1f1f4;\n    border-bottom-color: #b0b0b6;\n\n    .b-has-label label {\n        color: #555;\n    }\n}\n\n.b-theme-classic-light .b-gantt > .b-toolbar {\n    background-color: #fff;\n    border-bottom-color: #e0e0e0;\n}\n\n.b-theme-material .b-gantt > .b-toolbar {\n    background-color: #fff;\n    border-bottom: none;\n\n    .filter-by-name label {\n        display: block;\n    }\n}\n\n.b-theme-classic-dark .b-gantt > .b-toolbar {\n    background-color: #2b2b2f;\n    border-bottom-color: #2a2b2e;\n}\n\n.settings-menu .b-slider {\n    margin-bottom: 0.5em;\n}\n\n.b-task-baseline[data-index="0"] {\n    background-color : #ddd;\n}\n.b-task-baseline[data-index="1"] {\n    background-color : darken(#ddd, 4);\n}\n.b-task-baseline[data-index="2"] {\n    background-color : darken(#ddd, 8);\n}\n\n.b-hide-baseline-1 {\n    .b-task-baseline[data-index="0"] {\n        display : none;\n    }\n}\n.b-hide-baseline-2 {\n    .b-task-baseline[data-index="1"] {\n        display : none;\n    }\n}\n.b-hide-baseline-3 {\n    .b-task-baseline[data-index="2"] {\n        display : none;\n    }\n}\n\n.start-date-edit {\n    //margin-right: 0px;\n}\n\n.end-date-edit {\n   margin-bottom: 0.6em;\n}\n\n#bryntum-scheduler-component {\n    position: relative;\n    height: 100%;\n    flex: 1 1 100%;\n    min-height: 0;\n    display: flex;\n    flex-direction: column;\n    align-items: stretch;\n    transform: translate(0, 0);\n    top: 0;\n    left: 0;\n}\n\n.b-datefield.b-no-steppers .b-step-trigger {\n    display: none !important;\n}\n\n[aria-hidden="true"], [aria-hidden="1"] {\n    display: unset !important;\n}\n\n.b-undoredobase .b-badge::before {\n    top: -0.6em;\n}\n\n\n',
                ""
            ]);
            t["default"] = i;
        },
        298: function (e, t, n) {
            var a = n(4255);
            a.__esModule && (a = a.default);
            if ("string" === typeof a) {
                a = [[e.id, a, ""]];
            }
            if (a.locals) {
                e.exports = a.locals;
            }
            var o = n(9548).A;
            o("616df432", a, !1, { sourceMap: !1, shadowMode: !1 });
        }
    },
    t = {};
    function n(a) {
        var o = t[a];
        if (void 0 !== o) return o.exports;
        var r = t[a] = { id: a, exports: {} };
        e[a].call(r.exports, r, r.exports, n);
        return r.exports;
    }
    n.m = e;
    (function () {
        var e = [];
        n.O = function (t, a, o, r) {
            if (!a) {
                var s = 1 / 0;
                for (c = 0; c < e.length; c++) {
                    a = e[c][0];
                    o = e[c][1];
                    r = e[c][2];
                    for (var i = !0, l = 0; l < a.length; l++) {
                        (!1 & r || s >= r) &&
                        Object.keys(n.O).every(function (e) {
                            return n.O[e](a[l]);
                        })
                            ? a.splice(l--, 1)
                            : (i = !1, r < s && (s = r));
                    }
                    if (i) {
                        e.splice(c--, 1);
                        var d = o();
                        void 0 !== d && (t = d);
                    }
                }
                return t;
            }
            r = r || 0;
            for (var c = e.length; c > 0 && e[c - 1][2] > r; c--) {
                e[c] = e[c - 1];
            }
            e[c] = [a, o, r];
        };
    })();
    (function () {
        n.n = function (e) {
            var t = e && e.__esModule ? function () {
                return e["default"];
            } : function () {
                return e;
            };
            n.d(t, { a: t });
            return t;
        };
    })();
    (function () {
        n.d = function (e, t) {
            for (var a in t)
                if (n.o(t, a) && !n.o(e, a))
                    Object.defineProperty(e, a, { enumerable: !0, get: t[a] });
        };
    })();
    (function () {
        n.g = function () {
            if ("object" === typeof globalThis) return globalThis;
            try {
                return this || new Function("return this")();
            } catch (e) {
                if ("object" === typeof window) return window;
            }
        }();
    })();
    (function () {
        n.o = function (e, t) {
            return Object.prototype.hasOwnProperty.call(e, t);
        };
    })();
    (function () {
        n.r = function (e) {
            if (typeof Symbol !== "undefined" && Symbol.toStringTag) {
                Object.defineProperty(e, Symbol.toStringTag, { value: "Module" });
            }
            Object.defineProperty(e, "__esModule", { value: !0 });
        };
    })();
    (function () {
        n.p = "bryntum_gantt/static/gantt_src/";
    })();
    (function () {
        n.b = document.baseURI || self.location.href;
        var e = { 524: 0 };
        n.O.j = function (t) {
            return 0 === e[t];
        };
        var t = function (t, a) {
            var o, r, s = a[0],
                i = a[1],
                l = a[2],
                d = 0;
            if (s.some(function (t) {
                return 0 !== e[t];
            })) {
                for (o in i) {
                    if (n.o(i, o)) {
                        n.m[o] = i[o];
                    }
                }
                if (l) var c = l(n);
                for (t && t(a); d < s.length; d++) {
                    r = s[d];
                    if (n.o(e, r) && e[r] && e[r][0]()) {}
                    e[r] = 0;
                }
                return n.O(c);
            }
            return a;
        };
        var a = self["webpackChunkgantt_view_pro"] = self["webpackChunkgantt_view_pro"] || [];
        a.forEach(t.bind(null, 0));
        a.push = t.bind(null, a.push.bind(a));
    })();
    var a = n.O(void 0, [504], function () {
        return n(6668);
    });
    a = n.O(a);
})();
