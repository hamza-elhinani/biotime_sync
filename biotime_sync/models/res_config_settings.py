# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Biotime Configuration Reference
    biotime_config_id = fields.Many2one(
        'biotime.config',
        string='Biotime Configuration',
        config_parameter='biotime_sync.config_id',
        default=lambda self: self.env['biotime.config'].get_config(),
    )
    
    # API Settings (related to biotime.config)
    biotime_api_url = fields.Char(
        related='biotime_config_id.api_url',
        readonly=False,
        string='API URL',
    )
    biotime_api_port = fields.Integer(
        related='biotime_config_id.api_port',
        readonly=False,
        string='API Port',
    )
    biotime_auth_method = fields.Selection(
        related='biotime_config_id.auth_method',
        readonly=False,
        string='Authentication Method',
    )
    biotime_api_token = fields.Char(
        related='biotime_config_id.api_token',
        readonly=False,
        string='API Token',
    )
    biotime_username = fields.Char(
        related='biotime_config_id.username',
        readonly=False,
        string='Username',
    )
    biotime_password = fields.Char(
        related='biotime_config_id.password',
        readonly=False,
        string='Password',
    )
    biotime_timeout = fields.Integer(
        related='biotime_config_id.timeout',
        readonly=False,
        string='Request Timeout',
    )
    biotime_timezone = fields.Selection(
        related='biotime_config_id.timezone',
        readonly=False,
        string='Timezone',
    )
    
    # Business Rules
    biotime_work_start_time = fields.Float(
        related='biotime_config_id.work_start_time',
        readonly=False,
        string='Work Start Time',
    )
    biotime_work_end_time = fields.Float(
        related='biotime_config_id.work_end_time',
        readonly=False,
        string='Work End Time',
    )
    biotime_break_duration = fields.Integer(
        related='biotime_config_id.break_duration',
        readonly=False,
        string='Break Duration (minutes)',
    )
    biotime_late_tolerance = fields.Integer(
        related='biotime_config_id.late_tolerance',
        readonly=False,
        string='Late Tolerance (minutes)',
    )
    biotime_overtime_threshold = fields.Float(
        related='biotime_config_id.overtime_threshold',
        readonly=False,
        string='Overtime Threshold (hours)',
    )
    
    # Sync Settings
    biotime_auto_sync_enabled = fields.Boolean(
        related='biotime_config_id.auto_sync_enabled',
        readonly=False,
        string='Enable Auto Sync',
    )
    biotime_sync_interval = fields.Integer(
        related='biotime_config_id.sync_interval',
        readonly=False,
        string='Sync Interval (hours)',
    )
    biotime_sync_days_back = fields.Integer(
        related='biotime_config_id.sync_days_back',
        readonly=False,
        string='Sync Days Back',
    )
    biotime_create_missing_employees = fields.Boolean(
        related='biotime_config_id.create_missing_employees',
        readonly=False,
        string='Create Missing Employees',
    )
    biotime_sync_to_hr_attendance = fields.Boolean(
        related='biotime_config_id.sync_to_hr_attendance',
        readonly=False,
        string='Sync to HR Attendance',
    )
    
    # Last Sync Info (readonly)
    biotime_last_sync_date = fields.Datetime(
        related='biotime_config_id.last_sync_date',
        string='Last Sync Date',
    )
    biotime_last_sync_status = fields.Selection(
        related='biotime_config_id.last_sync_status',
        string='Last Sync Status',
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        config = self.env['biotime.config'].get_config()
        res['biotime_config_id'] = config.id
        return res

    def set_values(self):
        super().set_values()
        # Values are automatically saved via related fields

    def action_biotime_test_connection(self):
        """Test Biotime API connection from settings."""
        config = self.env['biotime.config'].get_config()
        return config.test_connection()

    def action_biotime_sync_employees(self):
        """Sync employees from settings."""
        config = self.env['biotime.config'].get_config()
        return config.action_sync_employees()

    def action_biotime_sync_attendance(self):
        """Open sync wizard from settings."""
        config = self.env['biotime.config'].get_config()
        return config.action_sync_now()

    def action_biotime_view_logs(self):
        """View sync logs from settings."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sync Logs',
            'res_model': 'biotime.sync.log',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_biotime_open_config(self):
        """Open full configuration form."""
        config = self.env['biotime.config'].get_config()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Biotime Configuration',
            'res_model': 'biotime.config',
            'res_id': config.id,
            'view_mode': 'form',
            'target': 'current',
        }
