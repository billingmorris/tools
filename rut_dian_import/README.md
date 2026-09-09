# Importar Contacto desde RUT (PDF DIAN) — Odoo 16 Community

Módulo que agrega un asistente en **Contactos → Configuración → Importar
desde RUT (PDF)** para crear (o actualizar) un contacto a partir del PDF
del RUT expedido por la DIAN.

## ¿Por qué OCR?

El PDF del RUT que genera la DIAN **no tiene capa de texto**: cada hoja es
en realidad una imagen (se comprobó con el archivo de ejemplo
`RUT_PROVEO_NET_S_A_S_.pdf`: 0 caracteres de texto, 1 imagen por página).
Por eso el módulo usa `pdfplumber` para rasterizar cada página y
`pytesseract` (Tesseract OCR) para reconocer el texto, en lugar de leer
texto embebido.

**El OCR nunca es 100% exacto sobre un formulario escaneado.** Por eso el
asistente tiene una pantalla intermedia de **revisión/edición** de los
datos antes de crear el contacto: nunca crea el contacto "a ciegas".

## Instalación

1. Copie la carpeta `rut_dian_import` a su carpeta de addons de Odoo 16.
2. Instale las dependencias Python en el entorno del servidor Odoo:

   ```bash
   pip install pdfplumber pytesseract Pillow
   ```

3. Instale Tesseract OCR y el paquete de idioma español (Debian/Ubuntu):

   ```bash
   apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils
   ```

4. Actualice la lista de aplicaciones e instale el módulo
   **"Importar Contacto desde RUT (PDF DIAN)"** desde Odoo.

## Uso

1. Vaya a **Contactos → Configuración → Importar desde RUT (PDF)**.
2. Adjunte el PDF del RUT.
3. Pulse **"Extraer datos del PDF"**.
4. Revise/corrija los campos (NIT, razón social, dirección, ciudad,
   departamento, teléfonos, correo, representante legal, etc.).
5. Pulse **"Crear contacto"**.

## Mapeo de campos (formulario RUT → `res.partner`)

| Casilla RUT                              | Campo en Odoo (`res.partner`)      |
|-------------------------------------------|-------------------------------------|
| 24. Tipo de contribuyente                 | `company_type` / `is_company`       |
| 5-6. NIT y DV                             | `vat` (formato `NIT-DV`)            |
| 35. Razón social (o 33-34 nombres)        | `name`                              |
| 36. Nombre comercial                      | `comment` (referencia)              |
| 38. País                                  | `country_id`                        |
| 39. Departamento                          | `state_id`                          |
| 40. Ciudad/Municipio                      | `city`                              |
| 41. Dirección principal                   | `street`                            |
| 42. Correo electrónico                    | `email`                             |
| 44. Teléfono 1                            | `phone`                             |
| 45. Teléfono 2                            | `mobile`                            |
| Hoja 3 — Representación (nombre + doc.)   | Contacto hijo (`type=contact`, `function="Representante legal"`) |

## Notas y posibles mejoras

* Si su instancia tiene instalada la localización colombiana (`l10n_co`),
  se puede extender el wizard para completar también
  `l10n_latam_identification_type_id` y el tipo de documento DIAN.
* La extracción de Departamento/Ciudad depende de que el nombre coincida
  (aunque sea parcialmente) con los registros de `res.country.state` /
  no existe un modelo de municipios en Odoo estándar, por lo que la
  ciudad se guarda como texto libre en `city`.
* Puede editar las expresiones regulares en
  `wizard/rut_import_wizard.py::_parse_rut_text` si la DIAN cambia el
  formato del formulario o si su copia escaneada tiene menor calidad.
