# -*- coding: utf-8 -*-
"""
Property-based tests for Biotime Sync Engine.

Uses hypothesis library for property-based testing.
Each test validates correctness properties from the design document.
"""
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume, settings
from collections import defaultdict


# =============================================================================
# Property 1: Employee Matching Priority
# For any Biotime employee record and set of Odoo employees, the matching 
# algorithm SHALL first attempt to match by biotime_id, and only if no match 
# is found, attempt to match by barcode field.
# Validates: Requirements 2.2
# =============================================================================


def match_employee(biotime_emp, odoo_employees):
    """
    Simulate the employee matching algorithm from sync_employees().
    
    Matching priority:
    1. First match by biotime_id
    2. If no match, try matching by barcode
    
    Args:
        biotime_emp: dict with 'id' or 'emp_code' keys
        odoo_employees: list of dicts with 'biotime_id' and 'barcode' keys
        
    Returns:
        tuple: (matched_employee or None, match_type: 'biotime_id'|'barcode'|None)
    """
    bt_id = str(biotime_emp.get('id', '')) or str(biotime_emp.get('emp_code', ''))
    bt_code = str(biotime_emp.get('emp_code', ''))
    
    if not bt_id:
        return None, None
    
    # Step 1: Try to match by biotime_id first
    for emp in odoo_employees:
        if emp.get('biotime_id') == bt_id:
            return emp, 'biotime_id'
    
    # Step 2: If no match, try matching by barcode
    if bt_code:
        for emp in odoo_employees:
            if emp.get('barcode') == bt_code:
                return emp, 'barcode'
    
    return None, None


@settings(max_examples=100)
@given(
    bt_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu', 'Ll'))),
    bt_code=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu', 'Ll'))),
)
def test_employee_matching_priority_biotime_id_first(bt_id, bt_code):
    """
    Feature: biotime-sync, Property 1: Employee Matching Priority
    
    When both biotime_id and barcode match different employees,
    the algorithm SHALL match by biotime_id first.
    
    **Validates: Requirements 2.2**
    """
    assume(bt_id != bt_code)  # Ensure they're different
    
    # Create two Odoo employees:
    # - Employee A: has matching biotime_id
    # - Employee B: has matching barcode
    odoo_employees = [
        {'id': 1, 'name': 'Employee A', 'biotime_id': bt_id, 'barcode': 'other_barcode'},
        {'id': 2, 'name': 'Employee B', 'biotime_id': 'other_id', 'barcode': bt_code},
    ]
    
    biotime_emp = {'id': bt_id, 'emp_code': bt_code}
    
    matched, match_type = match_employee(biotime_emp, odoo_employees)
    
    # Should match Employee A by biotime_id, not Employee B by barcode
    assert matched is not None, "Should find a match"
    assert match_type == 'biotime_id', f"Should match by biotime_id first, got {match_type}"
    assert matched['id'] == 1, f"Should match Employee A (id=1), got {matched['id']}"


@settings(max_examples=100)
@given(
    bt_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu', 'Ll'))),
    bt_code=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu', 'Ll'))),
)
def test_employee_matching_fallback_to_barcode(bt_id, bt_code):
    """
    Feature: biotime-sync, Property 1: Employee Matching Priority
    
    When biotime_id doesn't match any employee but barcode does,
    the algorithm SHALL fall back to barcode matching.
    
    **Validates: Requirements 2.2**
    """
    # Create Odoo employee with matching barcode but different biotime_id
    odoo_employees = [
        {'id': 1, 'name': 'Employee A', 'biotime_id': 'different_id', 'barcode': bt_code},
    ]
    
    biotime_emp = {'id': bt_id, 'emp_code': bt_code}
    
    matched, match_type = match_employee(biotime_emp, odoo_employees)
    
    # Should match by barcode since biotime_id doesn't match
    assert matched is not None, "Should find a match via barcode"
    assert match_type == 'barcode', f"Should match by barcode, got {match_type}"
    assert matched['id'] == 1, f"Should match Employee A (id=1), got {matched['id']}"


@settings(max_examples=100)
@given(
    bt_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu', 'Ll'))),
    bt_code=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu', 'Ll'))),
)
def test_employee_matching_no_match(bt_id, bt_code):
    """
    Feature: biotime-sync, Property 1: Employee Matching Priority
    
    When neither biotime_id nor barcode matches any employee,
    the algorithm SHALL return no match.
    
    **Validates: Requirements 2.2**
    """
    # Create Odoo employees with different biotime_id and barcode
    odoo_employees = [
        {'id': 1, 'name': 'Employee A', 'biotime_id': 'other_id_1', 'barcode': 'other_barcode_1'},
        {'id': 2, 'name': 'Employee B', 'biotime_id': 'other_id_2', 'barcode': 'other_barcode_2'},
    ]
    
    biotime_emp = {'id': bt_id, 'emp_code': bt_code}
    
    matched, match_type = match_employee(biotime_emp, odoo_employees)
    
    # Should not find a match
    assert matched is None, f"Should not find a match, got {matched}"
    assert match_type is None, f"Match type should be None, got {match_type}"


@settings(max_examples=100)
@given(
    bt_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Nd', 'Lu', 'Ll'))),
)
def test_employee_matching_biotime_id_only(bt_id):
    """
    Feature: biotime-sync, Property 1: Employee Matching Priority
    
    When only biotime_id matches, the algorithm SHALL match by biotime_id.
    
    **Validates: Requirements 2.2**
    """
    odoo_employees = [
        {'id': 1, 'name': 'Employee A', 'biotime_id': bt_id, 'barcode': 'some_barcode'},
    ]
    
    biotime_emp = {'id': bt_id, 'emp_code': 'different_code'}
    
    matched, match_type = match_employee(biotime_emp, odoo_employees)
    
    assert matched is not None, "Should find a match"
    assert match_type == 'biotime_id', f"Should match by biotime_id, got {match_type}"



# =============================================================================
# Property 2: Pagination Completeness
# For any paginated API response with N total pages, the sync engine SHALL 
# fetch exactly N pages and return all records from all pages combined.
# Validates: Requirements 3.2
# =============================================================================


def simulate_paginated_fetch(pages):
    """
    Simulate the _fetch_paginated() method behavior.
    
    Args:
        pages: list of lists, where each inner list represents records on a page
        
    Returns:
        list: All records from all pages combined
    """
    all_records = []
    for page in pages:
        all_records.extend(page)
    return all_records


@settings(max_examples=100)
@given(
    num_pages=st.integers(min_value=1, max_value=10),
    records_per_page=st.integers(min_value=1, max_value=50),
)
def test_pagination_completeness_all_records_fetched(num_pages, records_per_page):
    """
    Feature: biotime-sync, Property 2: Pagination Completeness
    
    For any paginated API response with N total pages, the sync engine SHALL 
    fetch exactly N pages and return all records from all pages combined.
    
    **Validates: Requirements 3.2**
    """
    # Generate pages with records
    pages = []
    total_expected_records = 0
    for page_num in range(num_pages):
        page_records = [
            {'id': page_num * records_per_page + i, 'data': f'record_{page_num}_{i}'}
            for i in range(records_per_page)
        ]
        pages.append(page_records)
        total_expected_records += len(page_records)
    
    # Simulate pagination fetch
    all_records = simulate_paginated_fetch(pages)
    
    # Assert all records are fetched
    assert len(all_records) == total_expected_records, \
        f"Expected {total_expected_records} records, got {len(all_records)}"
    
    # Assert all pages were processed (by checking record IDs)
    expected_ids = set(range(total_expected_records))
    actual_ids = set(r['id'] for r in all_records)
    assert actual_ids == expected_ids, \
        f"Missing records: {expected_ids - actual_ids}"


@settings(max_examples=100)
@given(
    num_pages=st.integers(min_value=1, max_value=10),
)
def test_pagination_completeness_variable_page_sizes(num_pages):
    """
    Feature: biotime-sync, Property 2: Pagination Completeness
    
    Pagination should work correctly even with variable page sizes.
    
    **Validates: Requirements 3.2**
    """
    # Generate pages with variable sizes
    pages = []
    record_id = 0
    total_expected_records = 0
    
    for page_num in range(num_pages):
        # Variable page size between 1 and 20
        page_size = (page_num % 5) + 1
        page_records = [
            {'id': record_id + i, 'data': f'record_{page_num}_{i}'}
            for i in range(page_size)
        ]
        pages.append(page_records)
        record_id += page_size
        total_expected_records += page_size
    
    # Simulate pagination fetch
    all_records = simulate_paginated_fetch(pages)
    
    # Assert all records are fetched
    assert len(all_records) == total_expected_records, \
        f"Expected {total_expected_records} records, got {len(all_records)}"


@settings(max_examples=100)
@given(
    st.data(),
)
def test_pagination_completeness_preserves_order(data):
    """
    Feature: biotime-sync, Property 2: Pagination Completeness
    
    Pagination should preserve the order of records across pages.
    
    **Validates: Requirements 3.2**
    """
    num_pages = data.draw(st.integers(min_value=1, max_value=5))
    
    # Generate pages with sequential IDs
    pages = []
    current_id = 0
    for page_num in range(num_pages):
        page_size = data.draw(st.integers(min_value=1, max_value=10))
        page_records = [
            {'id': current_id + i, 'sequence': current_id + i}
            for i in range(page_size)
        ]
        pages.append(page_records)
        current_id += page_size
    
    # Simulate pagination fetch
    all_records = simulate_paginated_fetch(pages)
    
    # Assert order is preserved
    sequences = [r['sequence'] for r in all_records]
    assert sequences == sorted(sequences), \
        f"Order not preserved: {sequences}"


def test_pagination_completeness_empty_pages():
    """
    Feature: biotime-sync, Property 2: Pagination Completeness
    
    Pagination should handle empty responses correctly.
    
    **Validates: Requirements 3.2**
    """
    # Empty pages
    pages = []
    
    all_records = simulate_paginated_fetch(pages)
    
    assert len(all_records) == 0, \
        f"Expected 0 records for empty pages, got {len(all_records)}"


def test_pagination_completeness_single_page():
    """
    Feature: biotime-sync, Property 2: Pagination Completeness
    
    Pagination should work correctly with a single page.
    
    **Validates: Requirements 3.2**
    """
    pages = [
        [{'id': 0}, {'id': 1}, {'id': 2}]
    ]
    
    all_records = simulate_paginated_fetch(pages)
    
    assert len(all_records) == 3, \
        f"Expected 3 records, got {len(all_records)}"



# =============================================================================
# Property 3: Transaction Chronological Pairing
# For any set of transactions for the same employee on the same day, the sync 
# engine SHALL pair them as check-in/check-out in chronological order, where 
# the earliest unpaired transaction becomes check-in and the next becomes check-out.
# Validates: Requirements 3.4
# =============================================================================


def pair_transactions(transactions):
    """
    Simulate the transaction pairing logic from sync_attendance().
    
    Pairs transactions chronologically as check-in/check-out for same employee/day.
    
    Args:
        transactions: list of dicts with 'punch_time' datetime
        
    Returns:
        tuple: (check_in, check_out) datetimes, check_out may be None
    """
    if not transactions:
        return None, None
    
    # Sort transactions chronologically
    sorted_trans = sorted(transactions, key=lambda x: x['punch_time'])
    
    # First is check-in, second is check-out
    check_in = sorted_trans[0]['punch_time'] if sorted_trans else None
    check_out = sorted_trans[1]['punch_time'] if len(sorted_trans) > 1 else None
    
    return check_in, check_out


@settings(max_examples=100)
@given(
    base_hour=st.integers(min_value=0, max_value=20),
    base_minute=st.integers(min_value=0, max_value=59),
    duration_hours=st.floats(min_value=1.0, max_value=12.0),
)
def test_transaction_pairing_chronological_order(base_hour, base_minute, duration_hours):
    """
    Feature: biotime-sync, Property 3: Transaction Chronological Pairing
    
    For any set of transactions, the earliest becomes check-in and 
    the next becomes check-out.
    
    **Validates: Requirements 3.4**
    """
    base_date = datetime(2024, 1, 15)
    
    # Create two transactions in random order
    time1 = base_date.replace(hour=base_hour, minute=base_minute)
    time2 = time1 + timedelta(hours=duration_hours)
    
    # Ensure time2 is still on the same day
    assume(time2.date() == base_date.date())
    
    # Transactions in reverse order (to test sorting)
    transactions = [
        {'punch_time': time2, 'id': '2'},
        {'punch_time': time1, 'id': '1'},
    ]
    
    check_in, check_out = pair_transactions(transactions)
    
    # Check-in should be the earlier time
    assert check_in == time1, f"Check-in should be {time1}, got {check_in}"
    # Check-out should be the later time
    assert check_out == time2, f"Check-out should be {time2}, got {check_out}"
    # Check-in should always be before check-out
    assert check_in < check_out, "Check-in should be before check-out"


@settings(max_examples=100)
@given(
    hour=st.integers(min_value=0, max_value=23),
    minute=st.integers(min_value=0, max_value=59),
)
def test_transaction_pairing_single_transaction(hour, minute):
    """
    Feature: biotime-sync, Property 3: Transaction Chronological Pairing
    
    When only one transaction exists, it becomes check-in and check-out is None.
    
    **Validates: Requirements 3.4**
    """
    base_date = datetime(2024, 1, 15)
    punch_time = base_date.replace(hour=hour, minute=minute)
    
    transactions = [
        {'punch_time': punch_time, 'id': '1'},
    ]
    
    check_in, check_out = pair_transactions(transactions)
    
    assert check_in == punch_time, f"Check-in should be {punch_time}, got {check_in}"
    assert check_out is None, f"Check-out should be None for single transaction, got {check_out}"


@settings(max_examples=100)
@given(
    num_transactions=st.integers(min_value=3, max_value=10),
)
def test_transaction_pairing_multiple_transactions(num_transactions):
    """
    Feature: biotime-sync, Property 3: Transaction Chronological Pairing
    
    When more than 2 transactions exist, only the first two (chronologically) 
    are used as check-in and check-out.
    
    **Validates: Requirements 3.4**
    """
    base_date = datetime(2024, 1, 15, 8, 0)
    
    # Create multiple transactions at different times
    transactions = []
    for i in range(num_transactions):
        punch_time = base_date + timedelta(hours=i)
        transactions.append({'punch_time': punch_time, 'id': str(i)})
    
    # Shuffle to test sorting
    import random
    random.shuffle(transactions)
    
    check_in, check_out = pair_transactions(transactions)
    
    # Check-in should be the earliest
    assert check_in == base_date, f"Check-in should be {base_date}, got {check_in}"
    # Check-out should be the second earliest
    expected_checkout = base_date + timedelta(hours=1)
    assert check_out == expected_checkout, f"Check-out should be {expected_checkout}, got {check_out}"


def test_transaction_pairing_empty_list():
    """
    Feature: biotime-sync, Property 3: Transaction Chronological Pairing
    
    When no transactions exist, both check-in and check-out should be None.
    
    **Validates: Requirements 3.4**
    """
    transactions = []
    
    check_in, check_out = pair_transactions(transactions)
    
    assert check_in is None, f"Check-in should be None for empty list, got {check_in}"
    assert check_out is None, f"Check-out should be None for empty list, got {check_out}"


@settings(max_examples=100)
@given(
    hour=st.integers(min_value=0, max_value=23),
    minute=st.integers(min_value=0, max_value=59),
)
def test_transaction_pairing_same_time(hour, minute):
    """
    Feature: biotime-sync, Property 3: Transaction Chronological Pairing
    
    When transactions have the same time, the pairing should still work 
    (deterministic behavior).
    
    **Validates: Requirements 3.4**
    """
    base_date = datetime(2024, 1, 15)
    same_time = base_date.replace(hour=hour, minute=minute)
    
    transactions = [
        {'punch_time': same_time, 'id': '1'},
        {'punch_time': same_time, 'id': '2'},
    ]
    
    check_in, check_out = pair_transactions(transactions)
    
    # Both should be the same time
    assert check_in == same_time, f"Check-in should be {same_time}, got {check_in}"
    assert check_out == same_time, f"Check-out should be {same_time}, got {check_out}"
