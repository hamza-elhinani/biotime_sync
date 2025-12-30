# -*- coding: utf-8 -*-
{
    'name': 'odoo ZKTeco Biotime Sync',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendance',
    'summary': 'Synchronize attendance data from Biotime (ZKTeco) biometric systems',
    'description': """
Biotime Sync
============
This module integrates Odoo with ZKTeco Biotime biometric attendance systems.

Features:
- API integration with Biotime server
- Employee synchronization and mapping
- Attendance transaction synchronization
- Automatic scheduled synchronization
- Worked hours calculation with break deduction
- Late detection and overtime calculation
- Dashboard with attendance statistics
- Role-based access control 
    """,
    'author': 'Hunter BI',
    'company': 'Hunter BI',
    'website': 'https://hunterbi.com',
    'license': 'OPL-1',
    'depends': [
        'hr',
        'hr_attendance',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/biotime_cron.xml',
        'wizard/biotime_sync_wizard_views.xml',
        'views/biotime_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/biotime_attendance_views.xml',
        'views/biotime_sync_log_views.xml',
        'views/hr_employee_views.xml',
        'views/biotime_dashboard_views.xml',
        'views/biotime_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'biotime_sync/static/src/css/dashboard.css',
            'biotime_sync/static/src/js/dashboard.js',
            'biotime_sync/static/src/xml/dashboard.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'price': 449,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False,
}
