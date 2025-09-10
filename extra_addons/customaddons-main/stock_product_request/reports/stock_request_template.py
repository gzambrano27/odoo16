#!/usr/bin/env python
# -*- coding: utf-8 -*-
from odoo import models
from odoo.osv import query


class MrpBomExplodedView(models.AbstractModel):
    _name = "report.stock_request_product.stock_request_template.xlsx"
    _inherit = "report.report_xlsx.abstract"

    def get_db(self, workbook, text):
        sheet = workbook.add_worksheet("Products")
        sheet.set_landscape()
        sheet.fit_to_pages(1, 0)
        sheet.autofilter("A1:C1")
        sheet.freeze_panes(1, 0)
        header = [
            {"header": "CODE", "format": text},
            {"header": "BARCODE", "format": text},
            {"header": "NAME"},
        ]
        data = []
        query = """
        SELECT pp.default_code,
               pp.barcode,
               pt.name,
               ARRAY(
                 SELECT CONCAT(pa.name, ': ', pav.name)
                   FROM product_attribute_value_product_product_rel pavppr
                        JOIN product_attribute_value pav ON
                               pavppr.product_attribute_value_id = pav.id
                        JOIN product_attribute pa ON
                               pav.attribute_id = pa.id
                  WHERE pavppr.product_product_id = pp.id) AS attributes
          FROM product_product pp
               JOIN product_template pt ON
                      pp.product_tmpl_id = pt.id
         WHERE pp.active IS TRUE
         ORDER BY pp.default_code
        """
        self.env.cr.execute(query)
        product_ids = self.env.cr.dictfetchall()
        count = 0
        for count, prod in enumerate(product_ids, start=1):
            name = prod.get("name")
            if prod.get("attributes"):
                name += " ({attr})".format(
                    attr=",".join(map(str, prod.get("attributes")))
                )
            data.append([prod.get("default_code"), prod.get("barcode"), name])
        if data:
            sheet.add_table(
                "A1:C{}".format(count),
                {
                    "name": "products",
                    "data": data,
                    "columns": header,
                    "style": "Table Style Light 11",
                },
            )
            workbook.define_name("base", "=Products!$A$1:$C${}".format(count))
            workbook.define_name("base_a", "=Products!$A$1:$A${}".format(count))
            workbook.define_name("base_b", "=Products!$B$1:$B${}".format(count))
        return sheet

    def generate_xlsx_report(self, workbook, data, objs):
        for row in objs:
            text = workbook.add_format({"num_format": "@"})
            bold = workbook.add_format({"bold": True})
            sheet = workbook.add_worksheet("Request")
            sheet.set_landscape()
            sheet.fit_to_pages(1, 0)
            sheet.autofilter("A1:E1")
            sheet.freeze_panes(1, 0)
            self.get_db(workbook, text)
            header = [
                "CODE",
                "BARCODE",
                "PRODUCT",
                "WAREHOUSE",
                "TYPE",
            ]
            warehouse = row.wh_to or row.wh_to.search([("id", "!=", row.wh_from.id)])
            header += ["{}|{}".format(wh.code, wh.name) for wh in warehouse]
            sheet.write_row(0, 0, header, bold)
            sheet.data_validation(
                "E2:E700", {"validate": "list", "source": ["bring", "send"]}
            )
            sheet.data_validation(
                "D2:D700", {"validate": "list", "source": [row.wh_from.code]}
            )
            for i in range(2, 700):
                sheet.write(i, 0, "", text)
                sheet.write(i, 1, "", text)
                sheet.write_formula(
                    "C{}".format(i),
                    "=INDEX(base,IF(ISBLANK(B{index}), MATCH(A{index}, base_a, 0), MATCH(B{index}, base_b, 0)), 3)".format(
                        index=i
                    ),
                )
