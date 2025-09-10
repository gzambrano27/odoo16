# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError
import xml.etree.ElementTree as ET
from datetime import datetime
import base64


class PlantillaTareasImportWizard(models.TransientModel):
    _name = 'plantilla.tareas.import.wizard'
    _description = 'Importar XML de Microsoft Project a Plantilla de Tareas'

    plantilla_id = fields.Many2one('plantilla.tareas', string="Plantilla", required=True)
    file = fields.Binary(string="Archivo XML", required=True)
    filename = fields.Char(string="Nombre del Archivo")

    def action_import(self):
        if not self.file:
            raise ValidationError("Debe adjuntar un archivo XML válido.")

        try:
            xml_content = base64.b64decode(self.file)
            root = ET.fromstring(xml_content)
        except Exception as e:
            raise ValidationError(f"Error al analizar el XML: {str(e)}")

        ns = {'msproj': 'http://schemas.microsoft.com/project'}
        lineas_dict = {}
        plantilla = self.plantilla_id

        for task in root.findall('.//msproj:Task', ns):
            wbs = task.findtext('msproj:WBS', namespaces=ns)
            if not wbs:
                continue

            name = task.findtext('msproj:Name', default='Sin nombre', namespaces=ns)
            start_str = task.findtext('msproj:Start', namespaces=ns)
            finish_str = task.findtext('msproj:Finish', namespaces=ns)
            cost_str = task.findtext('msproj:Cost', default='0', namespaces=ns)

            # --- Procesar fechas ---
            fecha_inicio = fecha_fin = False
            try:
                if start_str:
                    fecha_inicio = datetime.strptime(start_str[:19], '%Y-%m-%dT%H:%M:%S').date()
                if finish_str:
                    fecha_fin = datetime.strptime(finish_str[:19], '%Y-%m-%dT%H:%M:%S').date()
            except Exception:
                pass

            # --- Procesar costo ---
            try:
                if '.' in cost_str:
                    costo = float(cost_str)
                else:
                    costo = float(cost_str) / 100  # ajustar si viene sin punto decimal
            except Exception:
                costo = 0.0

            cantidad = 1.0

            if wbs.count('.') == 0:
                plantilla.name = name

            elif wbs.count('.') == 1:
                linea = self.env['plantilla.tareas.line'].create({
                    'plantilla_tarea_id': plantilla.id,
                    'name': name,
                })
                lineas_dict[wbs] = linea.id

            elif wbs.count('.') == 2:
                parent_wbs = '.'.join(wbs.split('.')[:2])
                linea_id = lineas_dict.get(parent_wbs)
                if linea_id:
                    self.env['plantilla.tareas.line.detalle'].create({
                        'line_id': linea_id,
                        'tareas': name,
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': fecha_fin,
                        'cantidad': cantidad,
                        'costo': costo,
                    })

        return {'type': 'ir.actions.act_window_close'}