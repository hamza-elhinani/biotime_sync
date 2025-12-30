# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    biotime_id = fields.Char(
        string='Biotime ID',
        help='Employee ID in the Biotime system',
        copy=False,
        index=True,
    )
    biotime_badge = fields.Char(
        string='Biotime Badge',
        help='Badge/barcode number used in the Biotime system',
        copy=False,
    )
