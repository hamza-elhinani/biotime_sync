# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BiotimeAttendance(models.Model):
    _name = 'biotime.attendance'
    _description = 'Biotime Attendance'
    _order = 'date desc, employee_id'

    # Core Fields
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True,
    )
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
    )
    check_in = fields.Datetime(
        string='Check In',
    )
    check_out = fields.Datetime(
        string='Check Out',
    )
    biotime_transaction_id = fields.Char(
        string='Biotime Transaction ID',
        help='External reference ID from Biotime system',
        copy=False,
        index=True,
    )
    
    # Link to Odoo hr.attendance
    hr_attendance_id = fields.Many2one(
        'hr.attendance',
        string='Odoo Attendance',
        ondelete='set null',
        help='Linked record in Odoo native attendance module',
    )
    synced_to_hr = fields.Boolean(
        string='Synced to HR Attendance',
        default=False,
        help='Whether this record has been synced to hr.attendance',
    )

    # Status Field (computed)
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('leave', 'Leave'),
        ('half_day', 'Half Day'),
        ('incomplete', 'Incomplete'),
    ], string='Status', compute='_compute_status', store=True, default='present')

    # Computed Fields
    worked_hours = fields.Float(
        string='Worked Hours',
        compute='_compute_worked_hours',
        store=True,
        help='Total worked hours calculated as (check_out - check_in) - break_duration',
    )
    is_late = fields.Boolean(
        string='Is Late',
        compute='_compute_late_status',
        store=True,
        help='True if employee checked in after work_start_time + late_tolerance',
    )
    late_minutes = fields.Integer(
        string='Late Minutes',
        compute='_compute_late_status',
        store=True,
        help='Number of minutes late (0 if not late)',
    )
    overtime_hours = fields.Float(
        string='Overtime Hours',
        compute='_compute_overtime',
        store=True,
        help='Hours worked beyond the overtime threshold',
    )

    _sql_constraints = [
        ('unique_employee_date', 'unique(employee_id, date)',
         'An attendance record already exists for this employee on this date.'),
    ]

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        """Compute worked hours as (check_out - check_in) - break_duration."""
        config = self.env['biotime.config'].get_config()
        break_duration_hours = config.break_duration / 60.0
        
        for record in self:
            if record.check_in and record.check_out:
                delta = record.check_out - record.check_in
                total_hours = delta.total_seconds() / 3600.0
                record.worked_hours = max(0, total_hours - break_duration_hours)
            else:
                record.worked_hours = 0.0

    @api.depends('check_in')
    def _compute_late_status(self):
        """Compute late status based on check_in time vs work_start_time + tolerance."""
        config = self.env['biotime.config'].get_config()
        work_start_time = config.work_start_time
        late_tolerance = config.late_tolerance
        
        for record in self:
            if record.check_in:
                check_in_hour = record.check_in.hour
                check_in_minute = record.check_in.minute
                check_in_total_minutes = check_in_hour * 60 + check_in_minute
                work_start_minutes = int(work_start_time * 60)
                minutes_after_start = check_in_total_minutes - work_start_minutes
                record.late_minutes = max(0, minutes_after_start)
                record.is_late = minutes_after_start > late_tolerance
            else:
                record.is_late = False
                record.late_minutes = 0

    @api.depends('worked_hours')
    def _compute_overtime(self):
        """Compute overtime hours."""
        config = self.env['biotime.config'].get_config()
        overtime_threshold = config.overtime_threshold
        
        for record in self:
            record.overtime_hours = max(0, record.worked_hours - overtime_threshold)

    @api.depends('check_in', 'check_out', 'is_late', 'worked_hours')
    def _compute_status(self):
        """Compute attendance status."""
        config = self.env['biotime.config'].get_config()
        expected_hours = config.work_end_time - config.work_start_time - (config.break_duration / 60.0)
        half_day_threshold = expected_hours / 2.0
        
        for record in self:
            if not record.check_in:
                record.status = 'absent'
            elif not record.check_out:
                record.status = 'incomplete'
            elif record.is_late:
                record.status = 'late'
            elif record.worked_hours < half_day_threshold:
                record.status = 'half_day'
            else:
                record.status = 'present'

    def sync_to_hr_attendance(self):
        """Sync biotime attendance records to Odoo hr.attendance module."""
        HrAttendance = self.env['hr.attendance']
        synced_count = 0
        errors = []
        
        for record in self:
            if not record.check_in:
                continue
            
            try:
                if record.hr_attendance_id:
                    # Update existing record
                    vals = {'check_in': record.check_in}
                    if record.check_out:
                        vals['check_out'] = record.check_out
                    record.hr_attendance_id.sudo().write(vals)
                    record.synced_to_hr = True
                    synced_count += 1
                    _logger.info("Updated hr.attendance %s for %s", 
                                record.hr_attendance_id.id, record.employee_id.name)
                else:
                    # Check if hr.attendance already exists for this employee/check_in
                    existing = HrAttendance.sudo().search([
                        ('employee_id', '=', record.employee_id.id),
                        ('check_in', '>=', record.check_in.replace(hour=0, minute=0, second=0)),
                        ('check_in', '<', record.check_in.replace(hour=23, minute=59, second=59)),
                    ], limit=1)
                    
                    if existing:
                        # Link to existing and update
                        vals = {'check_in': record.check_in}
                        if record.check_out:
                            vals['check_out'] = record.check_out
                        existing.sudo().write(vals)
                        record.write({
                            'hr_attendance_id': existing.id,
                            'synced_to_hr': True,
                        })
                        synced_count += 1
                        _logger.info("Linked existing hr.attendance %s for %s", 
                                    existing.id, record.employee_id.name)
                    else:
                        # Create new hr.attendance record
                        vals = {
                            'employee_id': record.employee_id.id,
                            'check_in': record.check_in,
                        }
                        if record.check_out:
                            vals['check_out'] = record.check_out
                        
                        hr_attendance = HrAttendance.sudo().create(vals)
                        record.write({
                            'hr_attendance_id': hr_attendance.id,
                            'synced_to_hr': True,
                        })
                        synced_count += 1
                        _logger.info("Created hr.attendance %s for %s on %s", 
                                    hr_attendance.id, record.employee_id.name, record.date)
                        
            except Exception as e:
                error_msg = f"Failed to sync attendance for {record.employee_id.name} on {record.date}: {str(e)}"
                errors.append(error_msg)
                _logger.warning(error_msg)
        
        if errors:
            _logger.warning("Sync completed with %d errors: %s", len(errors), '; '.join(errors[:5]))
        
        return synced_count

    @api.model
    def sync_all_to_hr_attendance(self):
        """Sync all unsynced biotime attendance records to hr.attendance."""
        unsynced = self.search([
            ('synced_to_hr', '=', False),
            ('check_in', '!=', False),
        ])
        
        synced_count = unsynced.sync_to_hr_attendance()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronisation terminée'),
                'message': _('%d enregistrements synchronisés vers HR Attendance.') % synced_count,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sync_to_hr(self):
        """Button action to sync selected records to hr.attendance."""
        synced_count = self.sync_to_hr_attendance()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronisation terminée'),
                'message': _('%d enregistrements synchronisés.') % synced_count,
                'type': 'success',
                'sticky': False,
            }
        }
    
    @api.model
    def create(self, vals):
        """Override create to auto-sync to hr.attendance if enabled."""
        record = super().create(vals)
        
        # Auto-sync if enabled in config
        config = self.env['biotime.config'].get_config()
        if config.sync_to_hr_attendance and record.check_in:
            try:
                record.sync_to_hr_attendance()
            except Exception as e:
                _logger.warning("Auto-sync to hr.attendance failed: %s", str(e))
        
        return record
    
    def write(self, vals):
        """Override write to update hr.attendance if linked."""
        result = super().write(vals)
        
        # Update linked hr.attendance records
        if 'check_in' in vals or 'check_out' in vals:
            config = self.env['biotime.config'].get_config()
            if config.sync_to_hr_attendance:
                for record in self:
                    if record.hr_attendance_id:
                        try:
                            update_vals = {}
                            if 'check_in' in vals:
                                update_vals['check_in'] = record.check_in
                            if 'check_out' in vals:
                                update_vals['check_out'] = record.check_out
                            if update_vals:
                                record.hr_attendance_id.sudo().write(update_vals)
                        except Exception as e:
                            _logger.warning("Failed to update hr.attendance: %s", str(e))
        
        return result
