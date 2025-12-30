# -*- coding: utf-8 -*-
"""
Property-based tests for Biotime Security Rules.

Uses hypothesis library for property-based testing.
Each test validates correctness properties from the design document.
"""
from hypothesis import given, strategies as st, assume, settings


# =============================================================================
# Property 12: Security-Based Record Visibility
# For any user U accessing attendance records:
# - If U is in User group: visible records SHALL only include records where 
#   employee_id.user_id = U
# - If U is in Supervisor group: visible records SHALL only include records 
#   where employee_id.department_id = U.employee_id.department_id
# - If U is in Manager group: all records SHALL be visible
# Validates: Requirements 13.2, 13.3, 13.4
# =============================================================================


def filter_records_by_security(user, attendance_records, user_group):
    """
    Simulate the security record rule filtering logic.
    
    Args:
        user: dict with 'id', 'employee_id' (dict with 'id', 'department_id')
        attendance_records: list of dicts with 'employee_id' (dict with 'user_id', 'department_id')
        user_group: 'user', 'supervisor', or 'manager'
        
    Returns:
        list: Filtered attendance records based on security rules
    """
    if user_group == 'manager':
        # Manager: no domain restriction - all records visible
        return attendance_records
    
    elif user_group == 'supervisor':
        # Supervisor: filter to same department
        user_dept_id = user.get('employee_id', {}).get('department_id')
        if user_dept_id is None:
            return []
        return [
            rec for rec in attendance_records
            if rec.get('employee_id', {}).get('department_id') == user_dept_id
        ]
    
    else:  # user_group == 'user'
        # User: filter to own employee records only
        user_id = user.get('id')
        return [
            rec for rec in attendance_records
            if rec.get('employee_id', {}).get('user_id') == user_id
        ]


# Strategy for generating employee data
employee_strategy = st.fixed_dictionaries({
    'id': st.integers(min_value=1, max_value=1000),
    'user_id': st.integers(min_value=1, max_value=100),
    'department_id': st.integers(min_value=1, max_value=20),
})

# Strategy for generating attendance records
attendance_strategy = st.fixed_dictionaries({
    'id': st.integers(min_value=1, max_value=10000),
    'employee_id': employee_strategy,
})


@settings(max_examples=100)
@given(
    user_id=st.integers(min_value=1, max_value=100),
    user_dept_id=st.integers(min_value=1, max_value=20),
    num_records=st.integers(min_value=1, max_value=20),
    data=st.data(),
)
def test_user_group_sees_only_own_records(user_id, user_dept_id, num_records, data):
    """
    Feature: biotime-sync, Property 12: Security-Based Record Visibility
    
    If U is in User group: visible records SHALL only include records 
    where employee_id.user_id = U
    
    **Validates: Requirements 13.2**
    """
    # Create user
    user = {
        'id': user_id,
        'employee_id': {
            'id': user_id * 10,
            'department_id': user_dept_id,
        }
    }
    
    # Generate attendance records with various user_ids
    attendance_records = []
    for i in range(num_records):
        rec_user_id = data.draw(st.integers(min_value=1, max_value=100))
        rec_dept_id = data.draw(st.integers(min_value=1, max_value=20))
        attendance_records.append({
            'id': i + 1,
            'employee_id': {
                'id': i + 100,
                'user_id': rec_user_id,
                'department_id': rec_dept_id,
            }
        })
    
    # Filter records as User group
    visible_records = filter_records_by_security(user, attendance_records, 'user')
    
    # Assert: all visible records belong to the user
    for rec in visible_records:
        assert rec['employee_id']['user_id'] == user_id, \
            f"User should only see own records, but saw record with user_id={rec['employee_id']['user_id']}"
    
    # Assert: all user's records are visible
    expected_count = sum(1 for r in attendance_records if r['employee_id']['user_id'] == user_id)
    assert len(visible_records) == expected_count, \
        f"Expected {expected_count} records, got {len(visible_records)}"



@settings(max_examples=100)
@given(
    user_id=st.integers(min_value=1, max_value=100),
    user_dept_id=st.integers(min_value=1, max_value=20),
    num_records=st.integers(min_value=1, max_value=20),
    data=st.data(),
)
def test_supervisor_group_sees_department_records(user_id, user_dept_id, num_records, data):
    """
    Feature: biotime-sync, Property 12: Security-Based Record Visibility
    
    If U is in Supervisor group: visible records SHALL only include records 
    where employee_id.department_id = U.employee_id.department_id
    
    **Validates: Requirements 13.3**
    """
    # Create user (supervisor)
    user = {
        'id': user_id,
        'employee_id': {
            'id': user_id * 10,
            'department_id': user_dept_id,
        }
    }
    
    # Generate attendance records with various department_ids
    attendance_records = []
    for i in range(num_records):
        rec_user_id = data.draw(st.integers(min_value=1, max_value=100))
        rec_dept_id = data.draw(st.integers(min_value=1, max_value=20))
        attendance_records.append({
            'id': i + 1,
            'employee_id': {
                'id': i + 100,
                'user_id': rec_user_id,
                'department_id': rec_dept_id,
            }
        })
    
    # Filter records as Supervisor group
    visible_records = filter_records_by_security(user, attendance_records, 'supervisor')
    
    # Assert: all visible records belong to the same department
    for rec in visible_records:
        assert rec['employee_id']['department_id'] == user_dept_id, \
            f"Supervisor should only see department records, but saw record with dept_id={rec['employee_id']['department_id']}"
    
    # Assert: all department records are visible
    expected_count = sum(1 for r in attendance_records if r['employee_id']['department_id'] == user_dept_id)
    assert len(visible_records) == expected_count, \
        f"Expected {expected_count} records, got {len(visible_records)}"


@settings(max_examples=100)
@given(
    user_id=st.integers(min_value=1, max_value=100),
    user_dept_id=st.integers(min_value=1, max_value=20),
    num_records=st.integers(min_value=1, max_value=20),
    data=st.data(),
)
def test_manager_group_sees_all_records(user_id, user_dept_id, num_records, data):
    """
    Feature: biotime-sync, Property 12: Security-Based Record Visibility
    
    If U is in Manager group: all records SHALL be visible
    
    **Validates: Requirements 13.4**
    """
    # Create user (manager)
    user = {
        'id': user_id,
        'employee_id': {
            'id': user_id * 10,
            'department_id': user_dept_id,
        }
    }
    
    # Generate attendance records with various user_ids and department_ids
    attendance_records = []
    for i in range(num_records):
        rec_user_id = data.draw(st.integers(min_value=1, max_value=100))
        rec_dept_id = data.draw(st.integers(min_value=1, max_value=20))
        attendance_records.append({
            'id': i + 1,
            'employee_id': {
                'id': i + 100,
                'user_id': rec_user_id,
                'department_id': rec_dept_id,
            }
        })
    
    # Filter records as Manager group
    visible_records = filter_records_by_security(user, attendance_records, 'manager')
    
    # Assert: all records are visible to manager
    assert len(visible_records) == len(attendance_records), \
        f"Manager should see all {len(attendance_records)} records, got {len(visible_records)}"
    
    # Assert: records are the same (not filtered)
    visible_ids = {r['id'] for r in visible_records}
    expected_ids = {r['id'] for r in attendance_records}
    assert visible_ids == expected_ids, \
        f"Manager should see all records, missing: {expected_ids - visible_ids}"


@settings(max_examples=100)
@given(
    user_id=st.integers(min_value=1, max_value=100),
    user_dept_id=st.integers(min_value=1, max_value=20),
)
def test_user_group_empty_when_no_own_records(user_id, user_dept_id):
    """
    Feature: biotime-sync, Property 12: Security-Based Record Visibility
    
    If U is in User group and no records belong to U, visible records SHALL be empty.
    
    **Validates: Requirements 13.2**
    """
    # Create user
    user = {
        'id': user_id,
        'employee_id': {
            'id': user_id * 10,
            'department_id': user_dept_id,
        }
    }
    
    # Create records that don't belong to the user
    other_user_id = user_id + 1  # Different user
    attendance_records = [
        {
            'id': 1,
            'employee_id': {
                'id': 100,
                'user_id': other_user_id,
                'department_id': user_dept_id,
            }
        },
        {
            'id': 2,
            'employee_id': {
                'id': 101,
                'user_id': other_user_id + 1,
                'department_id': user_dept_id + 1,
            }
        },
    ]
    
    # Filter records as User group
    visible_records = filter_records_by_security(user, attendance_records, 'user')
    
    # Assert: no records visible
    assert len(visible_records) == 0, \
        f"User should see 0 records when none belong to them, got {len(visible_records)}"


@settings(max_examples=100)
@given(
    user_id=st.integers(min_value=1, max_value=100),
    user_dept_id=st.integers(min_value=1, max_value=20),
)
def test_supervisor_empty_when_no_department_records(user_id, user_dept_id):
    """
    Feature: biotime-sync, Property 12: Security-Based Record Visibility
    
    If U is in Supervisor group and no records belong to U's department, 
    visible records SHALL be empty.
    
    **Validates: Requirements 13.3**
    """
    # Create user (supervisor)
    user = {
        'id': user_id,
        'employee_id': {
            'id': user_id * 10,
            'department_id': user_dept_id,
        }
    }
    
    # Create records from different departments
    other_dept_id = user_dept_id + 1  # Different department
    attendance_records = [
        {
            'id': 1,
            'employee_id': {
                'id': 100,
                'user_id': user_id + 1,
                'department_id': other_dept_id,
            }
        },
        {
            'id': 2,
            'employee_id': {
                'id': 101,
                'user_id': user_id + 2,
                'department_id': other_dept_id + 1,
            }
        },
    ]
    
    # Filter records as Supervisor group
    visible_records = filter_records_by_security(user, attendance_records, 'supervisor')
    
    # Assert: no records visible
    assert len(visible_records) == 0, \
        f"Supervisor should see 0 records when none in their department, got {len(visible_records)}"


@settings(max_examples=100)
@given(
    user_id=st.integers(min_value=1, max_value=100),
    user_dept_id=st.integers(min_value=1, max_value=20),
)
def test_group_hierarchy_manager_implies_supervisor(user_id, user_dept_id):
    """
    Feature: biotime-sync, Property 12: Security-Based Record Visibility
    
    Manager group implies Supervisor group - managers should see at least 
    what supervisors see (and more).
    
    **Validates: Requirements 13.3, 13.4**
    """
    # Create user
    user = {
        'id': user_id,
        'employee_id': {
            'id': user_id * 10,
            'department_id': user_dept_id,
        }
    }
    
    # Create mixed records
    attendance_records = [
        {
            'id': 1,
            'employee_id': {
                'id': 100,
                'user_id': user_id,
                'department_id': user_dept_id,
            }
        },
        {
            'id': 2,
            'employee_id': {
                'id': 101,
                'user_id': user_id + 1,
                'department_id': user_dept_id,
            }
        },
        {
            'id': 3,
            'employee_id': {
                'id': 102,
                'user_id': user_id + 2,
                'department_id': user_dept_id + 1,
            }
        },
    ]
    
    # Get visible records for each group
    supervisor_visible = filter_records_by_security(user, attendance_records, 'supervisor')
    manager_visible = filter_records_by_security(user, attendance_records, 'manager')
    
    # Assert: manager sees at least what supervisor sees
    supervisor_ids = {r['id'] for r in supervisor_visible}
    manager_ids = {r['id'] for r in manager_visible}
    
    assert supervisor_ids.issubset(manager_ids), \
        f"Manager should see all supervisor records. Supervisor: {supervisor_ids}, Manager: {manager_ids}"


@settings(max_examples=100)
@given(
    user_id=st.integers(min_value=1, max_value=100),
    user_dept_id=st.integers(min_value=1, max_value=20),
)
def test_group_hierarchy_supervisor_implies_user(user_id, user_dept_id):
    """
    Feature: biotime-sync, Property 12: Security-Based Record Visibility
    
    Supervisor group implies User group - supervisors should see at least 
    what users see (and more).
    
    **Validates: Requirements 13.2, 13.3**
    """
    # Create user
    user = {
        'id': user_id,
        'employee_id': {
            'id': user_id * 10,
            'department_id': user_dept_id,
        }
    }
    
    # Create mixed records - include user's own record in their department
    attendance_records = [
        {
            'id': 1,
            'employee_id': {
                'id': 100,
                'user_id': user_id,  # User's own record
                'department_id': user_dept_id,  # In user's department
            }
        },
        {
            'id': 2,
            'employee_id': {
                'id': 101,
                'user_id': user_id + 1,  # Different user
                'department_id': user_dept_id,  # Same department
            }
        },
        {
            'id': 3,
            'employee_id': {
                'id': 102,
                'user_id': user_id + 2,
                'department_id': user_dept_id + 1,  # Different department
            }
        },
    ]
    
    # Get visible records for each group
    user_visible = filter_records_by_security(user, attendance_records, 'user')
    supervisor_visible = filter_records_by_security(user, attendance_records, 'supervisor')
    
    # Assert: supervisor sees at least what user sees (when user's records are in their dept)
    user_ids = {r['id'] for r in user_visible}
    supervisor_ids = {r['id'] for r in supervisor_visible}
    
    # User's own records that are in their department should be visible to supervisor
    user_own_in_dept = {r['id'] for r in user_visible if r['employee_id']['department_id'] == user_dept_id}
    
    assert user_own_in_dept.issubset(supervisor_ids), \
        f"Supervisor should see user's own department records. User own in dept: {user_own_in_dept}, Supervisor: {supervisor_ids}"
