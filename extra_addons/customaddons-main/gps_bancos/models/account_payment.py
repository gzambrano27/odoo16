# coding: utf-8
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _, SUPERUSER_ID



class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_request_id=fields.Many2one("account.payment.request","Solicitud de Pagos")
    vat=fields.Char(related="partner_id.vat",store=False,readonly=True,string="# Identificacion")
    amount_residual=fields.Monetary(string="Valor Residual")
    payment_purchase_line_ids = fields.One2many('purchase.order.payment.line', 'payment_id', 'Ordenes')
    bank_macro_id = fields.Many2one("account.payment.bank.macro", "Macro",compute="_compute_bank_macro_id",store=True   ,readonly=True)
    ###########
    document_financial_id = fields.Many2one("document.financial", "Documento Bancario/Contrato",required=False)
    document_financial_payment_group_id = fields.Many2one("document.financial.line.payment.group", "Pago Bancario/Cobro Contrato",required=False)

    macro_request_counter = fields.Integer(
        string='Sol. Relacionadas',
        compute='_compute_payment_requests',
        store=False  #mejor dejarlo False para que siempre se actualice correctamente
    )

    name_account=fields.Char("# Cuenta",store=True)

    ref2 = fields.Char(
        string="Referencia 2",
    )

    @api.depends('state')
    def _compute_bank_macro_id(self):
        for brw_each in self:
            srch = self.env["account.payment.bank.macro.line"].sudo().search([('payment_id', '=', brw_each.id)])
            #name_accounts = srch and srch.mapped('bank_account_id.full_name') or []
            bank_macro_id = srch.mapped('bank_macro_id')
            brw_each.bank_macro_id = bank_macro_id and bank_macro_id.id or False
            #brw_each.name_account = name_accounts and ",".join(name_accounts) or ""

    @api.depends('state','bank_macro_id')
    def _compute_payment_requests(self):
        for brw_each in self:
            macro_request_ids = self.env["account.payment.request"]
            if brw_each.bank_macro_id:
                srch = self.env["account.payment.bank.macro.line"].sudo().search([
                    ('payment_id', '=', brw_each.id)
                ])
                macro_request_ids = srch.mapped('request_id')
            brw_each.macro_request_counter = len(macro_request_ids)

    def send_mail_payment_intercompany(self):
        for brw_each in self:
            if brw_each.partner_id:
                if brw_each.state=='posted' and brw_each.journal_id.type == 'bank':
                    if brw_each.amount!=0.00:
                        partner = brw_each.partner_id.sudo()
                        company_from_id = brw_each.company_id.sudo().id
                        # SQL: obtener company_id del partner si es compañía
                        self._cr.execute("""
                                        SELECT id
                                        FROM res_company
                                        WHERE partner_id = %s  
                                        LIMIT 1
                                    """, (partner.id,))
                        result = self._cr.fetchone()
                        company_to_id = result[0] if result else None
                        if (
                                partner and partner.is_company
                                and company_to_id
                                and company_from_id != company_to_id
                        ):
                            template = self.env.ref('gps_bancos.mail_template_payment_intercompany', raise_if_not_found=False)
                            if template:
                                template.sudo().send_mail(brw_each.id, force_send=True)
        return True


    def action_post(self):
        values=super(AccountPayment,self).action_post()
        self.update_request_states()
        self.update_order_payment_lines()
        self.update_payslip_payment_lines()
        self.send_mail_payment_intercompany()
        return values

    def action_draft(self):
        values=super(AccountPayment,self).action_draft()
        self.update_request_states()
        self.update_order_payment_lines()
        self.update_payslip_payment_lines()
        return values

    def action_cancel(self):
        values=super(AccountPayment,self).action_cancel()
        self.update_request_states()
        self.update_order_payment_lines()
        self.update_payslip_payment_lines()
        return values

    def update_request_states(self):
        for brw_each in self:
            if brw_each.payment_request_id:
                brw_each.payment_request_id.test_states()
        return True

    def unlink(self):
        for brw_each in self:
            brw_each.delete_payment_rel_purchases()
        return super(AccountPayment, self).unlink()

    def delete_payment_rel_purchases(self):
        for payment in self:
            # Eliminar líneas anteriores
            existing_lines = self.env['purchase.order.payment.line'].sudo().search([
                ('payment_id', '=', payment.id)
            ])
            if existing_lines:
                existing_lines.unlink()

            # existing_lines = self.env['purchase.order.payment.line'].sudo().search([
            #     ('payment_id', '=', payment.id)
            # ])
            # if existing_lines:
            #     existing_lines.unlink()

    @api.constrains("journal_id", "bank_reference")
    def _check_bank_reference(self):
        for row in self:
            pass

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []

        if name:
            domain = ['|', '|',
                      ('bank_reference', operator, name),
                      ('name', operator, name),
                      ('id', '=', name if name.isdigit() else 0)]

        records = self.search(domain + args, limit=limit)
        return records.name_get()

    @api.constrains('state', 'move_id.state', 'purchase_id','reversed_payment_id')
    def update_order_payment_lines(self):
        for payment in self:
            #pass
            #payment.delete_payment_rel_purchases()
            if payment.state=='posted':
                if not payment.reversed_payment_id:
                    # Verificar si el pago está vinculado a una o varias órdenes de compra
                    purchases = payment.purchase_id if payment.purchase_id else False
                    if purchases:
                        payment.payment_purchase_line_ids = [(5,),
                                                             (0,0,{
                                                                'order_id': purchases.id,
                                                                #'payment_id': payment.id,
                                                                'amount': payment.amount,
                                                            })  ]
                else:##si viene de una solicityd
                    payment.payment_purchase_line_ids = [(5,)]
            else:  ##si viene de una solicityd
                payment.payment_purchase_line_ids = [(5,)]

    def reverse_payment(self):
        self.ensure_one()
        payment=self
        srch_movement = self.env["hr.employee.movement.line"].sudo().search([('payment_id', '=', payment.id)])
        srch_payslip = self.env["hr.payslip"].sudo().search([('payment_id', '=', payment.id)])
        srch_payment = self.env["hr.employee.payment"].search([('state', '=', 'approved'),
                                                               '|',
                                                               ('movement_line_ids', 'in', srch_movement.ids),
                                                               ('payslip_line_ids', 'in', srch_payslip.ids)
                                                               ])
        if srch_payment:
            srch_payment.action_reversed_states()
        ########################################################################
        srch_liquidation_payment = self.env["hr.employee.liquidation"].search([('state', '=', 'paid'),
                                                                   ('payment_id', '=', payment.id)
                                                               ])
        if srch_liquidation_payment:
            srch_liquidation_payment.action_reversed_states()
        ########################################################################
        macro_summary = self.env['account.payment.bank.macro.summary'] \
            .sudo() \
            .with_context(active_test=False) \
            .search([
            ('intercompany_payment_id', '=', payment.id)
        ])
        if macro_summary:
            macro_summary.write({"accredited_other_company":False,
                                 'intercompany_payment_ref':None})
        ########################################################################
        return True


    @api.constrains('state', 'move_id.state','reversed_payment_id')
    def update_payslip_payment_lines(self):

        for payment in self:
            if payment.state == 'posted':
                if not payment.reversed_payment_id:
                    pass
                else:
                    payment.reverse_payment()
            else:
                payment.reverse_payment()

    def action_open_payment_requests(self):
        self.ensure_one()
        brw_each=self
        if brw_each.bank_macro_id:
            srch = self.env["account.payment.bank.macro.line"].sudo().search([
                ('payment_id', '=', brw_each.id)
            ])
            requests = srch.mapped('request_id')
            requests_ids = requests.ids + [-1, -1]
            id_action=(brw_each.bank_macro_id.type_module=='financial' and
                       "gps_bancos.account_payment_request_view_action" or
                       'gps_bancos.account_payment_request_payslip_view_action')
            action = self.env["ir.actions.actions"]._for_xml_id(
                id_action
            )
            action["domain"] = [('id', 'in', requests_ids)]
            action["context"]="{'create':False,'edit':False,'delete':False}"
            return action
        return True

    def get_mail_intercompany_to_send(self):
        self.ensure_one()
        brw_each=self
        OBJ_PARAM = self.env['ir.config_parameter'].sudo()
        mail_test_enable=OBJ_PARAM.get_param("mail.test.bank.enable","True")
        mail_send=OBJ_PARAM.get_param("mail.intercompany",False)
        if mail_test_enable in ("True","1"):
            mail_send=OBJ_PARAM.get_param("mail.test.bank",False)
            if not mail_send:
                mail_send=brw_each.email
        return mail_send