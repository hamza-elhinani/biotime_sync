# -*- coding: utf-8 -*-
import logging
import requests
import time
from datetime import datetime, timedelta
from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BiotimeAPIClient:
    """API Client for Biotime communication."""
    
    def __init__(self, config):
        """Initialize API client with configuration.
        
        Args:
            config: biotime.config record with API settings
        """
        self.config = config
        self.base_url = f"{config.api_url}:{config.api_port}" if config.api_port else config.api_url
        self.token = None
        self.session = requests.Session()
    
    def authenticate(self):
        """Authenticate with Biotime API based on configured auth method.
        
        Returns:
            str: Authentication token or session identifier
            
        Raises:
            UserError: If authentication fails
        """
        auth_method = self.config.auth_method
        
        if auth_method == 'token':
            # Token auth - use pre-configured API token
            self.token = self.config.api_token
            return self.token
            
        elif auth_method == 'jwt':
            # JWT auth - authenticate with username/password to get token
            url = f"{self.base_url}/jwt-api-token-auth/"
            payload = {
                'username': self.config.username,
                'password': self.config.password
            }
            _logger.info("JWT auth attempt to: %s with user: %s", url, self.config.username)
            try:
                response = self.session.post(url, json=payload, timeout=30)
                _logger.info("JWT auth response status: %s", response.status_code)
                if response.status_code != 200:
                    _logger.error("JWT auth failed: %s - %s", response.status_code, response.text)
                response.raise_for_status()
                data = response.json()
                self.token = data.get('token')
                _logger.info("JWT token obtained successfully")
                return self.token
            except requests.exceptions.RequestException as e:
                _logger.error("JWT authentication exception: %s", str(e))
                raise UserError(_("JWT authentication failed: %s") % str(e))
                
        elif auth_method == 'basic':
            # Basic auth - set session auth
            self.session.auth = (self.config.username, self.config.password)
            return 'basic_auth_configured'
        
        raise UserError(_("Unknown authentication method: %s") % auth_method)
    
    def _get_headers(self):
        """Get request headers with authentication.
        
        Returns:
            dict: Headers dictionary with authorization
        """
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.config.auth_method == 'token':
            headers['Authorization'] = f"Token {self.token}"
        elif self.config.auth_method == 'jwt':
            headers['Authorization'] = f"JWT {self.token}"
        # Basic auth is handled by session.auth
        
        return headers

    
    def _fetch_paginated(self, endpoint, params=None):
        """Fetch all pages from a paginated API endpoint.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters dictionary
            
        Returns:
            list: All records from all pages combined
        """
        if params is None:
            params = {}
        
        all_records = []
        url = f"{self.base_url}{endpoint}"
        
        while url:
            try:
                response = self.session.get(
                    url,
                    headers=self._get_headers(),
                    params=params if url == f"{self.base_url}{endpoint}" else None,
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                
                # Handle paginated response
                if isinstance(data, dict):
                    results = data.get('data', data.get('results', []))
                    all_records.extend(results)
                    url = data.get('next')  # Next page URL
                else:
                    # Non-paginated response
                    all_records.extend(data)
                    url = None
                    
            except requests.exceptions.RequestException as e:
                _logger.error("API request failed: %s", str(e))
                raise UserError(_("API request failed: %s") % str(e))
        
        return all_records
    
    def fetch_employees(self):
        """Fetch all employees from Biotime API.
        
        Returns:
            list: List of employee dictionaries
        """
        return self._fetch_paginated('/personnel/api/employees/')
    
    def fetch_transactions(self, start_time, end_time):
        """Fetch attendance transactions for a date range.
        
        Args:
            start_time: Start datetime
            end_time: End datetime
            
        Returns:
            list: List of transaction dictionaries
        """
        params = {
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        return self._fetch_paginated('/iclock/api/transactions/', params)


class BiotimeConfig(models.Model):
    _name = 'biotime.config'
    _description = 'Biotime Configuration'
    _rec_name = 'name'
    
    # General Settings
    name = fields.Char(
        string='Configuration Name',
        required=True,
        default='Main Configuration',
        help='Name to identify this configuration'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, this configuration will be hidden'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Company this configuration belongs to'
    )
    
    # API Settings
    api_url = fields.Char(
        string='API URL',
        required=True,
        default='https://biotime.example.com',
        help='Base URL of the Biotime server (e.g., https://biotime.example.com)'
    )
    api_port = fields.Integer(
        string='API Port',
        default=443,
        help='Port number for API connection'
    )
    auth_method = fields.Selection([
        ('token', 'Token Authentication'),
        ('jwt', 'JWT Authentication'),
        ('basic', 'Basic Authentication')
    ], string='Authentication Method', required=True, default='token',
       help='Method used to authenticate with Biotime API')
    username = fields.Char(
        string='Username',
        help='Username for JWT or Basic authentication'
    )
    password = fields.Char(
        string='Password',
        help='Password for JWT or Basic authentication'
    )
    api_token = fields.Char(
        string='API Token',
        help='API token for Token authentication'
    )
    timeout = fields.Integer(
        string='Request Timeout (seconds)',
        default=30,
        help='Timeout for API requests in seconds'
    )
    
    # Timezone Settings
    timezone = fields.Selection(
        selection='_get_timezone_selection',
        string='Timezone',
        default='UTC',
        help='Timezone used for attendance time conversion'
    )
    
    # Business Rules
    work_start_time = fields.Float(
        string='Work Start Time',
        default=9.0,
        help='Expected work start time in hours (e.g., 9.0 for 9:00 AM)'
    )
    work_end_time = fields.Float(
        string='Work End Time',
        default=18.0,
        help='Expected work end time in hours (e.g., 18.0 for 6:00 PM)'
    )
    break_duration = fields.Integer(
        string='Break Duration (minutes)',
        default=60,
        help='Break duration in minutes to deduct from worked hours'
    )
    late_tolerance = fields.Integer(
        string='Late Tolerance (minutes)',
        default=15,
        help='Grace period in minutes before marking as late'
    )
    overtime_threshold = fields.Float(
        string='Overtime Threshold (hours)',
        default=8.0,
        help='Daily hours threshold after which additional hours count as overtime'
    )
    
    # Sync Settings
    auto_sync_enabled = fields.Boolean(
        string='Enable Auto Sync',
        default=True,
        help='Enable automatic synchronization via scheduled action'
    )
    sync_interval = fields.Integer(
        string='Sync Interval (hours)',
        default=1,
        help='Interval between automatic synchronizations'
    )
    sync_days_back = fields.Integer(
        string='Sync Days Back',
        default=1,
        help='Number of days to look back when syncing attendance'
    )
    create_missing_employees = fields.Boolean(
        string='Create Missing Employees',
        default=False,
        help='Automatically create employees in Odoo that exist in Biotime but not in Odoo'
    )
    sync_to_hr_attendance = fields.Boolean(
        string='Sync to HR Attendance',
        default=True,
        help='Automatically sync biotime attendance to Odoo HR Attendance module'
    )
    
    # Last Sync Info (readonly)
    last_sync_date = fields.Datetime(
        string='Last Sync Date',
        readonly=True,
        help='Date and time of the last successful synchronization'
    )
    last_sync_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('partial', 'Partial'),
    ], string='Last Sync Status', readonly=True)
    last_sync_message = fields.Text(
        string='Last Sync Message',
        readonly=True,
        help='Details about the last synchronization'
    )
    
    @api.model
    def _get_timezone_selection(self):
        """Return list of timezones for selection field."""
        import pytz
        return [(tz, tz) for tz in pytz.common_timezones]
    
    @api.model
    def get_config(self):
        """Get the singleton configuration record.
        
        Creates a default configuration if none exists.
        
        Returns:
            biotime.config: The configuration record
        """
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({
                'name': 'Main Configuration',
                'api_url': 'https://biotime.example.com',
                'api_port': 443,
                'auth_method': 'token'
            })
        return config
    
    def _update_last_sync_info(self, status, message=None):
        """Update last sync information fields.
        
        Args:
            status: Sync status ('success', 'error', 'partial')
            message: Optional message with sync details
        """
        self.ensure_one()
        self.write({
            'last_sync_date': fields.Datetime.now(),
            'last_sync_status': status,
            'last_sync_message': message or '',
        })
    
    def get_api_client(self):
        """Get an authenticated API client instance.
        
        Returns:
            BiotimeAPIClient: Authenticated API client
        """
        self.ensure_one()
        client = BiotimeAPIClient(self)
        client.authenticate()
        return client
    
    def test_connection(self):
        """Test the API connection with current settings.
        
        Returns:
            dict: Action to display notification
        """
        self.ensure_one()
        try:
            client = BiotimeAPIClient(self)
            client.authenticate()
            
            # Try to fetch a small amount of data to verify connection
            # We'll just verify authentication worked
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Successfully connected to Biotime API.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except UserError as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Failed'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        except Exception as e:
            _logger.exception("Connection test failed")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Failed'),
                    'message': _('An unexpected error occurred: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_sync_now(self):
        """Open the sync wizard for manual synchronization.
        
        Returns:
            dict: Action to open sync wizard
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sync Now'),
            'res_model': 'biotime.sync.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sync_type': 'full'}
        }

    def sync_employees(self, create_missing=False):
        """Synchronize employees from Biotime to Odoo.
        
        Matching algorithm:
        1. First match by biotime_id field
        2. If no match, try matching by barcode field
        3. If create_missing=True, create new employee in Odoo
        
        Updates matched employees' biotime_id field.
        Logs unmatched employees for manual review.
        Creates sync log record on completion.
        
        Args:
            create_missing: If True, create employees that don't exist in Odoo
        
        Returns:
            dict: Sync results with counts
        """
        self.ensure_one()
        start_time = time.time()
        
        records_created = 0
        records_updated = 0
        records_skipped = 0
        unmatched_employees = []
        error_message = None
        status = 'success'
        
        try:
            # Get API client and fetch employees
            client = self.get_api_client()
            biotime_employees = client.fetch_employees()
            
            Employee = self.env['hr.employee']
            
            for bt_emp in biotime_employees:
                # Extract employee data from Biotime response
                bt_id = str(bt_emp.get('id', '')) or str(bt_emp.get('emp_code', ''))
                bt_code = str(bt_emp.get('emp_code', ''))
                first_name = bt_emp.get('first_name', '') or ''
                last_name = bt_emp.get('last_name', '') or ''
                bt_name = f"{first_name} {last_name}".strip() or f"Employee {bt_id}"
                
                if not bt_id:
                    records_skipped += 1
                    continue
                
                # Step 1: Try to match by biotime_id first
                employee = Employee.search([('biotime_id', '=', bt_id)], limit=1)
                
                # Step 2: If no match, try matching by barcode
                if not employee and bt_code:
                    employee = Employee.search([('barcode', '=', bt_code)], limit=1)
                
                # Step 3: Try matching by name (case insensitive)
                if not employee and bt_name:
                    employee = Employee.search([('name', '=ilike', bt_name)], limit=1)
                
                if employee:
                    # Update the biotime_id field if not already set
                    if employee.biotime_id != bt_id:
                        employee.write({'biotime_id': bt_id})
                        records_updated += 1
                else:
                    # No matching employee found
                    if create_missing:
                        # Create new employee in Odoo
                        try:
                            new_employee = Employee.create({
                                'name': bt_name,
                                'biotime_id': bt_id,
                                'barcode': bt_code if bt_code else None,
                            })
                            records_created += 1
                            _logger.info("Created employee: %s (Biotime ID: %s)", bt_name, bt_id)
                        except Exception as e:
                            _logger.error("Failed to create employee %s: %s", bt_name, str(e))
                            records_skipped += 1
                            unmatched_employees.append({
                                'biotime_id': bt_id,
                                'emp_code': bt_code,
                                'name': bt_name,
                                'error': str(e)
                            })
                    else:
                        # Log for manual review
                        unmatched_employees.append({
                            'biotime_id': bt_id,
                            'emp_code': bt_code,
                            'name': bt_name
                        })
                        records_skipped += 1
            
            # Log unmatched employees
            if unmatched_employees and not create_missing:
                _logger.warning(
                    "Unmatched Biotime employees: %s",
                    ', '.join([f"{e['name']} ({e['biotime_id']})" for e in unmatched_employees])
                )
            
            if records_created > 0 or records_updated > 0:
                status = 'success'
            elif unmatched_employees:
                status = 'partial'
                error_message = f"{len(unmatched_employees)} unmatched employees."
                    
        except UserError as e:
            status = 'error'
            error_message = str(e)
            _logger.error("Employee sync failed: %s", error_message)
        except Exception as e:
            status = 'error'
            error_message = f"Unexpected error: {str(e)}"
            _logger.exception("Employee sync failed with unexpected error")
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Create sync log record
        self.env['biotime.sync.log'].create({
            'sync_date': fields.Datetime.now(),
            'sync_type': 'employees',
            'records_created': records_created,
            'records_updated': records_updated,
            'records_skipped': records_skipped,
            'status': status,
            'duration': duration,
            'error_message': error_message,
            'user_id': self.env.user.id,
        })
        
        return {
            'records_created': records_created,
            'records_updated': records_updated,
            'records_skipped': records_skipped,
            'unmatched': unmatched_employees,
            'status': status,
            'error_message': error_message,
        }

    def sync_attendance(self, date_from, date_to):
        """Synchronize attendance transactions from Biotime for a date range.
        
        Fetches transactions using API client with pagination.
        Pairs transactions chronologically as check-in/check-out for same employee/day.
        Creates/updates biotime.attendance records.
        Skips unmapped employees with warning log.
        Creates sync log record on completion.
        
        Args:
            date_from: Start date for sync
            date_to: End date for sync
            
        Returns:
            dict: Sync results with counts
        """
        self.ensure_one()
        start_time = time.time()
        
        records_created = 0
        records_updated = 0
        records_skipped = 0
        unmapped_employees = set()
        error_message = None
        status = 'success'
        
        try:
            # Get API client and fetch transactions
            client = self.get_api_client()
            
            # Convert dates to datetime for API
            start_datetime = datetime.combine(date_from, datetime.min.time())
            end_datetime = datetime.combine(date_to, datetime.max.time())
            
            transactions = client.fetch_transactions(start_datetime, end_datetime)
            
            Employee = self.env['hr.employee']
            Attendance = self.env['biotime.attendance']
            
            # Group transactions by employee and date
            # Structure: {(employee_id, date): [transactions]}
            grouped_transactions = defaultdict(list)
            
            for trans in transactions:
                emp_code = str(trans.get('emp_code', ''))
                punch_time_str = trans.get('punch_time', '')
                
                if not emp_code or not punch_time_str:
                    records_skipped += 1
                    continue
                
                # Find employee by biotime_id or barcode
                employee = Employee.search([('biotime_id', '=', emp_code)], limit=1)
                if not employee:
                    employee = Employee.search([('barcode', '=', emp_code)], limit=1)
                
                if not employee:
                    # Unmapped employee - skip and log
                    unmapped_employees.add(emp_code)
                    records_skipped += 1
                    continue
                
                # Parse punch time
                try:
                    punch_time = datetime.strptime(punch_time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        punch_time = datetime.strptime(punch_time_str, '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        _logger.warning("Invalid punch time format: %s", punch_time_str)
                        records_skipped += 1
                        continue
                
                punch_date = punch_time.date()
                trans_id = str(trans.get('id', ''))
                
                grouped_transactions[(employee.id, punch_date)].append({
                    'punch_time': punch_time,
                    'transaction_id': trans_id,
                    'employee_id': employee.id,
                })
            
            # Process grouped transactions - pair as check-in/check-out
            for (employee_id, punch_date), trans_list in grouped_transactions.items():
                # Sort transactions chronologically
                trans_list.sort(key=lambda x: x['punch_time'])
                
                # Pair transactions: first is check-in, second is check-out
                check_in = trans_list[0]['punch_time'] if trans_list else None
                check_out = trans_list[1]['punch_time'] if len(trans_list) > 1 else None
                
                # Combine transaction IDs
                transaction_ids = ','.join([t['transaction_id'] for t in trans_list if t['transaction_id']])
                
                # Check if attendance record already exists
                existing = Attendance.search([
                    ('employee_id', '=', employee_id),
                    ('date', '=', punch_date),
                ], limit=1)
                
                if existing:
                    # Update existing record
                    vals = {}
                    if check_in and existing.check_in != check_in:
                        vals['check_in'] = check_in
                    if check_out and existing.check_out != check_out:
                        vals['check_out'] = check_out
                    if transaction_ids:
                        vals['biotime_transaction_id'] = transaction_ids
                    
                    if vals:
                        existing.write(vals)
                        records_updated += 1
                        # Sync to hr.attendance if enabled
                        if self.sync_to_hr_attendance:
                            existing.sync_to_hr_attendance()
                else:
                    # Create new attendance record
                    new_attendance = Attendance.create({
                        'employee_id': employee_id,
                        'date': punch_date,
                        'check_in': check_in,
                        'check_out': check_out,
                        'biotime_transaction_id': transaction_ids,
                    })
                    records_created += 1
                    # Sync to hr.attendance if enabled
                    if self.sync_to_hr_attendance:
                        new_attendance.sync_to_hr_attendance()
            
            # Log unmapped employees
            if unmapped_employees:
                _logger.warning(
                    "Unmapped employees in transactions: %s",
                    ', '.join(unmapped_employees)
                )
                
        except UserError as e:
            status = 'error'
            error_message = str(e)
            _logger.error("Attendance sync failed: %s", error_message)
        except Exception as e:
            status = 'error'
            error_message = f"Unexpected error: {str(e)}"
            _logger.exception("Attendance sync failed with unexpected error")
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Create sync log record
        self.env['biotime.sync.log'].create({
            'sync_date': fields.Datetime.now(),
            'sync_type': 'attendance',
            'records_created': records_created,
            'records_updated': records_updated,
            'records_skipped': records_skipped,
            'status': status,
            'duration': duration,
            'error_message': error_message,
            'user_id': self.env.user.id,
        })
        
        return {
            'records_created': records_created,
            'records_updated': records_updated,
            'records_skipped': records_skipped,
            'unmapped_employees': list(unmapped_employees),
            'status': status,
            'error_message': error_message,
        }

    def action_view_sync_logs(self):
        """Open sync logs filtered for this configuration.
        
        Returns:
            dict: Action to open sync logs
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sync Logs'),
            'res_model': 'biotime.sync.log',
            'view_mode': 'list,form',
            'domain': [],
            'context': {'default_user_id': self.env.user.id},
        }

    def action_sync_employees(self):
        """Trigger employee synchronization.
        
        Returns:
            dict: Action to display notification with results
        """
        self.ensure_one()
        result = self.sync_employees(create_missing=self.create_missing_employees)
        
        # Update last sync info
        message = f"Created: {result['records_created']}, Updated: {result['records_updated']}, Skipped: {result['records_skipped']}"
        self._update_last_sync_info(result['status'], message)
        
        if result['status'] == 'success':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Employee Sync Completed'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        elif result['status'] == 'partial':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Employee Sync Partial'),
                    'message': message,
                    'type': 'warning',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Employee Sync Failed'),
                    'message': result.get('error_message', 'Unknown error'),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    @api.model
    def cron_sync_attendance(self):
        """Cron job method to sync attendance based on configuration.
        
        Called by the scheduled action to automatically sync
        attendance records. Uses sync_days_back from configuration.
        
        Returns:
            bool: True if sync completed (regardless of result)
        """
        config = self.get_config()
        
        # Check if auto sync is enabled
        if not config.auto_sync_enabled:
            _logger.info("Auto sync is disabled, skipping scheduled sync")
            return True
        
        today = fields.Date.today()
        days_back = config.sync_days_back or 1
        date_from = today - timedelta(days=days_back - 1)
        
        _logger.info("Starting scheduled attendance sync from %s to %s", date_from, today)
        
        try:
            result = config.sync_attendance(date_from, today)
            
            # Update last sync info
            message = f"Created: {result.get('records_created', 0)}, Updated: {result.get('records_updated', 0)}, Skipped: {result.get('records_skipped', 0)}"
            config._update_last_sync_info(result.get('status', 'success'), message)
            
            _logger.info(
                "Scheduled sync completed: %d created, %d updated, %d skipped",
                result.get('records_created', 0),
                result.get('records_updated', 0),
                result.get('records_skipped', 0)
            )
        except Exception as e:
            config._update_last_sync_info('error', str(e))
            _logger.exception("Scheduled attendance sync failed: %s", str(e))
        
        return True
