# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import models, fields, api, _


class BiotimeSyncWizard(models.TransientModel):
    _name = 'biotime.sync.wizard'
    _description = 'Biotime Sync Wizard'

    sync_type = fields.Selection([
        ('employees', 'Employees Only'),
        ('attendance', 'Attendance Only'),
        ('full', 'Full Sync'),
    ], string='Sync Type', required=True, default='full',
       help='Select what to synchronize from Biotime')
    
    date_from = fields.Date(
        string='Date From',
        default=lambda self: date.today(),
        help='Start date for attendance synchronization'
    )
    date_to = fields.Date(
        string='Date To',
        default=lambda self: date.today(),
        help='End date for attendance synchronization'
    )

    @api.onchange('sync_type')
    def _onchange_sync_type(self):
        """Set default date range when sync type changes."""
        if self.sync_type == 'attendance':
            self.date_from = date.today()
            self.date_to = date.today()

    def action_sync(self):
        """Execute the selected sync operation.
        
        Returns:
            dict: Action displaying sync results
        """
        self.ensure_one()
        
        config = self.env['biotime.config'].get_config()
        
        results = {
            'employees': None,
            'attendance': None,
        }
        
        # Execute sync based on selected type
        if self.sync_type in ('employees', 'full'):
            results['employees'] = config.sync_employees()
        
        if self.sync_type in ('attendance', 'full'):
            results['attendance'] = config.sync_attendance(self.date_from, self.date_to)
        
        # Build result message
        message_parts = []
        total_created = 0
        total_updated = 0
        total_skipped = 0
        has_errors = False
        
        if results['employees']:
            emp_result = results['employees']
            total_created += emp_result.get('records_created', 0)
            total_updated += emp_result.get('records_updated', 0)
            total_skipped += emp_result.get('records_skipped', 0)
            
            message_parts.append(
                _("Employees: %d updated, %d skipped") % (
                    emp_result.get('records_updated', 0),
                    emp_result.get('records_skipped', 0)
                )
            )
            
            if emp_result.get('status') == 'error':
                has_errors = True
                message_parts.append(_("Employee sync error: %s") % emp_result.get('error_message', ''))
        
        if results['attendance']:
            att_result = results['attendance']
            total_created += att_result.get('records_created', 0)
            total_updated += att_result.get('records_updated', 0)
            total_skipped += att_result.get('records_skipped', 0)
            
            message_parts.append(
                _("Attendance: %d created, %d updated, %d skipped") % (
                    att_result.get('records_created', 0),
                    att_result.get('records_updated', 0),
                    att_result.get('records_skipped', 0)
                )
            )
            
            if att_result.get('status') == 'error':
                has_errors = True
                message_parts.append(_("Attendance sync error: %s") % att_result.get('error_message', ''))
        
        # Determine notification type
        notification_type = 'danger' if has_errors else 'success'
        title = _('Sync Completed with Errors') if has_errors else _('Sync Completed Successfully')
        
        # Build summary message
        summary = _("Total: %d created, %d updated, %d skipped") % (
            total_created, total_updated, total_skipped
        )
        
        full_message = '\n'.join(message_parts + [summary])
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': full_message,
                'type': notification_type,
                'sticky': has_errors,
            }
        }
