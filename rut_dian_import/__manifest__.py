# -*- coding: utf-8 -*-
{
    'name': 'Importar Contacto desde RUT (PDF DIAN)',
    'version': '16.0.1.0.0',
    'category': 'Contacts',
    'summary': 'Crea contactos en Odoo a partir del PDF del Registro Único Tributario (RUT - DIAN Colombia)',
    'description': """
Importar Contacto desde RUT (PDF DIAN)
=======================================

Este módulo agrega un asistente (wizard) en Contactos que permite:

* Adjuntar el PDF del RUT (Registro Único Tributario) expedido por la DIAN.
* Extraer automáticamente el texto del PDF mediante OCR (el RUT de la DIAN
  se genera como una imagen escaneada, sin capa de texto).
* Mapear los campos del formulario RUT a los campos estándar de
  ``res.partner`` (NIT, razón social, nombre comercial, dirección, ciudad,
  departamento, país, correo, teléfonos, tipo de contribuyente y
  representante legal).
* Mostrar una pantalla de revisión donde el usuario puede corregir
  cualquier dato antes de crear el contacto (el OCR sobre un formulario
  escaneado nunca es 100% exacto).
* Crear el contacto (y opcionalmente un contacto hijo con el representante
  legal) con un clic.

Mapeo de campos (RUT -> res.partner)
-------------------------------------
* Casilla 35 "Razón social" / 33-34 "Nombre(s)"  -> name
* Casilla 36 "Nombre comercial"                  -> comment / referencia
* Casilla 5-6 "NIT" y "DV"                       -> vat
* Casilla 24 "Tipo de contribuyente"             -> company_type / is_company
* Casilla 41 "Dirección principal"               -> street
* Casilla 40 "Ciudad/Municipio"                  -> city
* Casilla 39 "Departamento"                      -> state_id
* Casilla 38 "País"                              -> country_id
* Casilla 42 "Correo electrónico"                -> email
* Casilla 44 "Teléfono 1"                        -> phone
* Casilla 45 "Teléfono 2"                        -> mobile
* Hoja 3, "Representación" (nombre + identificación) -> contacto hijo

Requisitos externos (a instalar en el servidor Odoo)
-----------------------------------------------------
* Paquetes Python: ``pdfplumber``, ``pytesseract``, ``Pillow``
* Binario del sistema: ``tesseract-ocr`` con el paquete de idioma español
  (``tesseract-ocr-spa`` en Debian/Ubuntu)

  .. code-block:: bash

      pip install pdfplumber pytesseract Pillow
      apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils

Importante
----------
La extracción por OCR es una **ayuda**, no un proceso infalible: siempre
revise los datos en la pantalla de previsualización antes de confirmar la
creación del contacto.
    """,
    'author': 'Tu Empresa',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['contacts'],
    'external_dependencies': {
        'python': ['pdfplumber', 'pytesseract', 'PIL'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/rut_import_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
