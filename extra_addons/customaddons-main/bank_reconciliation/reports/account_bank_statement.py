#!/usr/bin/env python
import logging
from calendar import monthrange

from odoo import _, api, models


_logger = logging.getLogger(__name__)


class BankStatementReport(models.AbstractModel):
    _name = "report.bank_reconciliation.report_bank_statement"

    @api.model
    def get_month_name(self, month_selec):
        return (
            self.env["base.month"]
            .search([("number", "=", int(month_selec))], limit=1)
            .name
        )

    def _get_report_values(self, docids, data=None):
        docs = self.env["account.bank.statement.helper"].browse(docids)
        st = docs.statement_id
        year = int(st.date.strftime("%Y"))
        month = int(st.date.strftime("%m"))
        date_start = "{:0>4}-{:0>2}-01".format(year, month)
        date_end = "{:0>4}-{:0>2}-{:0>2}".format(
            year, month, monthrange(year, month)[1]
        )
        journal_id = docs.journal_id
        account_id = docs.journal_id.default_account_id
        docargs = {
            "doc_ids": docids,
            "doc_model": "account.bank.statement.helper",
            "docs": docs,
            "balance": 0.0,
            "moves": False,
            "old_moves": False,
            "excl_moves": False,
            "month": self.get_month_name(month),
            "get_month_name": self.get_month_name,
        }
        query = r"""
        SELECT move_id
          FROM account_move_line line
                 JOIN account_move move ON line.move_id = move.id
         WHERE line.account_id = {account} AND
               line.journal_id = {journal} AND
               line.date <= '{date}' AND
               move.state = 'posted'
         GROUP BY move_id HAVING COUNT(*) > 1
        """.format(
            account=account_id.id,
            journal=journal_id.id,
            date=date_end,
        )
        self.env.cr.execute(query)
        move_ids = self.env.cr.fetchall()
        move_ids = [m[0] for m in move_ids] if len(move_ids) > 1 else []
        move_line_obj = self.env["account.move.line"]
        domain0 = [
            ("account_id", "=", account_id.id),
            ("move_id.state", "=", "posted"),
            ("statement_id", "=", False),
            ("reconciled", "=", False),
            ("journal_id", "=", journal_id.id),
            ("date", ">=", date_start),
            ("date", "<=", date_end),
        ]
        domain1 = [
            ("account_id", "=", account_id.id),
            ("move_id.state", "=", "posted"),
            ("date", ">=", date_start),
            ("date", "<=", date_end),
            ("journal_id", "=", journal_id.id),
            ("statement_id", "!=", False),
            ("statement_id.date", ">", date_end),
        ]
        domain2 = [
            ("account_id", "=", account_id.id),
            ("move_id.state", "=", "posted"),
            ("statement_id", "=", False),
            ("reconciled", "=", False),
            ("journal_id", "=", journal_id.id),
            ("date", "<", date_start),
        ]
        domain3 = [
            ("account_id", "=", account_id.id),
            ("move_id.state", "=", "posted"),
            ("date", "<", date_start),
            ("statement_id", "!=", False),
            ("journal_id", "=", journal_id.id),
            ("statement_id.date", ">", date_end),
        ]

        if move_ids:
            domain0 += [("move_id", "not in", move_ids)]
            domain1 += [("move_id", "not in", move_ids)]
            domain2 += [("move_id", "not in", move_ids)]
            domain3 += [("move_id", "not in", move_ids)]
            docargs["excl_moves"] = move_line_obj.search(
                [
                    ("account_id", "=", account_id.id),
                    ("move_id", "in", move_ids),
                    ("move_id.state", "=", "posted"),
                    ("statement_id", "=", False),
                    ("reconciled", "=", False),
                    ("journal_id", "=", journal_id.id),
                    ("date", "<=", date_end),
                ],
                order="date",
            )
        balance_ids = self.env["account.move.line"].search(
            [
                ("account_id", "=", account_id.id),
                ("move_id.state", "=", "posted"),
                ("date", "<=", date_end),
            ]
        )
        if balance_ids:
            docargs["balance"] = sum(balance_ids.mapped("debit")) - sum(
                balance_ids.mapped("credit")
            )

        # MES A COMPROBAR
        moves = move_line_obj.search(domain0, order="date")
        moves += move_line_obj.search(domain1, order="date")
        moves = sorted(moves, key=lambda k: k["date"])

        # MESES ANTERIORES
        old_moves = move_line_obj.search(domain2, order="date")
        old_moves += move_line_obj.search(domain3, order="date")
        old_moves = sorted(old_moves, key=lambda k: k["date"])

        docargs["moves"] = moves
        docargs["old_moves"] = old_moves

        return docargs


class AccountBankStatementXlsx(models.AbstractModel):
    _name = "report.bank_reconciliation.bank_statement_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def get_report_values(self, docs):
        st = docs.statement_id
        year = int(st.date.strftime("%Y"))
        month = int(st.date.strftime("%m"))
        date_start = "{:0>4}-{:0>2}-01".format(year, month)
        date_end = "{:0>4}-{:0>2}-{:0>2}".format(
            year, month, monthrange(year, month)[1]
        )
        journal_id = docs.journal_id
        account_id = docs.journal_id.default_account_id
        month_name = (
            self.env["base.month"].search([("number", "=", month)], limit=1).name
        )
        query = r"""
        SELECT move_id
          FROM account_move_line line
                 JOIN account_move move ON line.move_id = move.id
         WHERE line.account_id = {account} AND
               line.journal_id = {journal} AND
               line.date <= '{date}' AND
               move.state = 'posted'
         GROUP BY move_id HAVING COUNT(*) > 1
        """.format(
            account=account_id.id,
            journal=journal_id.id,
            date=date_end,
        )
        self.env.cr.execute(query)
        move_ids = self.env.cr.fetchall()
        move_ids = [m[0] for m in move_ids] if len(move_ids) > 1 else []
        aml_obj = self.env["account.move.line"]
        excl_moves = moves = old_moves = aml_obj
        balance = 0
        domain0 = [
            ("account_id", "=", account_id.id),
            ("move_id.state", "=", "posted"),
            ("statement_id", "=", False),
            ("reconciled", "=", False),
            ("journal_id", "=", journal_id.id),
            ("date", ">=", date_start),
            ("date", "<=", date_end),
        ]
        domain1 = [
            ("account_id", "=", account_id.id),
            ("move_id.state", "=", "posted"),
            ("date", ">=", date_start),
            ("date", "<=", date_end),
            ("journal_id", "=", journal_id.id),
            ("statement_id", "!=", False),
            ("statement_id.date", ">", date_end),
        ]
        domain2 = [
            ("account_id", "=", account_id.id),
            ("move_id.state", "=", "posted"),
            ("statement_id", "=", False),
            ("reconciled", "=", False),
            ("journal_id", "=", journal_id.id),
            ("date", "<", date_start),
        ]
        domain3 = [
            ("account_id", "=", account_id.id),
            ("move_id.state", "=", "posted"),
            ("date", "<", date_start),
            ("statement_id", "!=", False),
            ("journal_id", "=", journal_id.id),
            ("statement_id.date", ">", date_end),
        ]

        if move_ids:
            domain0 += [("move_id", "not in", move_ids)]
            domain1 += [("move_id", "not in", move_ids)]
            domain2 += [("move_id", "not in", move_ids)]
            domain3 += [("move_id", "not in", move_ids)]
            excl_moves |= aml_obj.search(
                [
                    ("account_id", "=", account_id.id),
                    ("move_id", "in", move_ids),
                    ("move_id.state", "=", "posted"),
                    ("statement_id", "=", False),
                    ("reconciled", "=", False),
                    ("journal_id", "=", journal_id.id),
                    ("date", "<=", date_end),
                ],
                order="date",
            )
        balance_ids = self.env["account.move.line"].search(
            [
                ("account_id", "=", account_id.id),
                ("move_id.state", "=", "posted"),
                ("date", "<=", date_end),
            ]
        )
        if balance_ids:
            balance = sum(balance_ids.mapped("debit")) - sum(
                balance_ids.mapped("credit")
            )

        # MES A COMPROBAR
        moves |= aml_obj.search(domain0, order="date")
        moves |= aml_obj.search(domain1, order="date")
        moves = sorted(moves, key=lambda k: k["date"])

        # MESES ANTERIORES
        old_moves = aml_obj.search(domain2, order="date")
        old_moves += aml_obj.search(domain3, order="date")
        old_moves = sorted(old_moves, key=lambda k: k["date"])
        return excl_moves, moves, old_moves, balance, month_name

    def generate_xlsx_report(self, workbook, data, objs):
        sheet = workbook.add_worksheet(objs.statement_id.name.replace("/", "_"))
        text_format = workbook.add_format({"num_format": "@"})
        text_bold_format = workbook.add_format({"num_format": "@", "bold": True})
        number_format = workbook.add_format(
            {"num_format": '_(* #,##0.00_);_(* (#,##0.00);_(* "-"_);_(@_)'}
        )
        number_bold_format = workbook.add_format(
            {
                "num_format": '_(* #,##0.00_);_(* (#,##0.00);_(* "-"_);_(@_)',
                "bold": True,
            }
        )
        date_format = workbook.add_format({"num_format": "dd/mm/yyyy"})
        date_bold_format = workbook.add_format(
            {"num_format": "dd/mm/yyyy", "bold": True}
        )
        merge_format = workbook.add_format(
            {"align": "center", "valign": "vcenter", "bold": 1, "font_size": 15}
        )
        header_style = workbook.add_format({"bold": True, "bottom": 1})
        balance_style = workbook.add_format(
            {
                "bold": True,
                "top": 2,
                "num_format": '_(* #,##0.00_);_(* (#,##0.00);_(* "-"_);_(@_)',
            }
        )
        header = [
            _("FECHA"),  # A
            _("EMPRESA"),  # B
            _("NUM"),  # C
            _("DIARIO"),  # D
            _("DESCRIPCIÓN"),  # E
            _("REF"),  # F
            _("DEBE"),  # G
            _("HABER"),  # H
        ]
        excl_moves, moves, old_moves, balance, month = self.get_report_values(objs)
        sheet.merge_range(
            "A1:H1",
            _(
                "CONCILIACION BANCARIA {} - {}".format(
                    objs.statement_id.date,
                    objs.journal_id.default_account_id.display_name,
                )
            ),
            header_style,
        )
        sheet.merge_range(
            "A2:H2",
            _(
                "SALDO SEGÚN ESTADO DE CUENTA: {:0.4f}".format(
                    objs.statement_id.balance_end_real
                )
            ),
            header_style,
        )
        m1 = 5
        sheet.merge_range(
            "A4:H4",
            _("Movimientos no conciliados meses anteriores"),
            text_bold_format,
        )
        sheet.write_row(4, 0, header, header_style)
        old_debit = old_credit = 0
        for om in old_moves:
            sheet.set_row(m1, None, None, {"level": 1, "hidden": True})
            sheet.write(m1, 0, om.date, date_format)
            sheet.write(m1, 1, om.partner_id.name or "", text_format)
            sheet.write(m1, 2, om.bank_reference, text_format)
            sheet.write(m1, 3, om.journal_id.name or "", text_format)
            sheet.write(m1, 4, om.name or "", text_format)
            sheet.write(m1, 5, om.ref or "", text_format)
            sheet.write(m1, 6, om.debit or "", number_format)
            sheet.write(m1, 7, om.credit or "", number_format)
            old_debit += om.debit
            old_credit += om.credit
            m1 += 1
        sheet.write(m1, 5, "TOTAL", balance_style)
        sheet.write(m1, 6, old_debit, balance_style)
        sheet.write(m1, 7, old_credit, balance_style)
        m2 = m1 + 2

        sheet.merge_range(
            "A{line}:H{line}".format(line=m2),
            _("Movimientos no conciliados del mes de {}".format(month)),
            text_bold_format,
        )
        sheet.write_row(m2, 0, header, header_style)
        debit = credit = 0
        m2 += 1
        for m in moves:
            sheet.set_row(m2, None, None, {"level": 1, "hidden": True})
            sheet.write(m2, 0, m.date, date_format)
            sheet.write(m2, 1, m.partner_id.name or "", text_format)
            sheet.write(m2, 2, m.bank_reference, text_format)
            sheet.write(m2, 3, m.journal_id.name or "", text_format)
            sheet.write(m2, 4, m.name or "", text_format)
            sheet.write(m2, 5, m.ref or "", text_format)
            sheet.write(m2, 6, m.debit or "", number_format)
            sheet.write(m2, 7, m.credit or "", number_format)
            debit += m.debit
            credit += m.credit
            m2 += 1
        sheet.write(m2, 5, "TOTAL", balance_style)
        sheet.write(m2, 6, debit, balance_style)
        sheet.write(m2, 7, credit, balance_style)
        m3 = m2 + 3
        sheet.merge_range(
            "A{line}:B{line}".format(line=m3),
            "RESUMEN DEL EXTRACTO",
            text_bold_format,
        )
        sheet.write(m3, 0, "SALDO SEGUN ESTADO DE CUENTA")
        sheet.write(
            m3, 1, objs.statement_id.balance_end_real or 0.0, number_bold_format
        )
        sheet.write(m3 + 1, 0, "(-) NO COCILIADOS MESES ANTERIORES")
        sheet.write(m3 + 1, 1, old_credit, number_bold_format)
        sheet.write(m3 + 2, 0, "(+) NO COCILIADOS MESES ANTERIORES")
        sheet.write(m3 + 2, 1, old_debit, number_bold_format)
        sheet.write(m3 + 3, 0, "(-) NO COCILIADOS MES DE {}".format(month).upper())
        sheet.write(m3 + 3, 1, credit, number_bold_format)
        sheet.write(m3 + 4, 0, "(+) NO COCILIADOS MES DE {}".format(month).upper())
        sheet.write(m3 + 4, 1, debit, number_bold_format)
        sheet.write(m3 + 5, 0, "SALDO CONCILIADO")
        sheet.write(m3 + 5, 1, objs.statement_id.balance_end, number_bold_format)
        sheet.write(m3 + 6, 0, "SALDO EN LIBROS", text_bold_format)
        sheet.write(m3 + 6, 1, balance, number_bold_format)
        sheet.write(m3 + 7, 0, "DIFERENCIA (+/-) NC/DC", text_bold_format)
        sheet.write(
            m3 + 7, 1, objs.statement_id.balance_end - balance, number_bold_format
        )
