# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BiotimeSyncLog(models.Model):
    _name = 'biotime.sync.log'
    _description = 'Biotime Sync Log'
    _order = 'sync_date desc'

    sync_date = fields.Datetime(
        string='Sync Date',
        required=True,
        default=fields.Datetime.now,
        index=True,
        help='Date and time when the synchronization was executed',
    )
    sync_type = fields.Selection([
        ('employees', 'Employees'),
        ('attendance', 'Attendance'),
        ('full', 'Full Sync'),
    ], string='Sync Type', required=True, index=True,
       help='Type of synchronization performed')
    records_created = fields.Integer(
        string='Records Created',
        default=0,
        help='Number of new records created during sync',
    )
    records_updated = fields.Integer(
        string='Records Updated',
        default=0,
        help='Number of existing records updated during sync',
    )
    records_skipped = fields.Integer(
        string='Records Skipped',
        default=0,
        help='Number of records skipped during sync (e.g., unmapped employees)',
    )
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('partial', 'Partial'),
    ], string='Status', required=True, default='success', index=True,
       help='Result status of the synchronization')
    duration = fields.Float(
        string='Duration (seconds)',
        default=0.0,
        help='Time taken to complete the synchronization in seconds',
    )
    error_message = fields.Text(
        string='Error Message',
        help='Error details if the sync failed or had issues',
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        index=True,
        help='User who triggered the synchronization',
    )
