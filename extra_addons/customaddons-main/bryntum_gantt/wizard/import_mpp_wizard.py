from odoo import models, fields
from odoo.exceptions import UserError
import base64, xml.etree.ElementTree as ET, pytz
from io import BytesIO
from datetime import datetime, date, time, timedelta

class ImportMPPWizard(models.TransientModel):
    _name = 'import.mpp.wizard'
    _description = 'Importar Proyecto desde MPP'

    file_mpp   = fields.Binary(string="Archivo MPP", required=True)
    filename   = fields.Char(  string="Nombre del Archivo")
    project_id = fields.Many2one('project.project', string="Proyecto Destino", required=True)

    def action_import(self):
        def _parse_iso_date(v):
            try:
                return datetime.strptime(v[:10], '%Y-%m-%d').date()
            except:
                return False

        def _to_utc(d, start):
            if not d:
                return False
            tz = pytz.timezone('America/Guayaquil')
            h = time(0,0) if start else time(23,59)
            loc = tz.localize(datetime.combine(d, h))
            return loc.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')

        if not self.filename or not self.filename.endswith('.xml'):
            raise UserError("Sube un .xml válido de MS Project.")

        try:
            tree = ET.parse(BytesIO(base64.b64decode(self.file_mpp)))
            root = tree.getroot()
            ns   = {'ns': 'http://schemas.microsoft.com/project'}
        except Exception as e:
            raise UserError(f"Error al leer XML: {e}")

        # 1) Actualizar fecha de inicio del proyecto
        sd = root.findtext("ns:StartDate", namespaces=ns)
        if sd:
            d = _parse_iso_date(sd)
            if d:
                self.project_id.write({'project_start_date': _to_utc(d, True)})

        company = self.project_id.company_id.id

        # 2) Leer tareas en dict, incluyendo duración, predecesores, etc.
        data = {}
        for t in root.findall("ns:Tasks/ns:Task", ns):
            uid = t.findtext("ns:UID", namespaces=ns)
            if not uid or uid == "0":
                continue
            name   = t.findtext("ns:Name", namespaces=ns) or ""
            out    = t.findtext("ns:OutlineNumber", namespaces=ns) or ""
            wbs    = t.findtext("ns:WBS", namespaces=ns) or ""
            st     = _parse_iso_date(t.findtext("ns:Start", namespaces=ns) or "")
            fn     = _parse_iso_date(t.findtext("ns:Finish", namespaces=ns) or "")
            qty    = int(t.findtext(
                        "ns:ExtendedAttribute[ns:FieldID='188743731']/ns:Value",
                        namespaces=ns) or 0)
            cost   = float(t.findtext("ns:Cost", namespaces=ns) or 0) / 100.0
            summary= t.findtext("ns:Summary", namespaces=ns) == "1"
            dur_str= t.findtext("ns:Duration", namespaces=ns) or "PT0H0M0S"
            # calcular días de duración en horas/8
            try:
                part = dur_str[2:]
                h=m=s=0
                if 'H' in part:
                    h, part = part.split('H',1); h=int(h)
                if 'M' in part:
                    m, part = part.split('M',1); m=int(m)
                if 'S' in part:
                    s = int(part.replace('S',''))
                duration_days = round((h + m/60 + s/3600) / 8, 2)
            except:
                duration_days = 0.0
            # predecesores
            preds = []
            for pl in t.findall("ns:PredecessorLink", ns):
                pu = pl.findtext("ns:PredecessorUID", namespaces=ns)
                if pu and pu!="0":
                    preds.append(pu)

            if not (name and out and st and fn):
                continue

            data[out] = {
                'uid':        uid,
                'name':       name,
                'outline':    out,
                'wbs':        wbs,
                'start':      st,
                'finish':     fn,
                'cantidad':   qty,
                'cost':       cost,
                'duration':   duration_days,
                'summary':    summary,
                'predecessors': preds,
                'record':     None,
            }

        # 3) Crear tareas en project.task según jerarquía WBS
        def _key(o): return list(map(int, o.split('.')))
        for outline in sorted(data, key=_key):
            d = data[outline]
            parent_outline = '.'.join(outline.split('.')[:-1])
            parent_rec     = data.get(parent_outline, {}).get('record')
            start_utc = _to_utc(d['start'], True)
            end_utc   = _to_utc(d['finish'], False)
            rec = self.env['project.task'].create({
                'name':               d['name'],
                'project_id':         self.project_id.id,
                'company_id':         company,
                'planned_date_begin': start_utc,
                'planned_date_end':   end_utc,
                'duration':           d['duration'],
                'parent_id':          parent_rec.id if parent_rec else False,
                'sequence':           int(d['uid']),
                'cantidad':           d['cantidad'],
                'wbs_value':          d['wbs'],
                'costo':              d['cost'],
            })
            d['record'] = rec

        # 4) Crear dependencias en project.task.linked
        for d in data.values():
            for puid in d['predecessors']:
                pred = next((x for x in data.values() if x['uid']==puid), None)
                if pred and pred['record']:
                    self.env['project.task.linked'].create({
                        'from_id':    pred['record'].id,
                        'to_id':      d['record'].id,
                        'lag':        0,
                        'lag_unit':   'd',
                        'type':       2,
                        'dep_active': True,
                    })

        # 5) Crear cronograma.planilla con name = project.name
        analytic = self.env['account.analytic.account'].search(
            [('name','=', self.project_id.name)], limit=1)
        planilla = self.env['cronograma.planilla'].create({
            'name':                self.project_id.name,
            'cuenta_analitica_id': analytic.id,
        })

        # 6) Crear notebooks y detalles para hojas bajo "OBRA EN CAMPO"
        tasks = [data[o] for o in sorted(data, key=_key)]
        obra = next((x for x in tasks if x['name'].upper()=="OBRA EN CAMPO"), None)
        if obra:
            prefix = obra['outline'] + '.'
            leaves = [t for t in tasks if t['outline'].startswith(prefix) and not t['summary']]
            for t in leaves:
                rubro = t['wbs'].split('.')[-1]
                nb = self.env['cronograma.notebook'].create({
                    'planilla_id':      planilla.id,
                    'rubro':            t['wbs'],
                    'descripcion':      t['name'],
                    'precio_unitario':  t['cost'],
                    'cantidad':         t['cantidad'],
                })
                dias = (t['finish'] - t['start']).days + 1
                if dias > 0:
                    cant_dia = round(t['cantidad']/dias, 2)
                    total    = cant_dia * dias
                    resto    = round(t['cantidad'] - total, 2)
                    fecha    = t['start']
                    for i in range(dias):
                        q = cant_dia + (resto if i==dias-1 else 0)
                        self.env['cronograma.detalle'].create({
                            'notebook_id':          nb.id,
                            'fecha':                fecha,
                            'cantidad':             q,
                            'cantidad_avance_real': 0.0,
                            'valor':                round(q * t['cost'], 2),
                            'valor_avance_real':    0.0,
                        })
                        fecha += timedelta(days=1)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Importación + Planilla OK',
                'message': f'Se importaron {len(data)} tareas y se creó planilla "{planilla.name}".',
                'type': 'success',
                'sticky': False,
            }
        }
