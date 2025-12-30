# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from collections import defaultdict
from odoo import http, fields
from odoo.http import request


class BiotimeDashboardController(http.Controller):
    """HTTP controller providing dashboard data via JSON endpoints."""

    @http.route('/biotime/dashboard/stats', type='json', auth='user')
    def get_stats(self, department_id=None, date_from=None, date_to=None):
        """Get today's attendance statistics.
        
        Args:
            department_id: Optional department filter
            date_from: Optional start date (YYYY-MM-DD)
            date_to: Optional end date (YYYY-MM-DD)
            
        Returns:
            dict: Statistics including total_employees, present_count, 
                  absent_count, late_count, total_worked_hours
        """
        Attendance = request.env['biotime.attendance']
        Employee = request.env['hr.employee']
        
        # Parse dates or use today
        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        else:
            date_from = fields.Date.today()
        
        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        else:
            date_to = date_from
        
        # Build employee domain
        employee_domain = []
        if department_id:
            employee_domain.append(('department_id', '=', int(department_id)))
        
        # Get total employees count
        total_employees = Employee.search_count(employee_domain)
        
        # Build attendance domain
        attendance_domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        
        if department_id:
            attendance_domain.append(('employee_id.department_id', '=', int(department_id)))
        
        # Get attendance records
        attendances = Attendance.search(attendance_domain)
        
        # Calculate statistics
        present_count = len(attendances.filtered(lambda a: a.status == 'present'))
        late_count = len(attendances.filtered(lambda a: a.status == 'late'))
        absent_count = total_employees - len(attendances)
        if absent_count < 0:
            absent_count = 0
        
        total_worked_hours = sum(attendances.mapped('worked_hours'))
        
        return {
            'total_employees': total_employees,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'total_worked_hours': round(total_worked_hours, 2),
        }

    @http.route('/biotime/dashboard/trend', type='json', auth='user')
    def get_trend(self, department_id=None, days=30):
        """Get presence trend data for the last N days.
        
        Args:
            department_id: Optional department filter
            days: Number of days to include (default 30)
            
        Returns:
            list: List of dicts with date, present_count, late_count, absent_count
        """
        Attendance = request.env['biotime.attendance']
        Employee = request.env['hr.employee']
        
        days = int(days)
        today = fields.Date.today()
        start_date = today - timedelta(days=days - 1)
        
        # Get total employees for absent calculation
        employee_domain = []
        if department_id:
            employee_domain.append(('department_id', '=', int(department_id)))
        total_employees = Employee.search_count(employee_domain)
        
        # Build attendance domain
        attendance_domain = [
            ('date', '>=', start_date),
            ('date', '<=', today),
        ]
        if department_id:
            attendance_domain.append(('employee_id.department_id', '=', int(department_id)))
        
        attendances = Attendance.search(attendance_domain)
        
        # Group by date
        date_data = defaultdict(lambda: {'present': 0, 'late': 0, 'total': 0})
        for att in attendances:
            date_str = str(att.date)
            date_data[date_str]['total'] += 1
            if att.status == 'present':
                date_data[date_str]['present'] += 1
            elif att.status == 'late':
                date_data[date_str]['late'] += 1
        
        # Build result for all days in range
        result = []
        current_date = start_date
        while current_date <= today:
            date_str = str(current_date)
            data = date_data.get(date_str, {'present': 0, 'late': 0, 'total': 0})
            result.append({
                'date': date_str,
                'present_count': data['present'],
                'late_count': data['late'],
                'absent_count': max(0, total_employees - data['total']),
            })
            current_date += timedelta(days=1)
        
        return result


    @http.route('/biotime/dashboard/department_hours', type='json', auth='user')
    def get_department_hours(self, date_from=None, date_to=None):
        """Get worked hours aggregated by department.
        
        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            
        Returns:
            list: List of dicts with department_id, department_name, total_hours
        """
        Attendance = request.env['biotime.attendance']
        
        # Parse dates or use today
        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        else:
            date_from = fields.Date.today()
        
        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        else:
            date_to = date_from
        
        # Build domain
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        
        attendances = Attendance.search(domain)
        
        # Aggregate hours by department
        dept_hours = defaultdict(lambda: {'name': '', 'hours': 0.0})
        for att in attendances:
            dept = att.employee_id.department_id
            if dept:
                dept_hours[dept.id]['name'] = dept.name
                dept_hours[dept.id]['hours'] += att.worked_hours
            else:
                # Handle employees without department
                dept_hours[0]['name'] = 'No Department'
                dept_hours[0]['hours'] += att.worked_hours
        
        # Build result
        result = []
        for dept_id, data in dept_hours.items():
            result.append({
                'department_id': dept_id if dept_id else None,
                'department_name': data['name'],
                'total_hours': round(data['hours'], 2),
            })
        
        # Sort by total hours descending
        result.sort(key=lambda x: x['total_hours'], reverse=True)
        
        return result

    @http.route('/biotime/dashboard/status_distribution', type='json', auth='user')
    def get_status_distribution(self, department_id=None, date=None):
        """Get attendance status distribution for a date.
        
        Args:
            department_id: Optional department filter
            date: Date to get distribution for (YYYY-MM-DD), defaults to today
            
        Returns:
            dict: Status counts {present: N, late: N, absent: N, ...}
        """
        Attendance = request.env['biotime.attendance']
        Employee = request.env['hr.employee']
        
        # Parse date or use today
        if date:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            target_date = fields.Date.today()
        
        # Build domain
        domain = [('date', '=', target_date)]
        if department_id:
            domain.append(('employee_id.department_id', '=', int(department_id)))
        
        attendances = Attendance.search(domain)
        
        # Get total employees for absent calculation
        employee_domain = []
        if department_id:
            employee_domain.append(('department_id', '=', int(department_id)))
        total_employees = Employee.search_count(employee_domain)
        
        # Count by status
        status_counts = {
            'present': 0,
            'absent': 0,
            'late': 0,
            'leave': 0,
            'half_day': 0,
            'incomplete': 0,
        }
        
        for att in attendances:
            if att.status in status_counts:
                status_counts[att.status] += 1
        
        # Calculate absent as employees without attendance record
        employees_with_attendance = len(attendances)
        status_counts['absent'] = max(0, total_employees - employees_with_attendance)
        
        return status_counts

    @http.route('/biotime/dashboard/top_late', type='json', auth='user')
    def get_top_late(self, limit=10, department_id=None):
        """Get top late employees ranked by weekly late frequency.
        
        Args:
            limit: Maximum number of employees to return (default 10)
            department_id: Optional department filter
            
        Returns:
            list: List of dicts with employee_id, employee_name, late_count, 
                  total_late_minutes
        """
        Attendance = request.env['biotime.attendance']
        
        limit = int(limit)
        
        # Calculate date range for last 7 days
        today = fields.Date.today()
        week_start = today - timedelta(days=6)
        
        # Build domain
        domain = [
            ('date', '>=', week_start),
            ('date', '<=', today),
            ('is_late', '=', True),
        ]
        if department_id:
            domain.append(('employee_id.department_id', '=', int(department_id)))
        
        late_attendances = Attendance.search(domain)
        
        # Aggregate by employee
        employee_late = defaultdict(lambda: {
            'name': '',
            'late_count': 0,
            'total_late_minutes': 0
        })
        
        for att in late_attendances:
            emp_id = att.employee_id.id
            employee_late[emp_id]['name'] = att.employee_id.name
            employee_late[emp_id]['late_count'] += 1
            employee_late[emp_id]['total_late_minutes'] += att.late_minutes
        
        # Build and sort result
        result = []
        for emp_id, data in employee_late.items():
            result.append({
                'employee_id': emp_id,
                'employee_name': data['name'],
                'late_count': data['late_count'],
                'total_late_minutes': data['total_late_minutes'],
            })
        
        # Sort by late_count descending
        result.sort(key=lambda x: x['late_count'], reverse=True)
        
        # Limit results
        return result[:limit]
