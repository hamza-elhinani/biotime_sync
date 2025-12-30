# Requirements Document

## Introduction

Biotime Sync is an Odoo 19 module that synchronizes attendance data from Biotime (ZKTeco) biometric systems with Odoo. The module provides API integration, employee mapping, attendance tracking with business rules, and a dashboard for monitoring attendance statistics.

## Glossary

- **Biotime_System**: The ZKTeco biometric attendance system that captures employee check-in/check-out data
- **Sync_Engine**: The component responsible for fetching and processing data from Biotime API
- **Attendance_Record**: A single check-in or check-out transaction from the biometric system
- **Employee_Mapping**: The association between a Biotime employee ID and an Odoo hr.employee record
- **Work_Schedule**: The configured work start time, end time, and break duration
- **Late_Tolerance**: The grace period (in minutes) before an employee is marked as late
- **Overtime_Threshold**: The daily hours threshold after which additional hours count as overtime
- **Sync_Log**: A record tracking the execution and results of a synchronization operation
- **Dashboard**: The visual interface displaying attendance statistics and charts

## Requirements

### Requirement 1: API Configuration and Connection

**User Story:** As an administrator, I want to configure the Biotime API connection settings, so that the module can communicate with our biometric system.

#### Acceptance Criteria

1. THE Configuration_Form SHALL provide fields for API URL, port, authentication method, username, password, and API token
2. WHEN an administrator selects Token authentication, THE Configuration_Form SHALL display the API token field
3. WHEN an administrator selects JWT or Basic authentication, THE Configuration_Form SHALL display username and password fields
4. WHEN an administrator clicks Test Connection, THE Sync_Engine SHALL attempt to authenticate with the Biotime API and display the result
5. IF the connection test fails, THEN THE Configuration_Form SHALL display a descriptive error message

### Requirement 2: Employee Synchronization

**User Story:** As an administrator, I want to synchronize employees from Biotime to Odoo, so that attendance records can be properly mapped.

#### Acceptance Criteria

1. WHEN an administrator triggers employee sync, THE Sync_Engine SHALL fetch all employees from the Biotime API endpoint `/personnel/api/employees/`
2. WHEN processing a Biotime employee, THE Sync_Engine SHALL match by biotime_id field first, then by barcode field
3. WHEN a matching Odoo employee is found, THE Sync_Engine SHALL update the biotime_id field on the hr.employee record
4. WHEN no matching employee is found, THE Sync_Engine SHALL log the unmatched employee for manual review
5. THE hr.employee model SHALL include a biotime_id field and a Biotime tab in the form view

### Requirement 3: Attendance Synchronization

**User Story:** As an administrator, I want to synchronize attendance transactions from Biotime, so that employee check-in/check-out data is available in Odoo.

#### Acceptance Criteria

1. WHEN an administrator triggers attendance sync with a date range, THE Sync_Engine SHALL fetch transactions from `/iclock/api/transactions/` with the specified start_time and end_time parameters
2. WHEN the API returns paginated results, THE Sync_Engine SHALL iterate through all pages until all records are fetched
3. WHEN processing a transaction, THE Sync_Engine SHALL create or update a biotime.attendance record with employee reference, check-in time, and check-out time
4. WHEN multiple transactions exist for the same employee on the same day, THE Sync_Engine SHALL pair them as check-in and check-out based on chronological order
5. IF a transaction references an unmapped employee, THEN THE Sync_Engine SHALL skip the record and log a warning

### Requirement 4: Automatic Scheduled Synchronization

**User Story:** As an administrator, I want attendance to sync automatically on a schedule, so that data stays current without manual intervention.

#### Acceptance Criteria

1. THE module SHALL register a cron job that executes hourly
2. WHEN the cron job executes, THE Sync_Engine SHALL sync attendance records for the current day
3. THE cron job SHALL use the configured API settings from biotime.config
4. WHEN the scheduled sync completes, THE Sync_Engine SHALL create a Sync_Log record with the results

### Requirement 5: Worked Hours Calculation

**User Story:** As an HR manager, I want worked hours calculated automatically with break deduction, so that I can track actual working time.

#### Acceptance Criteria

1. WHEN an Attendance_Record has both check-in and check-out times, THE Attendance_Record SHALL calculate worked_hours as the difference minus break duration
2. WHEN calculating worked hours, THE Attendance_Record SHALL use the break_duration from the Work_Schedule configuration
3. IF check-out time is missing, THEN THE Attendance_Record SHALL display worked_hours as zero and status as Incomplete

### Requirement 6: Late Detection

**User Story:** As an HR manager, I want to identify employees who arrive late, so that I can monitor punctuality.

#### Acceptance Criteria

1. WHEN an employee checks in after work_start_time plus late_tolerance, THE Attendance_Record SHALL be marked with is_late flag set to true
2. WHEN an employee checks in within the late_tolerance period, THE Attendance_Record SHALL not be marked as late
3. THE Attendance_Record SHALL calculate and store late_minutes as the difference between check-in time and work_start_time

### Requirement 7: Overtime Calculation

**User Story:** As an HR manager, I want overtime hours calculated automatically, so that I can track extra work time.

#### Acceptance Criteria

1. WHEN worked_hours exceeds the overtime_threshold, THE Attendance_Record SHALL calculate overtime_hours as worked_hours minus overtime_threshold
2. WHEN worked_hours is less than or equal to overtime_threshold, THE Attendance_Record SHALL set overtime_hours to zero
3. THE overtime_threshold SHALL be configurable in the Work_Schedule settings with a default of 8 hours

### Requirement 8: Attendance Status Management

**User Story:** As an HR manager, I want attendance records to have clear status indicators, so that I can quickly understand each employee's attendance situation.

#### Acceptance Criteria

1. THE Attendance_Record SHALL support the following status values: Present, Absent, Late, Leave, Half Day, Incomplete
2. WHEN an employee has complete check-in and check-out within tolerance, THE Attendance_Record status SHALL be Present
3. WHEN an employee checks in late but has complete records, THE Attendance_Record status SHALL be Late
4. WHEN an employee has check-in but no check-out, THE Attendance_Record status SHALL be Incomplete
5. WHEN worked_hours is less than half of the expected daily hours, THE Attendance_Record status SHALL be Half Day

### Requirement 9: Synchronization Logging

**User Story:** As an administrator, I want to view sync history and results, so that I can troubleshoot issues and verify data integrity.

#### Acceptance Criteria

1. WHEN a sync operation completes, THE Sync_Engine SHALL create a biotime.sync.log record
2. THE Sync_Log SHALL store sync_date, sync_type, records_created, records_updated, status, duration, and error_message fields
3. THE Sync_Log list view SHALL display all sync operations with filtering by date and status
4. IF a sync operation fails, THEN THE Sync_Log SHALL store the error message and set status to Error

### Requirement 10: Dashboard Statistics

**User Story:** As an HR manager, I want a dashboard showing today's attendance overview, so that I can monitor workforce presence at a glance.

#### Acceptance Criteria

1. WHEN a user opens the Dashboard, THE Dashboard SHALL display today's statistics: total employees, present count, absent count, late count, and total worked hours
2. THE Dashboard SHALL display an interactive presence trend chart showing the last 30 days
3. THE Dashboard SHALL display a department comparison chart showing hours by department
4. THE Dashboard SHALL display a status distribution pie chart
5. THE Dashboard SHALL display a top late employees list ranked by weekly late frequency

### Requirement 11: Dashboard Filtering

**User Story:** As an HR manager, I want to filter dashboard data by department and date range, so that I can analyze specific segments.

#### Acceptance Criteria

1. THE Dashboard SHALL provide a department filter dropdown
2. THE Dashboard SHALL provide a date range selector
3. WHEN filters are applied, THE Dashboard SHALL refresh all statistics and charts to reflect the filtered data

### Requirement 12: Manual Sync Wizard

**User Story:** As an administrator, I want to manually trigger sync with specific options, so that I can control what data is synchronized.

#### Acceptance Criteria

1. THE Sync_Wizard SHALL provide options for sync type: Employees Only, Attendance Only, Full Sync
2. THE Sync_Wizard SHALL provide date range fields for attendance sync
3. WHEN the administrator clicks Sync, THE Sync_Wizard SHALL execute the selected sync operation and display results
4. WHEN sync completes, THE Sync_Wizard SHALL display a summary of records created and updated

### Requirement 13: Security Access Levels

**User Story:** As an administrator, I want to control access to attendance data based on user roles, so that sensitive information is protected.

#### Acceptance Criteria

1. THE module SHALL define three security groups: Biotime User, Biotime Supervisor, Biotime Manager
2. WHEN a User accesses attendance records, THE Security_Rules SHALL restrict visibility to their own records only
3. WHEN a Supervisor accesses attendance records, THE Security_Rules SHALL allow visibility to their department's records
4. WHEN a Manager accesses attendance records, THE Security_Rules SHALL allow visibility to all records
5. THE Configuration settings SHALL be accessible only to Managers

### Requirement 14: Attendance Views

**User Story:** As an HR user, I want multiple views of attendance data, so that I can find and analyze records efficiently.

#### Acceptance Criteria

1. THE Attendance list view SHALL display employee name, date, check-in, check-out, worked hours, status, and late indicator
2. THE Attendance kanban view SHALL group records by status with visual indicators
3. THE Attendance form view SHALL display all fields including calculated values
4. THE module SHALL provide a Today's Attendance menu item showing only current day records
