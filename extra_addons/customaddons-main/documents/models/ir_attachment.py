# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError, UserError
import base64
import io
import os
from odoo import models, api
from PyPDF2 import PdfFileWriter, PdfFileReader


class IrAttachment(models.Model):
    _inherit = ['ir.attachment']

    @api.model
    def _pdf_split(self, new_files=None, open_files=None):
        """Creates and returns new pdf attachments based on existing data.

        :param new_files: the array that represents the new pdf structure:
            [{
                'name': 'New File Name',
                'new_pages': [{
                    'old_file_index': 7,
                    'old_page_number': 5,
                }],
            }]
        :param open_files: array of open file objects.
        :returns: the new PDF attachments
        """
        vals_list = []
        pdf_from_files = [PdfFileReader(open_file, strict=False) for open_file in open_files]
        for new_file in new_files:
            output = PdfFileWriter()
            for page in new_file['new_pages']:
                input_pdf = pdf_from_files[int(page['old_file_index'])]
                page_index = page['old_page_number'] - 1
                output.addPage(input_pdf.getPage(page_index))
            with io.BytesIO() as stream:
                output.write(stream)
                vals_list.append({
                    'name': new_file['name'] + ".pdf",
                    'datas': base64.b64encode(stream.getvalue()),
                })
        return self.create(vals_list)

    def _create_document(self, vals):
        """
        Implemented by bridge modules that create new documents if attachments are linked to
        their business models.

        :param vals: the create/write dictionary of ir attachment
        :return True if new documents are created
        """
        # Special case for documents
        if vals.get('res_model') == 'documents.document' and vals.get('res_id'):
            document = self.env['documents.document'].browse(vals['res_id'])
            if document.exists() and not document.attachment_id:
                document.attachment_id = self[0].id
            return False

        # Generic case for all other models
        res_model = vals.get('res_model')
        res_id = vals.get('res_id')
        model = self.env.get(res_model)
        if model is not None and res_id and issubclass(type(model), self.pool['documents.mixin']):
            vals_list = [
                model.browse(res_id)._get_document_vals(attachment)
                for attachment in self
                if not attachment.res_field
            ]
            vals_list = [vals for vals in vals_list if vals]  # Remove empty values
            self.env['documents.document'].create(vals_list)
            return True
        return False
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Verificar si el archivo se está subiendo a una nota interna
            is_note_attachment = vals.get('res_model') == 'mail.compose.message'
            file_size = 0  # Inicializar tamaño del archivo

            # Validar si el archivo está en "datas" (almacenado en la base de datos)
            if 'datas' in vals and vals['datas']:
                file_size = len(base64.b64decode(vals['datas']))  # Decodificar Base64 para obtener tamaño real

            elif 'raw' in vals and vals['raw']:
                file_size = len(vals['raw'])

            # Validar si el archivo está en "store_fname" (almacenado en el sistema de archivos)
            elif 'store_fname' in vals:
                file_size = self._get_file_size(vals['store_fname'])

            # Validar si se subió el archivo mediante "attachment_ids" (caso de notas internas)
            elif 'attachment_ids' in vals and vals['attachment_ids']:
                attachments = self.env['ir.attachment'].browse(vals['attachment_ids'][0][2])
                for attachment in attachments:
                    if attachment.datas:
                        file_size = len(base64.b64decode(attachment.datas))
                    elif attachment.store_fname:
                        file_size = self._get_file_size(attachment.store_fname)

            # Lanzar error si el archivo es mayor a 2MB
            if file_size > 20 * 1024 * 1024:  # 2 MB
                error_msg = "No puedes adjuntar archivos mayores a 2 MB en una nota interna." if is_note_attachment else "No puedes subir archivos mayores a 2 MB."
                raise UserError(error_msg)
        attachments = super().create(vals_list)
        for attachment, vals in zip(attachments, vals_list):
            # the context can indicate that this new attachment is created from documents, and therefore
            # doesn't need a new document to contain it.
            if not self._context.get('no_document') and not attachment.res_field:
                attachment.sudo()._create_document(dict(vals, res_model=attachment.res_model, res_id=attachment.res_id))
        return attachments
    
    def _get_file_size(self, file_path):
        """ Obtiene el tamaño real de un archivo si se almacena en el sistema de archivos """
        full_path = os.path.join(self._storage_path(), file_path)
        return os.path.getsize(full_path) if os.path.exists(full_path) else 0

    def write(self, vals): 
        # Validar el tamaño del archivo antes de guardar
        if 'raw' in vals and vals['raw']:
            file_size =  len(vals['raw']) * 3 / 4  # Convertir Base64 a bytes
            if file_size > 20 * 1024 * 1024:  # 2 MB
                raise ValidationError("No puedes subir archivos mayores a 2 MB.")
        # Continuar con el flujo normal
        res = super(IrAttachment, self).write(vals)
        # Si no hay contexto que lo evite, crear documentos
        if not self._context.get('no_document'):
            self.filtered(lambda a: not (vals.get('res_field') or a.res_field)).sudo()._create_document(vals)
        return res
