# -*- coding: utf-8 -*-
"""
Property-based tests for Biotime Dashboard.

Uses hypothesis library for property-based testing.
Each test validates correctness properties from the design document.
"""
from datetime import datetime, date, timedelta
from hypothesis import given, strategies as st, assume, settings
from collections import defaultdict


# =============================================================================
# Property 8: Dashboard Department Hours Aggregation
# For any date range and set of attendance records, the department hours 
# aggregation SHALL return the sum of worked_hours grouped by department, 
# where each department's total equals the sum of all its employees' 
# worked_hours in the period.
# Validates: Requirements 10.3
# =============================================================================


def aggregate_department_hours(attendance_records):
    """
    Simulate the department hours aggregation logic from get_department_hours().
    
    Args:
        attendance_records: list of dicts with 'department_id', 'department_name', 
                           'worked_hours' keys
        
    Returns:
        list: List of dicts with department_id, department_name, total_hours
    """
    dept_hours = defaultdict(lambda: {'name': '', 'hours': 0.0})
    
    for record in attendance_records:
        dept_id = record.get('department_id')
        dept_name = record.get('department_name', 'No Department')
        worked_hours = record.get('worked_hours', 0.0)
        
        if dept_id:
            dept_hours[dept_id]['name'] = dept_name
            dept_hours[dept_id]['hours'] += worked_hours
        else:
            dept_hours[0]['name'] = 'No Department'
            dept_hours[0]['hours'] += worked_hours
    
    result = []
    for dept_id, data in dept_hours.items():
        result.append({
            'department_id': dept_id if dept_id else None,
            'department_name': data['name'],
            'total_hours': round(data['hours'], 2),
        })
    
    result.sort(key=lambda x: x['total_hours'], reverse=True)
    return result


@settings(max_examples=100)
@given(
    num_departments=st.integers(min_value=1, max_value=5),
    records_per_dept=st.integers(min_value=1, max_value=10),
    hours_per_record=st.floats(min_value=0.0, max_value=12.0),
)
def test_department_hours_aggregation_sum_equals_total(num_departments, records_per_dept, hours_per_record):
    """
    Feature: biotime-sync, Property 8: Dashboard Department Hours Aggregation
    
    The sum of all department totals SHALL equal the sum of all individual 
    worked_hours in the attendance records.
    
    **Validates: Requirements 10.3**
    """
    # Generate attendance records
    attendance_records = []
    total_expected_hours = 0.0
    
    for dept_id in range(1, num_departments + 1):
        for _ in range(records_per_dept):
            attendance_records.append({
                'department_id': dept_id,
                'department_name': f'Department {dept_id}',
                'worked_hours': hours_per_record,
            })
            total_expected_hours += hours_per_record
    
    # Aggregate
    result = aggregate_department_hours(attendance_records)
    
    # Sum of all department totals
    total_aggregated_hours = sum(d['total_hours'] for d in result)
    
    # Assert sum equals total (with floating point tolerance)
    # Note: We use a larger tolerance because each department's total is rounded
    # individually, which can accumulate small differences
    assert abs(total_aggregated_hours - total_expected_hours) < 0.1 * num_departments, \
        f"Expected total ~{total_expected_hours:.2f}, got {total_aggregated_hours}"


@settings(max_examples=100)
@given(
    dept_id=st.integers(min_value=1, max_value=100),
    num_records=st.integers(min_value=1, max_value=20),
    st_data=st.data(),
)
def test_department_hours_aggregation_per_department(dept_id, num_records, st_data):
    """
    Feature: biotime-sync, Property 8: Dashboard Department Hours Aggregation
    
    Each department's total SHALL equal the sum of all its employees' 
    worked_hours in the period.
    
    **Validates: Requirements 10.3**
    """
    # Generate records for a single department with varying hours
    attendance_records = []
    expected_dept_total = 0.0
    
    for _ in range(num_records):
        hours = st_data.draw(st.floats(min_value=0.0, max_value=12.0))
        attendance_records.append({
            'department_id': dept_id,
            'department_name': f'Department {dept_id}',
            'worked_hours': hours,
        })
        expected_dept_total += hours
    
    # Aggregate
    result = aggregate_department_hours(attendance_records)
    
    # Find the department in results
    dept_result = next((d for d in result if d['department_id'] == dept_id), None)
    
    assert dept_result is not None, f"Department {dept_id} should be in results"
    assert abs(dept_result['total_hours'] - round(expected_dept_total, 2)) < 0.01, \
        f"Expected {round(expected_dept_total, 2)} for dept {dept_id}, got {dept_result['total_hours']}"


@settings(max_examples=100)
@given(
    num_departments=st.integers(min_value=2, max_value=5),
)
def test_department_hours_aggregation_sorted_descending(num_departments):
    """
    Feature: biotime-sync, Property 8: Dashboard Department Hours Aggregation
    
    Results SHALL be sorted by total_hours in descending order.
    
    **Validates: Requirements 10.3**
    """
    # Generate records with different hours per department
    attendance_records = []
    
    for dept_id in range(1, num_departments + 1):
        # Each department gets different hours (dept_id * 2)
        hours = dept_id * 2.0
        attendance_records.append({
            'department_id': dept_id,
            'department_name': f'Department {dept_id}',
            'worked_hours': hours,
        })
    
    # Aggregate
    result = aggregate_department_hours(attendance_records)
    
    # Check descending order
    hours_list = [d['total_hours'] for d in result]
    assert hours_list == sorted(hours_list, reverse=True), \
        f"Results should be sorted descending: {hours_list}"


def test_department_hours_aggregation_empty_records():
    """
    Feature: biotime-sync, Property 8: Dashboard Department Hours Aggregation
    
    Empty attendance records SHALL return empty results.
    
    **Validates: Requirements 10.3**
    """
    result = aggregate_department_hours([])
    assert result == [], f"Expected empty list, got {result}"


@settings(max_examples=100)
@given(
    num_records=st.integers(min_value=1, max_value=10),
    hours_per_record=st.floats(min_value=0.0, max_value=12.0),
)
def test_department_hours_aggregation_no_department(num_records, hours_per_record):
    """
    Feature: biotime-sync, Property 8: Dashboard Department Hours Aggregation
    
    Records without department SHALL be grouped under 'No Department'.
    
    **Validates: Requirements 10.3**
    """
    # Generate records without department
    attendance_records = []
    expected_total = 0.0
    
    for _ in range(num_records):
        attendance_records.append({
            'department_id': None,
            'department_name': None,
            'worked_hours': hours_per_record,
        })
        expected_total += hours_per_record
    
    # Aggregate
    result = aggregate_department_hours(attendance_records)
    
    # Should have one entry for 'No Department'
    assert len(result) == 1, f"Expected 1 result, got {len(result)}"
    assert result[0]['department_name'] == 'No Department', \
        f"Expected 'No Department', got {result[0]['department_name']}"
    assert abs(result[0]['total_hours'] - round(expected_total, 2)) < 0.01, \
        f"Expected {round(expected_total, 2)}, got {result[0]['total_hours']}"



# =============================================================================
# Property 9: Dashboard Status Distribution
# For any date and set of attendance records, the status distribution SHALL 
# return counts for each status value where the sum of all counts equals the 
# total number of records for that date.
# Validates: Requirements 10.4
# =============================================================================


def compute_status_distribution(attendance_records, total_employees):
    """
    Simulate the status distribution logic from get_status_distribution().
    
    Args:
        attendance_records: list of dicts with 'status' key
        total_employees: total number of employees for absent calculation
        
    Returns:
        dict: Status counts {present: N, late: N, absent: N, ...}
    """
    status_counts = {
        'present': 0,
        'absent': 0,
        'late': 0,
        'leave': 0,
        'half_day': 0,
        'incomplete': 0,
    }
    
    for record in attendance_records:
        status = record.get('status')
        if status in status_counts:
            status_counts[status] += 1
    
    # Calculate absent as employees without attendance record
    employees_with_attendance = len(attendance_records)
    status_counts['absent'] = max(0, total_employees - employees_with_attendance)
    
    return status_counts


@settings(max_examples=100)
@given(
    num_present=st.integers(min_value=0, max_value=20),
    num_late=st.integers(min_value=0, max_value=20),
    num_incomplete=st.integers(min_value=0, max_value=20),
    num_half_day=st.integers(min_value=0, max_value=20),
    num_leave=st.integers(min_value=0, max_value=20),
    extra_employees=st.integers(min_value=0, max_value=10),
)
def test_status_distribution_sum_equals_total(num_present, num_late, num_incomplete, 
                                               num_half_day, num_leave, extra_employees):
    """
    Feature: biotime-sync, Property 9: Dashboard Status Distribution
    
    The sum of all status counts SHALL equal the total number of employees
    (records with attendance + absent employees).
    
    **Validates: Requirements 10.4**
    """
    # Generate attendance records with various statuses
    attendance_records = []
    
    for _ in range(num_present):
        attendance_records.append({'status': 'present'})
    for _ in range(num_late):
        attendance_records.append({'status': 'late'})
    for _ in range(num_incomplete):
        attendance_records.append({'status': 'incomplete'})
    for _ in range(num_half_day):
        attendance_records.append({'status': 'half_day'})
    for _ in range(num_leave):
        attendance_records.append({'status': 'leave'})
    
    # Total employees = records + extra (absent)
    total_employees = len(attendance_records) + extra_employees
    
    # Compute distribution
    result = compute_status_distribution(attendance_records, total_employees)
    
    # Sum of all counts should equal total employees
    total_count = sum(result.values())
    
    assert total_count == total_employees, \
        f"Sum of status counts ({total_count}) should equal total employees ({total_employees})"


@settings(max_examples=100)
@given(
    num_records=st.integers(min_value=1, max_value=50),
    status=st.sampled_from(['present', 'late', 'incomplete', 'half_day', 'leave']),
)
def test_status_distribution_correct_count_per_status(num_records, status):
    """
    Feature: biotime-sync, Property 9: Dashboard Status Distribution
    
    Each status count SHALL equal the number of records with that status.
    
    **Validates: Requirements 10.4**
    """
    # Generate records with single status
    attendance_records = [{'status': status} for _ in range(num_records)]
    
    # Compute distribution (no extra employees for simplicity)
    result = compute_status_distribution(attendance_records, num_records)
    
    # The specific status should have the correct count
    assert result[status] == num_records, \
        f"Expected {num_records} for status '{status}', got {result[status]}"


@settings(max_examples=100)
@given(
    total_employees=st.integers(min_value=1, max_value=100),
    num_with_attendance=st.integers(min_value=0, max_value=100),
)
def test_status_distribution_absent_calculation(total_employees, num_with_attendance):
    """
    Feature: biotime-sync, Property 9: Dashboard Status Distribution
    
    Absent count SHALL equal total_employees minus employees with attendance records.
    
    **Validates: Requirements 10.4**
    """
    # Ensure num_with_attendance doesn't exceed total
    num_with_attendance = min(num_with_attendance, total_employees)
    
    # Generate attendance records
    attendance_records = [{'status': 'present'} for _ in range(num_with_attendance)]
    
    # Compute distribution
    result = compute_status_distribution(attendance_records, total_employees)
    
    expected_absent = total_employees - num_with_attendance
    
    assert result['absent'] == expected_absent, \
        f"Expected {expected_absent} absent, got {result['absent']}"


def test_status_distribution_empty_records():
    """
    Feature: biotime-sync, Property 9: Dashboard Status Distribution
    
    With no attendance records, all employees should be marked absent.
    
    **Validates: Requirements 10.4**
    """
    total_employees = 10
    attendance_records = []
    
    result = compute_status_distribution(attendance_records, total_employees)
    
    assert result['absent'] == total_employees, \
        f"Expected {total_employees} absent, got {result['absent']}"
    assert result['present'] == 0, "Expected 0 present"
    assert result['late'] == 0, "Expected 0 late"


@settings(max_examples=100)
@given(
    st_data=st.data(),
)
def test_status_distribution_all_statuses_present(st_data):
    """
    Feature: biotime-sync, Property 9: Dashboard Status Distribution
    
    Distribution SHALL correctly count all status types when mixed.
    
    **Validates: Requirements 10.4**
    """
    statuses = ['present', 'late', 'incomplete', 'half_day', 'leave']
    expected_counts = {}
    attendance_records = []
    
    for status in statuses:
        count = st_data.draw(st.integers(min_value=0, max_value=10))
        expected_counts[status] = count
        for _ in range(count):
            attendance_records.append({'status': status})
    
    total_employees = len(attendance_records)
    
    result = compute_status_distribution(attendance_records, total_employees)
    
    for status in statuses:
        assert result[status] == expected_counts[status], \
            f"Expected {expected_counts[status]} for '{status}', got {result[status]}"



# =============================================================================
# Property 10: Top Late Employees Ranking
# For any set of attendance records over a week, the top late employees list 
# SHALL be ordered by late_count descending, where late_count is the number 
# of records with is_late=true for each employee.
# Validates: Requirements 10.5
# =============================================================================


def compute_top_late(attendance_records, limit=10):
    """
    Simulate the top late employees logic from get_top_late().
    
    Args:
        attendance_records: list of dicts with 'employee_id', 'employee_name', 
                           'is_late', 'late_minutes' keys
        limit: Maximum number of employees to return
        
    Returns:
        list: List of dicts with employee_id, employee_name, late_count, 
              total_late_minutes, sorted by late_count descending
    """
    employee_late = defaultdict(lambda: {
        'name': '',
        'late_count': 0,
        'total_late_minutes': 0
    })
    
    for record in attendance_records:
        if record.get('is_late'):
            emp_id = record['employee_id']
            employee_late[emp_id]['name'] = record.get('employee_name', '')
            employee_late[emp_id]['late_count'] += 1
            employee_late[emp_id]['total_late_minutes'] += record.get('late_minutes', 0)
    
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
    
    return result[:limit]


@settings(max_examples=100)
@given(
    num_employees=st.integers(min_value=2, max_value=10),
    st_data=st.data(),
)
def test_top_late_ranking_sorted_descending(num_employees, st_data):
    """
    Feature: biotime-sync, Property 10: Top Late Employees Ranking
    
    The top late employees list SHALL be ordered by late_count descending.
    
    **Validates: Requirements 10.5**
    """
    # Generate attendance records with varying late counts per employee
    attendance_records = []
    
    for emp_id in range(1, num_employees + 1):
        late_count = st_data.draw(st.integers(min_value=0, max_value=7))
        for _ in range(late_count):
            attendance_records.append({
                'employee_id': emp_id,
                'employee_name': f'Employee {emp_id}',
                'is_late': True,
                'late_minutes': 15,
            })
    
    # Compute top late
    result = compute_top_late(attendance_records)
    
    # Check descending order by late_count
    late_counts = [r['late_count'] for r in result]
    assert late_counts == sorted(late_counts, reverse=True), \
        f"Results should be sorted by late_count descending: {late_counts}"


@settings(max_examples=100)
@given(
    emp_id=st.integers(min_value=1, max_value=100),
    late_count=st.integers(min_value=1, max_value=7),
    late_minutes_per_day=st.integers(min_value=1, max_value=120),
)
def test_top_late_ranking_correct_count(emp_id, late_count, late_minutes_per_day):
    """
    Feature: biotime-sync, Property 10: Top Late Employees Ranking
    
    late_count SHALL equal the number of records with is_late=true for each employee.
    
    **Validates: Requirements 10.5**
    """
    # Generate attendance records for single employee
    attendance_records = []
    
    for _ in range(late_count):
        attendance_records.append({
            'employee_id': emp_id,
            'employee_name': f'Employee {emp_id}',
            'is_late': True,
            'late_minutes': late_minutes_per_day,
        })
    
    # Compute top late
    result = compute_top_late(attendance_records)
    
    assert len(result) == 1, f"Expected 1 employee, got {len(result)}"
    assert result[0]['late_count'] == late_count, \
        f"Expected late_count {late_count}, got {result[0]['late_count']}"
    assert result[0]['total_late_minutes'] == late_count * late_minutes_per_day, \
        f"Expected total_late_minutes {late_count * late_minutes_per_day}, got {result[0]['total_late_minutes']}"


@settings(max_examples=100)
@given(
    num_employees=st.integers(min_value=5, max_value=20),
    limit=st.integers(min_value=1, max_value=10),
)
def test_top_late_ranking_respects_limit(num_employees, limit):
    """
    Feature: biotime-sync, Property 10: Top Late Employees Ranking
    
    The result SHALL be limited to the specified number of employees.
    
    **Validates: Requirements 10.5**
    """
    # Generate attendance records for multiple employees
    attendance_records = []
    
    for emp_id in range(1, num_employees + 1):
        attendance_records.append({
            'employee_id': emp_id,
            'employee_name': f'Employee {emp_id}',
            'is_late': True,
            'late_minutes': 15,
        })
    
    # Compute top late with limit
    result = compute_top_late(attendance_records, limit=limit)
    
    expected_count = min(num_employees, limit)
    assert len(result) <= limit, \
        f"Result should be limited to {limit}, got {len(result)}"
    assert len(result) == expected_count, \
        f"Expected {expected_count} employees, got {len(result)}"


def test_top_late_ranking_excludes_non_late():
    """
    Feature: biotime-sync, Property 10: Top Late Employees Ranking
    
    Employees with is_late=false SHALL NOT appear in the ranking.
    
    **Validates: Requirements 10.5**
    """
    attendance_records = [
        {'employee_id': 1, 'employee_name': 'Employee 1', 'is_late': True, 'late_minutes': 15},
        {'employee_id': 2, 'employee_name': 'Employee 2', 'is_late': False, 'late_minutes': 0},
        {'employee_id': 3, 'employee_name': 'Employee 3', 'is_late': True, 'late_minutes': 30},
    ]
    
    result = compute_top_late(attendance_records)
    
    # Only employees 1 and 3 should appear
    employee_ids = [r['employee_id'] for r in result]
    assert 2 not in employee_ids, "Employee 2 (not late) should not appear"
    assert 1 in employee_ids, "Employee 1 (late) should appear"
    assert 3 in employee_ids, "Employee 3 (late) should appear"


def test_top_late_ranking_empty_records():
    """
    Feature: biotime-sync, Property 10: Top Late Employees Ranking
    
    Empty attendance records SHALL return empty results.
    
    **Validates: Requirements 10.5**
    """
    result = compute_top_late([])
    assert result == [], f"Expected empty list, got {result}"


@settings(max_examples=100)
@given(
    num_employees=st.integers(min_value=2, max_value=5),
)
def test_top_late_ranking_aggregates_by_employee(num_employees):
    """
    Feature: biotime-sync, Property 10: Top Late Employees Ranking
    
    Multiple late records for the same employee SHALL be aggregated.
    
    **Validates: Requirements 10.5**
    """
    # Generate multiple late records per employee
    attendance_records = []
    
    for emp_id in range(1, num_employees + 1):
        # Each employee has emp_id number of late records
        for day in range(emp_id):
            attendance_records.append({
                'employee_id': emp_id,
                'employee_name': f'Employee {emp_id}',
                'is_late': True,
                'late_minutes': 10,
            })
    
    result = compute_top_late(attendance_records)
    
    # Each employee should appear once with aggregated count
    assert len(result) == num_employees, \
        f"Expected {num_employees} employees, got {len(result)}"
    
    # Verify aggregation
    for r in result:
        emp_id = r['employee_id']
        assert r['late_count'] == emp_id, \
            f"Employee {emp_id} should have late_count {emp_id}, got {r['late_count']}"



# =============================================================================
# Property 11: Dashboard Filter Application
# For any department filter D and date range [start, end], all dashboard 
# statistics SHALL only include attendance records where 
# employee.department_id = D (if D specified) AND date is within [start, end].
# Validates: Requirements 11.3
# =============================================================================


def apply_filters(attendance_records, department_id=None, date_from=None, date_to=None):
    """
    Simulate the filter application logic used across dashboard endpoints.
    
    Args:
        attendance_records: list of dicts with 'department_id', 'date' keys
        department_id: Optional department filter
        date_from: Optional start date
        date_to: Optional end date
        
    Returns:
        list: Filtered attendance records
    """
    filtered = []
    
    for record in attendance_records:
        # Apply department filter
        if department_id is not None:
            if record.get('department_id') != department_id:
                continue
        
        # Apply date range filter
        record_date = record.get('date')
        if date_from is not None and record_date < date_from:
            continue
        if date_to is not None and record_date > date_to:
            continue
        
        filtered.append(record)
    
    return filtered


@settings(max_examples=100)
@given(
    target_dept=st.integers(min_value=1, max_value=5),
    num_records=st.integers(min_value=5, max_value=20),
    st_data=st.data(),
)
def test_filter_application_department_filter(target_dept, num_records, st_data):
    """
    Feature: biotime-sync, Property 11: Dashboard Filter Application
    
    When department filter D is applied, all results SHALL have 
    employee.department_id = D.
    
    **Validates: Requirements 11.3**
    """
    # Generate records with various departments
    attendance_records = []
    base_date = date(2024, 1, 15)
    
    for i in range(num_records):
        dept_id = st_data.draw(st.integers(min_value=1, max_value=5))
        attendance_records.append({
            'department_id': dept_id,
            'date': base_date,
            'worked_hours': 8.0,
        })
    
    # Apply department filter
    filtered = apply_filters(attendance_records, department_id=target_dept)
    
    # All filtered records should have the target department
    for record in filtered:
        assert record['department_id'] == target_dept, \
            f"Expected department_id {target_dept}, got {record['department_id']}"


@settings(max_examples=100)
@given(
    start_offset=st.integers(min_value=0, max_value=10),
    end_offset=st.integers(min_value=0, max_value=10),
    num_records=st.integers(min_value=5, max_value=20),
    st_data=st.data(),
)
def test_filter_application_date_range_filter(start_offset, end_offset, num_records, st_data):
    """
    Feature: biotime-sync, Property 11: Dashboard Filter Application
    
    When date range [start, end] is applied, all results SHALL have 
    date within [start, end].
    
    **Validates: Requirements 11.3**
    """
    # Define date range
    base_date = date(2024, 1, 15)
    date_from = base_date - timedelta(days=start_offset)
    date_to = base_date + timedelta(days=end_offset)
    
    # Generate records with various dates
    attendance_records = []
    
    for i in range(num_records):
        # Random date within a wider range
        day_offset = st_data.draw(st.integers(min_value=-15, max_value=15))
        record_date = base_date + timedelta(days=day_offset)
        attendance_records.append({
            'department_id': 1,
            'date': record_date,
            'worked_hours': 8.0,
        })
    
    # Apply date range filter
    filtered = apply_filters(attendance_records, date_from=date_from, date_to=date_to)
    
    # All filtered records should be within date range
    for record in filtered:
        assert record['date'] >= date_from, \
            f"Record date {record['date']} should be >= {date_from}"
        assert record['date'] <= date_to, \
            f"Record date {record['date']} should be <= {date_to}"


@settings(max_examples=100)
@given(
    target_dept=st.integers(min_value=1, max_value=3),
    num_records=st.integers(min_value=10, max_value=30),
    st_data=st.data(),
)
def test_filter_application_combined_filters(target_dept, num_records, st_data):
    """
    Feature: biotime-sync, Property 11: Dashboard Filter Application
    
    When both department and date range filters are applied, all results 
    SHALL satisfy both conditions.
    
    **Validates: Requirements 11.3**
    """
    # Define filters
    base_date = date(2024, 1, 15)
    date_from = base_date - timedelta(days=5)
    date_to = base_date + timedelta(days=5)
    
    # Generate records with various departments and dates
    attendance_records = []
    
    for i in range(num_records):
        dept_id = st_data.draw(st.integers(min_value=1, max_value=5))
        day_offset = st_data.draw(st.integers(min_value=-10, max_value=10))
        record_date = base_date + timedelta(days=day_offset)
        attendance_records.append({
            'department_id': dept_id,
            'date': record_date,
            'worked_hours': 8.0,
        })
    
    # Apply both filters
    filtered = apply_filters(attendance_records, 
                            department_id=target_dept, 
                            date_from=date_from, 
                            date_to=date_to)
    
    # All filtered records should satisfy both conditions
    for record in filtered:
        assert record['department_id'] == target_dept, \
            f"Expected department_id {target_dept}, got {record['department_id']}"
        assert record['date'] >= date_from, \
            f"Record date {record['date']} should be >= {date_from}"
        assert record['date'] <= date_to, \
            f"Record date {record['date']} should be <= {date_to}"


@settings(max_examples=100)
@given(
    num_records=st.integers(min_value=5, max_value=20),
)
def test_filter_application_no_filter_returns_all(num_records):
    """
    Feature: biotime-sync, Property 11: Dashboard Filter Application
    
    When no filters are applied, all records SHALL be returned.
    
    **Validates: Requirements 11.3**
    """
    # Generate records
    base_date = date(2024, 1, 15)
    attendance_records = []
    
    for i in range(num_records):
        attendance_records.append({
            'department_id': i % 3 + 1,
            'date': base_date + timedelta(days=i),
            'worked_hours': 8.0,
        })
    
    # Apply no filters
    filtered = apply_filters(attendance_records)
    
    assert len(filtered) == num_records, \
        f"Expected {num_records} records, got {len(filtered)}"


def test_filter_application_empty_result():
    """
    Feature: biotime-sync, Property 11: Dashboard Filter Application
    
    When filters match no records, empty result SHALL be returned.
    
    **Validates: Requirements 11.3**
    """
    base_date = date(2024, 1, 15)
    attendance_records = [
        {'department_id': 1, 'date': base_date, 'worked_hours': 8.0},
        {'department_id': 2, 'date': base_date, 'worked_hours': 8.0},
    ]
    
    # Filter for non-existent department
    filtered = apply_filters(attendance_records, department_id=999)
    
    assert filtered == [], f"Expected empty list, got {filtered}"


@settings(max_examples=100)
@given(
    target_dept=st.integers(min_value=1, max_value=5),
    num_matching=st.integers(min_value=1, max_value=10),
    num_non_matching=st.integers(min_value=1, max_value=10),
)
def test_filter_application_correct_count(target_dept, num_matching, num_non_matching):
    """
    Feature: biotime-sync, Property 11: Dashboard Filter Application
    
    The number of filtered records SHALL equal the number of records 
    matching the filter criteria.
    
    **Validates: Requirements 11.3**
    """
    base_date = date(2024, 1, 15)
    attendance_records = []
    
    # Add matching records
    for i in range(num_matching):
        attendance_records.append({
            'department_id': target_dept,
            'date': base_date,
            'worked_hours': 8.0,
        })
    
    # Add non-matching records
    other_dept = target_dept + 1 if target_dept < 5 else 1
    for i in range(num_non_matching):
        attendance_records.append({
            'department_id': other_dept,
            'date': base_date,
            'worked_hours': 8.0,
        })
    
    # Apply filter
    filtered = apply_filters(attendance_records, department_id=target_dept)
    
    assert len(filtered) == num_matching, \
        f"Expected {num_matching} matching records, got {len(filtered)}"
