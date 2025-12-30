# Implementation Plan: Biotime Sync

## Overview

This implementation plan breaks down the Biotime Sync Odoo 19 module into discrete coding tasks. Each task builds incrementally on previous work, ensuring no orphaned code. The module will be implemented using Python for Odoo models/controllers and XML for views/security.

## Tasks

- [x] 1. Set up module structure and manifest
  - Create `biotime_sync/__init__.py` with model imports
  - Create `biotime_sync/__manifest__.py` with module metadata, dependencies (hr, hr_attendance), and data file references
  - Create directory structure: models/, views/, security/, data/, controllers/, wizard/, static/src/
  - _Requirements: Module structure_

- [x] 2. Implement Configuration Model
  - [x] 2.1 Create biotime.config model with API and business rule fields
    - Create `models/biotime_config.py` with fields: api_url, api_port, auth_method (selection), username, password, api_token, work_start_time, work_end_time, break_duration, late_tolerance, overtime_threshold
    - Implement `get_config()` singleton pattern method
    - _Requirements: 1.1, 7.3_
  
  - [x] 2.2 Implement API Client class
    - Create `BiotimeAPIClient` class within biotime_config.py
    - Implement `authenticate()` method supporting Token, JWT, and Basic auth
    - Implement `_get_headers()` for request authentication
    - Implement `fetch_employees()` calling `/personnel/api/employees/`
    - Implement `fetch_transactions(start_time, end_time)` calling `/iclock/api/transactions/`
    - Implement `_fetch_paginated()` for handling paginated responses
    - _Requirements: 2.1, 3.1, 3.2_
  
  - [x] 2.3 Implement test_connection action
    - Add `test_connection()` method that attempts authentication and returns success/failure notification
    - _Requirements: 1.4, 1.5_

- [x] 3. Implement Employee Extension
  - [x] 3.1 Create hr.employee extension
    - Create `models/hr_employee.py` extending hr.employee with biotime_id and biotime_badge fields
    - _Requirements: 2.5_
  
  - [x] 3.2 Create employee view extension
    - Create `views/hr_employee_views.xml` adding Biotime tab to employee form with biotime_id and biotime_badge fields
    - _Requirements: 2.5_

- [x] 4. Implement Attendance Model
  - [x] 4.1 Create biotime.attendance model with core fields
    - Create `models/biotime_attendance.py` with fields: employee_id, date, check_in, check_out, biotime_transaction_id
    - Add status selection field with values: present, absent, late, leave, half_day, incomplete
    - _Requirements: 8.1_
  
  - [x] 4.2 Implement worked_hours computation
    - Add computed field `worked_hours` with `_compute_worked_hours()` method
    - Calculate as (check_out - check_in) - break_duration, return 0 if check_out missing
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 4.3 Write property test for worked_hours calculation
    - **Property 4: Worked Hours Calculation**
    - **Validates: Requirements 5.1, 5.2, 5.3**
  
  - [x] 4.4 Implement late detection computation
    - Add computed fields `is_late` and `late_minutes` with `_compute_late_status()` method
    - is_late = check_in > work_start_time + late_tolerance
    - late_minutes = max(0, check_in - work_start_time) in minutes
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [x] 4.5 Write property test for late detection
    - **Property 5: Late Detection**
    - **Validates: Requirements 6.1, 6.2, 6.3**
  
  - [x] 4.6 Implement overtime computation
    - Add computed field `overtime_hours` with `_compute_overtime()` method
    - overtime_hours = max(0, worked_hours - overtime_threshold)
    - _Requirements: 7.1, 7.2_
  
  - [x] 4.7 Write property test for overtime calculation
    - **Property 6: Overtime Calculation**
    - **Validates: Requirements 7.1, 7.2**
  
  - [x] 4.8 Implement status computation
    - Add `_compute_status()` method determining status based on check_in, check_out, is_late, worked_hours
    - Status logic: incomplete (no check_out), late (is_late + complete), half_day (worked < expected/2), present (otherwise)
    - _Requirements: 8.2, 8.3, 8.4, 8.5_
  
  - [x] 4.9 Write property test for status determination
    - **Property 7: Status Determination**
    - **Validates: Requirements 8.2, 8.3, 8.4, 8.5**

- [x] 5. Checkpoint - Core models complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Sync Log Model
  - [x] 6.1 Create biotime.sync.log model
    - Create `models/biotime_sync_log.py` with fields: sync_date, sync_type (selection), records_created, records_updated, records_skipped, status (selection), duration, error_message, user_id
    - _Requirements: 9.1, 9.2_

- [x] 7. Implement Sync Engine
  - [x] 7.1 Implement employee sync logic
    - Add `sync_employees()` method to biotime.config
    - Implement matching algorithm: first by biotime_id, then by barcode
    - Update matched employees' biotime_id field
    - Log unmatched employees
    - Create sync log record on completion
    - _Requirements: 2.2, 2.3, 2.4, 4.4_
  
  - [x] 7.2 Write property test for employee matching priority
    - **Property 1: Employee Matching Priority**
    - **Validates: Requirements 2.2**
  
  - [x] 7.3 Implement attendance sync logic
    - Add `sync_attendance(date_from, date_to)` method to biotime.config
    - Fetch transactions using API client with pagination
    - Pair transactions chronologically as check-in/check-out for same employee/day
    - Create/update biotime.attendance records
    - Skip unmapped employees with warning log
    - Create sync log record on completion
    - _Requirements: 3.3, 3.4, 3.5, 4.4_
  
  - [x] 7.4 Write property test for pagination completeness
    - **Property 2: Pagination Completeness**
    - **Validates: Requirements 3.2**
  
  - [x] 7.5 Write property test for transaction pairing
    - **Property 3: Transaction Chronological Pairing**
    - **Validates: Requirements 3.4**

- [x] 8. Implement Sync Wizard
  - [x] 8.1 Create biotime.sync.wizard transient model
    - Create `wizard/biotime_sync_wizard.py` with fields: sync_type (selection: employees/attendance/full), date_from, date_to
    - Implement `action_sync()` method executing selected sync type
    - Return action displaying sync results
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  
  - [x] 8.2 Create sync wizard view
    - Create `wizard/biotime_sync_wizard_views.xml` with form view and action
    - _Requirements: 12.1, 12.2_

- [x] 9. Checkpoint - Sync functionality complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement Scheduled Sync
  - [x] 10.1 Create cron job for hourly sync
    - Create `data/biotime_cron.xml` with ir.cron record
    - Configure hourly interval calling attendance sync for current day
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 11. Implement Security
  - [x] 11.1 Create security groups
    - Create `security/security_groups.xml` defining biotime_user, biotime_supervisor, biotime_manager groups
    - Set group hierarchy: manager implies supervisor implies user
    - _Requirements: 13.1_
  
  - [x] 11.2 Create access rights
    - Create `security/ir.model.access.csv` with CRUD permissions per group
    - Users: read attendance; Supervisors: read/write attendance; Managers: full access to all models
    - _Requirements: 13.5_
  
  - [x] 11.3 Create record rules
    - Add record rules to security_groups.xml
    - User rule: domain filters to own employee records
    - Supervisor rule: domain filters to same department
    - Manager rule: no domain restriction
    - _Requirements: 13.2, 13.3, 13.4_
  
  - [x] 11.4 Write property test for security-based visibility
    - **Property 12: Security-Based Record Visibility**
    - **Validates: Requirements 13.2, 13.3, 13.4**

- [x] 12. Implement Views
  - [x] 12.1 Create configuration views
    - Create `views/biotime_config_views.xml` with form view for settings
    - Add Test Connection and Sync Now buttons
    - Implement conditional field visibility based on auth_method
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [x] 12.2 Create attendance views
    - Create `views/biotime_attendance_views.xml` with tree, form, and kanban views
    - Tree view: employee, date, check_in, check_out, worked_hours, status, is_late
    - Kanban view: grouped by status
    - Form view: all fields including computed values
    - _Requirements: 14.1, 14.2, 14.3_
  
  - [x] 12.3 Create sync log views
    - Create `views/biotime_sync_log_views.xml` with tree and form views
    - Add search view with date and status filters
    - _Requirements: 9.3_
  
  - [x] 12.4 Create menu structure
    - Create `views/biotime_menu.xml` with main menu and submenus
    - Add Today's Attendance action with domain filtering current date
    - _Requirements: 14.4_

- [x] 13. Implement Dashboard
  - [x] 13.1 Create dashboard controller
    - Create `controllers/dashboard_controller.py` with JSON endpoints
    - Implement `/biotime/dashboard/stats` returning today's statistics
    - Implement `/biotime/dashboard/trend` returning 30-day presence data
    - Implement `/biotime/dashboard/department_hours` returning hours by department
    - Implement `/biotime/dashboard/status_distribution` returning status counts
    - Implement `/biotime/dashboard/top_late` returning ranked late employees
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  
  - [x] 13.2 Write property test for department hours aggregation
    - **Property 8: Dashboard Department Hours Aggregation**
    - **Validates: Requirements 10.3**
  
  - [x] 13.3 Write property test for status distribution
    - **Property 9: Dashboard Status Distribution**
    - **Validates: Requirements 10.4**
  
  - [x] 13.4 Write property test for top late ranking
    - **Property 10: Top Late Employees Ranking**
    - **Validates: Requirements 10.5**
  
  - [x] 13.5 Write property test for filter application
    - **Property 11: Dashboard Filter Application**
    - **Validates: Requirements 11.3**
  
  - [x] 13.6 Create dashboard frontend
    - Create `static/src/js/dashboard.js` with OWL component
    - Create `static/src/css/dashboard.css` for styling
    - Create `static/src/xml/dashboard.xml` with QWeb template
    - Implement charts using Chart.js or Odoo's built-in charting
    - Add department filter and date range selector
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.2, 11.3_
  
  - [x] 13.7 Create dashboard view
    - Create `views/biotime_dashboard_views.xml` with client action
    - Register dashboard in menu
    - _Requirements: 10.1_

- [x] 14. Final checkpoint - All features complete
  - Ensure all tests pass, ask the user if questions arise.
  - Verify module installs without errors
  - Test full sync workflow end-to-end

## Notes

- All tasks including property tests are required
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using hypothesis
- Unit tests validate specific examples and edge cases
- The module follows Odoo 19 conventions and best practices
