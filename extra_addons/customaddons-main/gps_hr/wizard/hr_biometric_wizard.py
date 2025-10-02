from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import csv
from datetime import datetime
import pytz

class HrBiometricWizard(models.TransientModel):
    _name = 'hr.biometric.wizard'
    _description = 'Importación de marcaciones desde biométrico'

    biometric_id = fields.Many2one(
        'zk.machine',
        string='Dispositivo Biométrico',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    file_data = fields.Binary(string="Archivo de Marcaciones (.dat o .txt)")
    filename = fields.Char(string="Nombre del Archivo")

    result_preview = fields.Text("Vista previa del resultado", readonly=True)

    def action_process(self):
        """Detecta el formato según extensión y procesa el archivo"""
        if not self.file_data or not self.filename:
            raise UserError(_("Debe adjuntar un archivo."))

        # Decodificar archivo
        file_content = base64.b64decode(self.file_data)

        # Detectar extensión
        extension = self.filename.lower().split('.')[-1]
        if extension == 'dat':
            values= self._process_dat(file_content)
            print(values)
        elif extension=='txt':
            values= self._process_txt(file_content)
            print(values)
        elif extension=='csv':
            values= self._process_csv(file_content)
            print(values)
        else:
            raise UserError(_("Formato no soportado: %s") % extension)
        return self.process_marcaciones(values)

    def _process_dat(self, file_content):
        """
        Procesar archivo .dat -> retorna lista de tuplas
        Formato típico: id_biometrico, fecha_hora
        """
        result = []
        try:
            lines = file_content.decode("utf-8", errors="ignore").splitlines()
            for line in lines:
                if not line.strip():
                    continue
                parts = line.strip().split()  # depende del formato real
                # Ejemplo: [ID, Fecha, Hora]
                if len(parts) >= 3:
                    bio_id = parts[0]
                    fecha_str = parts[1]
                    hora_str = parts[2]
                    try:
                        full_fecha="{0} {1}".format(fecha_str,hora_str)
                        fecha = datetime.strptime(full_fecha.strip(), "%Y-%m-%d %H:%M:%S")
                        result.append((bio_id, fecha))
                    except Exception:
                        continue
        except Exception as e:
            raise UserError(_("Error procesando .dat: %s") % str(e))
        return result

    def _process_txt(self , file_content):
        """
        Procesar archivo .txt -> retorna lista de tuplas
        Formato típico CSV o delimitado por tab
        """
        result = []
        try:
            content = io.StringIO(file_content.decode("utf-8", errors="ignore"))
            reader = csv.reader(content, delimiter='\t')  # o cambiar a ',' si es CSV
            for row in reader:
                if not row or len(row) < 2:
                    continue
                bio_id = row[0]
                fecha_str = row[1]
                try:
                    fecha = datetime.datetime.strptime(
                        fecha_str.strip(), "%Y-%m-%d %H:%M:%S"
                    )
                    result.append((bio_id, fecha))
                except Exception:
                    continue
        except Exception as e:
            raise UserError(_("Error procesando .txt: %s") % str(e))
        return result

    def _process_csv(self, file_content):
        """
        Procesar archivo .txt -> retorna lista de tuplas
        Formato típico CSV o delimitado por tab
        """
        result = []
        try:
            content = io.StringIO(file_content.decode("utf-8", errors="ignore"))
            reader = csv.reader(content, delimiter=',')  # o cambiar a ',' si es CSV
            i=0
            for row in reader:
                if not row or len(row) < 2 and i>0:
                    continue
                bio_id = row[0]
                fecha_str = row[2]
                print(bio_id,fecha_str)
                try:
                    fecha = datetime.strptime(fecha_str.strip(), "%d/%m/%Y %H:%M:%S")
                    result.append((bio_id, fecha))
                except Exception:
                    continue
                i+=1
        except Exception as e:
            raise UserError(_("Error procesando .txt: %s") % str(e))
        return result

    def process_marcaciones(self,values):
        att_obj=self.env["employee.attendance.raw"]
        empl_obj = self.env["hr.employee"]
        employees={}
        for pk_biometrico,fecha in values:
            pk_biometrico_int=int(pk_biometrico)
            if not employees.get(pk_biometrico_int,False):
                srch_employee=empl_obj.search([('id','=',pk_biometrico_int)])
                if srch_employee:
                    employees[pk_biometrico_int]=srch_employee[0]
            brw_employee=employees.get(pk_biometrico_int,empl_obj)
            if not brw_employee:
                continue

            fecha_formateada=self.convert_local_to_utc(fecha)
            # Verificar si ya existe una marcación con ese empleado y timestamp
            existing_att = att_obj.search([
                ('employee_id', '=', brw_employee.id),
                ('date_time', '=', fecha_formateada),  # o 'punching_time' si es otro campo
            ], limit=1)

            if not existing_att:
                att_obj.create({
                    'employee_id': brw_employee.id,
                    'date_time': fecha_formateada,  # o 'punching_time'
                    'biometric_id':self.biometric_id.id,
                    'raw_user_id':pk_biometrico,
                    'imported':True
                })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asistencias',
            'res_model': 'employee.attendance.raw',
            'view_mode': 'tree',
            'target': 'current',
        }

    def convert_local_to_utc(self, local_dt):
        """
        Convierte una fecha naive (sin tz) desde la zona horaria del usuario actual a UTC.
        """
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)

        # Asegurar que sea naive antes de localizar
        if local_dt.tzinfo is None:
            local_dt = local_tz.localize(local_dt)

        # ✅ Convertir a UTC
        return local_dt.astimezone(pytz.utc).replace(tzinfo=None)