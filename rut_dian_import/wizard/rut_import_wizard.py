# -*- coding: utf-8 -*-
import base64
import io
import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None


def _clean(text):
    """Colapsa espacios/saltos de línea múltiples para facilitar las regex."""
    if not text:
        return ''
    return re.sub(r'[ \t]+', ' ', text)


def _digits_only(text):
    return re.sub(r'\D', '', text or '')


def _search(pattern, text, group=1, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    if not m:
        return ''
    try:
        return (m.group(group) or '').strip(' \n\t.:|_-')
    except IndexError:
        return ''


class RutImportWizard(models.TransientModel):
    _name = 'rut.import.wizard'
    _description = 'Asistente de importación de contacto desde RUT (PDF DIAN)'

    state = fields.Selection(
        [('draft', 'Cargar PDF'),
         ('preview', 'Revisar datos'),
         ('done', 'Contacto creado')],
        default='draft', string='Estado')

    pdf_file = fields.Binary(string='Archivo RUT (PDF)', attachment=False)
    pdf_filename = fields.Char(string='Nombre del archivo')

    # --- Campos extraídos / editables antes de crear el contacto ---
    company_type = fields.Selection(
        [('company', 'Empresa (persona jurídica)'),
         ('person', 'Persona natural')],
        default='company', string='Tipo de contribuyente')

    name = fields.Char(string='Razón social / Nombre completo')
    trade_name = fields.Char(string='Nombre comercial')
    vat_number = fields.Char(string='NIT (sin DV)')
    vat_dv = fields.Char(string='Dígito de verificación (DV)')

    street = fields.Char(string='Dirección')
    city = fields.Char(string='Ciudad/Municipio')
    state_id = fields.Many2one('res.country.state', string='Departamento')
    country_id = fields.Many2one('res.country', string='País')

    email = fields.Char(string='Correo electrónico')
    phone = fields.Char(string='Teléfono 1')
    mobile = fields.Char(string='Teléfono 2 / Móvil')

    legal_rep_name = fields.Char(string='Representante legal')
    legal_rep_doc_type = fields.Char(string='Tipo doc. representante')
    legal_rep_vat = fields.Char(string='Identificación del representante legal')
    create_legal_rep_contact = fields.Boolean(
        string='Crear representante legal como contacto hijo', default=True)

    existing_partner_id = fields.Many2one(
        'res.partner', string='Actualizar contacto existente',
        help='Déjelo vacío para crear un contacto nuevo.')

    raw_text = fields.Text(string='Texto reconocido (OCR)', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Contacto creado', readonly=True)

    # ------------------------------------------------------------------
    # Extracción OCR
    # ------------------------------------------------------------------
    def _check_dependencies(self):
        missing = []
        if pdfplumber is None:
            missing.append('pdfplumber')
        if pytesseract is None or Image is None:
            missing.append('pytesseract / Pillow')
        if missing:
            raise UserError(_(
                "Faltan librerías Python en el servidor para leer el PDF: %s.\n"
                "Instálelas con:\n"
                "  pip install pdfplumber pytesseract Pillow\n"
                "Y asegúrese de tener instalado el binario 'tesseract-ocr' "
                "(con el paquete de idioma español 'tesseract-ocr-spa')."
            ) % ', '.join(missing))

    def _ocr_page(self, page):
        """Renderiza una página de pdfplumber a imagen y le aplica OCR."""
        img = page.to_image(resolution=300).original
        try:
            return pytesseract.image_to_string(img, lang='spa+eng')
        except Exception:
            # El paquete de idioma español puede no estar instalado.
            _logger.warning(
                "No se pudo usar el idioma 'spa' en Tesseract, "
                "reintentando en inglés únicamente.")
            return pytesseract.image_to_string(img, lang='eng')

    def action_extract(self):
        self.ensure_one()
        self._check_dependencies()
        if not self.pdf_file:
            raise UserError(_("Debe adjuntar el PDF del RUT antes de continuar."))

        pdf_bytes = base64.b64decode(self.pdf_file)
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                texts = []
                # Hoja 1: identificación / ubicación / clasificación.
                if len(pdf.pages) >= 1:
                    texts.append(_clean(self._ocr_page(pdf.pages[0])))
                # Hoja 3 (índice 2): representación legal, si existe.
                if len(pdf.pages) >= 3:
                    texts.append(_clean(self._ocr_page(pdf.pages[2])))
        except Exception as exc:
            raise UserError(_(
                "No fue posible procesar el PDF: %s") % exc)

        page1 = texts[0] if texts else ''
        page3 = texts[1] if len(texts) > 1 else ''
        full_text = '\n'.join(texts)

        values = self._parse_rut_text(page1, page3)
        values['raw_text'] = full_text
        values['state'] = 'preview'
        self.write(values)

        return self._reopen_view()

    # ------------------------------------------------------------------
    # Parsing / mapeo de campos
    # ------------------------------------------------------------------
    def _parse_rut_text(self, page1, page3):
        values = {}

        # --- Tipo de contribuyente (24) ---
        tipo = _search(r'Tipo de contribuyente[^\n]*\n\s*([^\n]{3,40})', page1)
        if tipo:
            values['company_type'] = 'person' if 'natural' in tipo.lower() else 'company'

        # --- NIT y DV (5-6) ---
        nit_block = _search(
            r'Identificaci[oó]n Tributaria \(NIT\)(.*?)(?:Direcci[oó]n seccional|12\.)',
            page1, flags=re.IGNORECASE | re.DOTALL)
        if nit_block:
            nit_digits = _digits_only(nit_block)
            if len(nit_digits) >= 9:
                # El DV es normalmente el último dígito del bloque leído.
                values['vat_number'] = nit_digits[:9]
                values['vat_dv'] = nit_digits[9:10] or ''
            elif nit_digits:
                values['vat_number'] = nit_digits

        # --- Razón social (35) o nombres (33-34) para persona natural ---
        razon_social = _search(r'Raz[oó]n social[^\n]*\n\s*([^\n]{3,120})', page1)
        if razon_social:
            values['name'] = razon_social.title() if razon_social.isupper() else razon_social

        # --- Nombre comercial (36) ---
        nombre_comercial = _search(r'Nombre comercial[^\n]*\n\s*([^\n]{3,120})', page1)
        if nombre_comercial:
            values['trade_name'] = nombre_comercial

        # --- País (38) ---
        pais = _search(r'\b38\.\s*Pa[ií]s[^\n]*\n\s*([A-ZÁÉÍÓÚÑa-záéíóúñ ]{3,40})', page1)
        country = False
        if pais:
            country = self.env['res.country'].search(
                [('name', '=ilike', pais.strip())], limit=1)
        if not country:
            # El RUT es un formulario colombiano: Colombia por defecto.
            country = self.env['res.country'].search(
                [('code', '=', 'CO')], limit=1)
        if country:
            values['country_id'] = country.id

        # --- Departamento (39) ---
        depto = _search(
            r'\b39\.\s*Departamento[^\n]*\n[^\n]*?([A-ZÁÉÍÓÚÑa-záéíóúñ]{4,30})\s+\d',
            page1)
        if depto and country:
            state = self.env['res.country.state'].search(
                [('country_id', '=', country.id), ('name', '=ilike', depto.strip())],
                limit=1)
            if not state:
                state = self.env['res.country.state'].search(
                    [('country_id', '=', country.id),
                     ('name', 'ilike', depto.strip())], limit=1)
            if state:
                values['state_id'] = state.id

        # --- Ciudad/Municipio (40) ---
        ciudad = _search(
            r'\b40\.\s*Ciudad/Municipio[^\n]*\n[^\n]*?([A-ZÁÉÍÓÚÑa-záéíóúñ]{3,30})\s+\d',
            page1)
        if ciudad:
            values['city'] = ciudad.strip().title()

        # --- Dirección principal (41) ---
        direccion = _search(r'Direcci[oó]n principal[^\n]*\n\s*([^\n]{4,100})', page1)
        if direccion:
            values['street'] = direccion.strip()

        # --- Correo electrónico (42) ---
        correo = _search(r'([\w.\-]+@[\w\-]+\.[a-zA-Z]{2,})', page1)
        if correo:
            values['email'] = correo.lower()

        # --- Teléfono 1 y 2 (44-45) ---
        tel1 = _search(r'Tel[eé]fon[oq]\s*1[^\d]{0,25}(\d[\d ]{5,15}\d)', page1)
        if tel1:
            values['phone'] = _digits_only(tel1)
        tel2 = _search(r'Tel[eé]fon[oq]\s*2[^\d]{0,25}(\d[\d ]{5,15}\d)', page1)
        if tel2:
            values['mobile'] = _digits_only(tel2)

        # --- Representante legal (hoja 3) ---
        if page3:
            apellido1 = _search(r'104\.\s*Primer apellido[^\n]*\n\s*([^\n]{2,40})', page3)
            apellido2 = _search(r'105\.\s*Segundo apellido[^\n]*\n\s*([^\n]{0,40})', page3)
            nombre1 = _search(r'106\.\s*Primer nombre[^\n]*\n\s*([^\n]{2,40})', page3)
            otros_nombres = _search(r'107\.\s*Otros nombres[^\n]*\n\s*([^\n]{0,40})', page3)
            nombre_completo = ' '.join(
                p.strip() for p in
                [nombre1, otros_nombres, apellido1, apellido2] if p and p.strip())
            if nombre_completo:
                values['legal_rep_name'] = nombre_completo.title()

            tipo_doc = _search(r'100\.\s*Tipo de documento[^\n]*\n\s*([^\n]{3,40})', page3)
            if tipo_doc:
                values['legal_rep_doc_type'] = tipo_doc.strip()

            doc_num = _search(
                r'101\.\s*N[uú]mero de identificaci[oó]n(.*?)(?:102\.|103\.)',
                page3, flags=re.IGNORECASE | re.DOTALL)
            if doc_num:
                digits = _digits_only(doc_num)
                if digits:
                    values['legal_rep_vat'] = digits

        return values

    # ------------------------------------------------------------------
    # Creación del contacto
    # ------------------------------------------------------------------
    def action_create_partner(self):
        self.ensure_one()
        if not self.name:
            raise UserError(_(
                "El campo 'Razón social / Nombre completo' es obligatorio "
                "para crear el contacto."))

        vat = self.vat_number or ''
        if vat and self.vat_dv:
            vat = '%s-%s' % (self.vat_number, self.vat_dv)

        partner_vals = {
            'name': self.name,
            'is_company': self.company_type == 'company',
            'company_type': self.company_type,
            'vat': vat or False,
            'street': self.street or False,
            'city': self.city or False,
            'state_id': self.state_id.id or False,
            'country_id': self.country_id.id or False,
            'email': self.email or False,
            'phone': self.phone or False,
            'mobile': self.mobile or False,
        }
        if self.trade_name:
            partner_vals['comment'] = _('Nombre comercial: %s') % self.trade_name

        if self.existing_partner_id:
            self.existing_partner_id.write(partner_vals)
            partner = self.existing_partner_id
        else:
            partner = self.env['res.partner'].create(partner_vals)

        if self.create_legal_rep_contact and self.legal_rep_name:
            existing_rep = self.env['res.partner'].search([
                ('parent_id', '=', partner.id),
                ('name', '=', self.legal_rep_name),
            ], limit=1)
            if not existing_rep:
                self.env['res.partner'].create({
                    'name': self.legal_rep_name,
                    'parent_id': partner.id,
                    'function': _('Representante legal'),
                    'type': 'contact',
                    'company_type': 'person',
                    'vat': self.legal_rep_vat or False,
                })

        self.write({'partner_id': partner.id, 'state': 'done'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_back_to_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})
        return self._reopen_view()

    def _reopen_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rut.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
