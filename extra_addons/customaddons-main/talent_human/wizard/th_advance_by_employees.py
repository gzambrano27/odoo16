from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools import float_compare
from datetime import date, timedelta, datetime



class hr_advance_employees(models.TransientModel):

    _name ='th.advance.employees'
    _description = 'Generate discount for all selected employees'
    
    
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_advance_rel', 'advance_id', 'employee_id', 'Employees')
    
    def cargar_employees(self):
        self.ensure_one()  # Asegura que la función se ejecute en un solo registro
        print('vino a cargar')
        run_pool = self.env['th.discount.run']
        id_discount_run = self.env.context.get('id', False)
        run_record = run_pool.browse(id_discount_run)

        if not run_record:
            raise UserError(_('No se encontró el registro de run.'))

        # from_date = run_record.date_start
        # to_date = run_record.date_end

        emp = []
        search_domain = [("identificador_company", "=", run_record.company_id.id)]
        if run_record.anticipo_serv_prestados:
            search_domain.append(('rol', 'in', ['ROL SERVICIOS PRESTADOS']))
        else:
            search_domain.append(('rol', 'in', ['ROL ADMINISTRATIVO']))
        

        emp.extend(self.env['employee.contract.info.view'].search(search_domain).ids)

        # ('date_from', '>=', from_date), ('date_to', '<=', to_date)
        # if run_record.anticipo_agricola:
        #     sql_partes = """
        #         SELECT DISTINCT employee_id, e.name_related
        #         FROM registro_partes_line pl
        #         INNER JOIN hr_employee e ON pl.employee_id = e.id
        #         INNER JOIN tipo_roles tr ON e.tipo_rol = tr.id
        #         WHERE date BETWEEN %s AND %s
        #         AND tr.name IN ('ROL AGRICOLA DESTAJO', 'ROL EMPAQUE', 'ROL COSECHA')
        #         AND COALESCE(pl.state, 'draft') = 'draft'
        #         ORDER BY 2
        #     """
        #     self.env.cr.execute(sql_partes, (from_date, to_date))
        #     results_parte = self.env.cr.dictfetchall()
        #     emp.extend([x['employee_id'] for x in results_parte])

        # if run_record.anticipo_serv_prestados:
        #     sql_partes = """
        #         SELECT DISTINCT employee_id, e.name_related
        #         FROM registro_partes_line pl
        #         INNER JOIN hr_employee e ON pl.employee_id = e.id
        #         INNER JOIN tipo_roles tr ON e.tipo_rol = tr.id
        #         WHERE date BETWEEN %s AND %s
        #         AND tr.name IN ('ROL SERVICIOS PRESTADOS', 'PLANTILLA')
        #         AND COALESCE(pl.state, 'draft') = 'draft'
        #         ORDER BY 2
        #     """
        #     self.env.cr.execute(sql_partes, (from_date, to_date))
        #     results_parte = self.env.cr.dictfetchall()
        #     emp.extend([x['employee_id'] for x in results_parte])

        if not emp:
            view = self.env.ref('sh_message.sh_message_wizard')
            context = dict(self._context or {})
            context['message'] = 'No hay partes que cargar para ese periodo de ese rol!!'
            return {
                'name': 'Mensaje',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'sh.message.wizard',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': context,
            }

        for record in self:
            record.employee_ids = [(6, 0, emp)]

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'th.advance.employees',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def obtiene_novedades(self, periodo, empleado, tipo, empresa):
        if empresa == 'INNOVAVERSA S.A.':
            sql_novedad = """
                select h.id,
                    (select name from establecimientos a where a.id = e.unidad_administrativa) unidad,
                    (select name from tipo_roles t where t.id = e.tipo_rol)tipo_rol,
                    e.name_related empleado,
                    (select name from hr_leave_type s where s.id = h.holiday_status_id)tipo_falta,
                    h.tipo_certificado,
                    case 
                        when cast(to_char(date(h.date_from), 'MMYYYY') as int)< cast('""" + periodo + """' as int) then
                            to_date('""" + periodo + """','mmyyyydd')
                        else
                            (case when cast(to_char(date(h.date_from), 'MMYYYY') as int)> cast('""" + periodo + """' as int) then
                                (date_trunc('MONTH', to_date('""" + periodo + """','mmyyyydd')::date))::DATE
                            else
                                date(h.date_from)
                            end)
                    end as fechainicio,
                    case 
                        when cast(to_char(date(h.date_to), 'MMYYYY') as int)> cast('""" + periodo + """' as int) then
                            (date_trunc('MONTH', to_date('""" + periodo + """','mmyyyydd')::date) + INTERVAL '1 MONTH - 1 day')::DATE
                        when cast(to_char(date(h.date_to), 'YYYY') as int) > cast(to_char(date(h.date_from), 'YYYY') as int) then
                            (case when cast(to_char(date(h.date_to), 'MMYYYY') as int) = cast('""" + periodo + """' as int) then
                                Date(h.date_to)
                            else
                                (date_trunc('MONTH', to_date('""" + periodo + """','mmyyyydd')::date) + INTERVAL '1 MONTH - 1 day')::DATE
                            end)
                        else
                            Date(h.date_to)
                    end as fechafin,
                    h.name causa,
                    case 
                        when h.es_medio_dia then
                            0.5
                        else
                            date(case 
                                when cast(to_char(date(h.date_to), 'MMYYYY') as int)> cast('""" + periodo + """' as int) then
                                    (date_trunc('MONTH', to_date('""" + periodo + """','mmyyyydd')::date) + INTERVAL '1 MONTH - 1 day')::DATE
                                when cast(to_char(date(h.date_to), 'YYYY') as int) > cast(to_char(date(h.date_from), 'YYYY') as int) then
                                    (case when cast(to_char(date(h.date_to), 'MMYYYY') as int) = cast('""" + periodo + """' as int) then
                                        Date(h.date_to)
                                    else
                                        (date_trunc('MONTH', to_date('""" + periodo + """','mmyyyydd')::date) + INTERVAL '1 MONTH - 1 day')::DATE
                                    end)
                                else
                                    Date(h.date_to)
                            end)-
                            date(case 
                                when cast(to_char(date(h.date_from), 'MMYYYY') as int)< cast('""" + periodo + """' as int) then
                                    to_date('""" + periodo + """','mmyyyydd')
                                else
                                    (case when cast(to_char(date(h.date_from), 'MMYYYY') as int)> cast('""" + periodo + """' as int) then
                                        (date_trunc('MONTH', to_date('""" + periodo + """','mmyyyydd')::date))::DATE
                                    else
                                        date(h.date_from)
                                    end)
                            end) + 1 
                    end dias,
                    (select periodo from hr_vacations_historic v where v.employee_id = h.employee_id and v.id = h.periodos) periodo_gozado,
                    to_char( h.date_to, 'MMYYYY'),
                    case when coalesce(h.es_pagado,False)=False then
                        'No'
                    else
                        'Si'
                    end pagado,
                    e.id emp_id,
                    (select id from hr_contract c where c.employee_id = e.id) contrato_id,
                    (select wage from hr_contract c where c.employee_id = e.id) sueldo,
                    (select porcentaje_rem_empleador from hr_leave_type s where s.id = h.holiday_status_id) porc_remuneracion
                from hr_leave h,
                    hr_employee e
                where h.employee_id = e.id
                    and (to_char( h.date_from, 'MMYYYY') =  '""" + periodo + """' or to_char( h.date_to, 'MMYYYY') =  '""" + periodo + """')
                    and h.employee_id = """ + str(empleado) + """
                    and h.holiday_status_id = """ + str(tipo) + """
                    --and coalesce(h.periodo_anticipado,False)<>True
                order by fechainicio
            """
            self.env.cr.execute(sql_novedad)
            return self.env.cr.dictfetchall()
    
    def compute_sheet(self):
        emp_pool = self.env['employee.contract.info.view']
        discount_pool = self.env['th.discount']
        run_pool = self.env['th.discount.run']
        contract_pool = self.env['hr.contract']
        discount_ids = []
        
        
        if not self.employee_ids:
            raise ValidationError(_('Warning ! Debe de seleccionar un empleado(s) para crear anticipo(s).'))

        context = self.env.context
        id_descto_run = context.get('id', False)
        
        # if context.get('anticipo_agricola', False):
        #     from_date = context.get('date_start', False)
        #     to_date = context.get('date_end', False)
        #     journal_id = context.get('journal_id', False)
        #     id_descto_run = context.get('id', False)
            
        #     sql_general = """
        #         SELECT e.id AS employee_id
        #         FROM hr_employee e
        #         INNER JOIN tipo_roles r ON e.tipo_rol = r.id
        #         WHERE r.name IN ('ROL AGRICOLA DESTAJO', 'ROL EMPAQUE', 'ROL COSECHA')
        #     """
            
        #     self.env.cr.execute(sql_general)
        #     results_gen = self.env.cr.dictfetchall()
        #     list_emp = [x['employee_id'] for x in results_gen]

        # elif context.get('anticipo_serv_prestados', False):
        #     from_date = context.get('date_start', False)
        #     to_date = context.get('date_end', False)
        #     journal_id = context.get('journal_id', False)
        #     id_descto_run = context.get('id', False)
            
        #     sql_general = """
        #         SELECT e.id AS employee_id
        #         FROM hr_employee e
        #         INNER JOIN tipo_roles r ON e.tipo_rol = r.id
        #         WHERE r.name IN ('ROL SERVICIOS PRESTADOS', 'PLANTILLA')
        #     """
            
        #     self.env.cr.execute(sql_general)
        #     results_gen = self.env.cr.dictfetchall()
        #     list_emp = [x['employee_id'] for x in results_gen]

        # else:
        #     if context.get('active_ids', []):
        #         id_descto_run = context['active_id']
        #     employee_ids = context.get('employee_ids')[0][2]
        #     list_emp = list(set(self.employee_ids.ids + employee_ids))
        
        # if not list_emp:
        #     view = self.env.ref('sh_message.sh_message_wizard')
        #     context = dict(self._context or {})
        #     context['message'] = 'No hay registros que procesar!!'
        #     return {
        #         'name': 'Mensaje',
        #         'type': 'ir.actions.act_window',
        #         'view_type': 'form',
        #         'view_mode': 'form',
        #         'res_model': 'sh.message.wizard',
        #         'views': [(view.id, 'form')],
        #         'view_id': view.id,
        #         'target': 'new',
        #         'context': context,
        #     }

        run_record = run_pool.browse(id_descto_run)
        from_date = run_record.date_registro
        to_date = run_record.date_end
        name = run_record.transaction_type_id.id
        ref = run_record.name
        domain = [('identificador_company', '=', run_record.company_id.id)]
        if run_record.anticipo_serv_prestados:
            domain.append(('rol', 'in', ['ROL SERVICIOS PRESTADOS']))
            from_date = run_record.date_start
        else:
            domain.append(('rol', 'in', ['ROL ADMINISTRATIVO']))
        
        for emp in self.env['employee.contract.info.view'].search(domain):
            name = run_record.transaction_type_id.id
            ref = f'descuento por anticipo nomina {emp.nombre_empleado} periodo {from_date} al {to_date} de {run_record.company_id.name}'
            contract_id = self.env['hr.contract'].search([('employee_id', '=', emp.id)], limit=1)
            amount = 0
            method_payment = emp.metodo_pago_quincenal
            value_method = emp.valor
            
            if not emp.metodo_pago_quincenal and emp.valor <= 0:
                method_payment = 'percent'
                value_method = 50
            
                

            amount = emp.sueldo*(value_method/100) if method_payment == 'percent' else emp.valor

            if from_date < emp.fecha_ingreso < to_date:
                # Calcular los días efectivos del contrato dentro del período de la nómina
                days_in_period = (to_date - from_date).days + 1
                contract_days = (to_date - emp.fecha_ingreso).days + 1
                prorrateo = contract_days / days_in_period
                # Ajustar el monto según el prorrateo
                amount = amount * prorrateo
            
            if emp.fecha_ingreso > to_date:
                amount = 0
            

            res = {
                    'name': name or False,
                    'ref': ref or False,
                    'employee_id': emp.id,                
                    'date': from_date,
                    'date_from': to_date,
                    'contract_id': contract_id.id,
                    'amount_to_paid': amount,
                    'advance_run_id': id_descto_run,
                }
            discount_ids.append(discount_pool.create(res))

        # if not list_emp:
        #     raise ValidationError(_('Warning ! Debe de seleccionar un empleado(s) para crear anticipo(s).'))

        # for emp in emp_pool.browse(list_emp):
        #     contract_id = contract_pool.search([('employee_id', '=', emp.id)], limit=1)
            
        #     if self.env.user.company_id.name == 'Fanalba S.A.' and contract_id.type_id.name in ['INDEFINIDO', 'Contrato Indefinido', 'CONTRATO EVENTUAL CONTINUO']:
        #         if contract_id.modo_1q == 'cantidad':
        #             amount = contract_id.valor
        #         elif contract_id.modo_1q == 'porcentaje' and contract_id.wage > 0:
        #             obj_inco_ids = self.env['hr.contract.income'].search([('contract_id', '=', contract_id.id)])
        #             adicional = sum([i.amount for i in obj_inco_ids])
        #             hora50 = (contract_id.wage / 240) * 1.5 * contract_id.numero_hora_50 if contract_id.numero_hora_50 else 0
        #             hora100 = (contract_id.wage / 240) * 2 * contract_id.numero_hora_100 if contract_id.numero_hora_100 else 0
        #             amount = ((contract_id.wage + adicional + hora50 + hora100) * contract_id.valor) / 100
        #         else:
        #             raise ValidationError(_('Warning ! El empleado no tiene Valor de contrato o no tiene contrato: %s') % emp.name_related)
        #     else:
        #         # Implementación de lógica específica según tipo de anticipo y empleado
        #         # [Lógica omitida por brevedad]
        #         pass

        #     factor = 1
        #     if amount > 0:
        #         res = {
        #             'name': name or False,
        #             'ref': ref or False,
        #             'employee_id': emp.id,                
        #             'date': from_date,
        #             'date_from': to_date,
        #             'contract_id': contract_id.id,
        #             'amount': amount * factor,
        #             'advance_run_id': id_descto_run,
        #         }
        #         discount_ids.append(discount_pool.create(res))

        return {
            'name': _('Anticipo Run'),
            'view_mode': 'form',
            'view_id': self.env.ref('talent_human.hr_discount_run_form').id,
            'res_model': 'th.discount.run',
            'res_id': id_descto_run,
            'context': "{}",
            'type': 'ir.actions.act_window',
        }
