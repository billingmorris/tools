# -*- coding: utf-8 -*-
{
    'name': 'Calculadora Popup',
    'version': '16.0.1.0.0',
    'summary': 'Calculadora flotante accesible desde la barra de menú superior',
    'description': """
        Añade un botón de calculadora en la barra de menú superior de Odoo
        (junto a los botones de actividades y mensajes). Al hacer clic,
        abre un popup con una calculadora funcional disponible en cualquier
        vista: ventas, facturas, asientos contables, etc.
    """,
    'author': 'Custom',
    'category': 'Tools',
    'license': 'LGPL-3',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'calculadora_popup/static/src/css/calculadora.css',
            'calculadora_popup/static/src/xml/calculadora.xml',
            'calculadora_popup/static/src/js/calculadora.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
