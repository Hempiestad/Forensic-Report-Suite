#!/usr/bin/env python3
"""
Quick test script for archive system functionality
Tests archive workflow: archive case -> view archived -> restore
"""

import sys
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_archive_database_methods():
    """Test that archive methods work correctly"""
    from database import DatabaseManager
    
    db = DatabaseManager()
    logger.info("✓ Database connected")
    
    # Get a closed case to test with
    cases = db.get_cases_with_details()
    closed_cases = [c for c in cases if c['status'] == 'Closed']
    
    if not closed_cases:
        logger.warning("⚠ No closed cases available for testing")
        logger.info("Creating a test case...")
        # Would need to create a test case here
        return False
    
    test_case = closed_cases[0]
    case_number = test_case['id']
    logger.info(f"✓ Found test case: {case_number} (Status: {test_case['status']})")
    
    # Test 1: Archive the case
    logger.info("Testing: Archive case...")
    archive_date = datetime.now() + timedelta(days=30)
    success = db.archive_case(
        case_number,
        "test_user",
        "Testing archive functionality",
        archive_date
    )
    
    if success:
        logger.info(f"✓ Case {case_number} archived successfully")
    else:
        logger.error(f"✗ Failed to archive case {case_number}")
        return False
    
    # Test 2: Check archive status
    logger.info("Testing: Check archive status...")
    is_archived = db.is_case_archived(case_number)
    if is_archived:
        logger.info(f"✓ Case {case_number} confirmed as archived")
    else:
        logger.error(f"✗ Case {case_number} not marked as archived")
        return False
    
    # Test 3: Get archived cases list
    logger.info("Testing: Get archived cases...")
    archived_cases = db.get_archived_cases()
    matching_case = next((c for c in archived_cases if c['case_number'] == case_number), None)
    if matching_case:
        logger.info(f"✓ Found {case_number} in archived cases list")
        logger.info(f"  - Archived by: {matching_case.get('archived_by')}")
        logger.info(f"  - Archive reason: {matching_case.get('archive_reason')}")
    else:
        logger.error(f"✗ Case {case_number} not found in archived cases")
        return False
    
    # Test 4: Verify archived case not in active dashboard
    logger.info("Testing: Archived case excluded from active dashboard...")
    active_cases = db.get_cases_with_details(include_archived=False)
    active_case = next((c for c in active_cases if c['id'] == case_number), None)
    if active_case is None:
        logger.info(f"✓ Case {case_number} correctly excluded from active dashboard")
    else:
        logger.error(f"✗ Case {case_number} still appears in active dashboard")
        return False
    
    # Test 5: Restore the case
    logger.info("Testing: Restore archived case...")
    success = db.restore_case(case_number, "test_user")
    if success:
        logger.info(f"✓ Case {case_number} restored successfully")
    else:
        logger.error(f"✗ Failed to restore case {case_number}")
        return False
    
    # Test 6: Verify restored case is active again
    logger.info("Testing: Verify case is active again...")
    is_archived = db.is_case_archived(case_number)
    if not is_archived:
        logger.info(f"✓ Case {case_number} confirmed as active (not archived)")
    else:
        logger.error(f"✗ Case {case_number} still marked as archived after restore")
        return False
    
    # Test 7: Verify restored case appears in active dashboard
    logger.info("Testing: Verify restored case appears in dashboard...")
    active_cases = db.get_cases_with_details(include_archived=False)
    active_case = next((c for c in active_cases if c['id'] == case_number), None)
    if active_case is not None:
        logger.info(f"✓ Case {case_number} now appears in active dashboard")
    else:
        logger.error(f"✗ Case {case_number} not found in active dashboard after restore")
        return False
    
    logger.info("\n" + "="*60)
    logger.info("✅ All archive system tests PASSED!")
    logger.info("="*60)
    return True


def test_archive_filters():
    """Test archive filtering functionality"""
    from database import DatabaseManager
    
    logger.info("\n" + "="*60)
    logger.info("Testing Archive Filters...")
    logger.info("="*60)
    
    db = DatabaseManager()
    
    # Test filtering by year
    logger.info("\nTesting: Filter archived cases by year...")
    current_year = str(datetime.now().year)
    archived_this_year = db.get_archived_cases({'year': current_year})
    logger.info(f"✓ Found {len(archived_this_year)} archived cases in {current_year}")
    
    # Test filtering by user
    logger.info("Testing: Filter archived cases by user...")
    archived_by_user = db.get_archived_cases({'assigned_to': 'test_user'})
    logger.info(f"✓ Found {len(archived_by_user)} archived cases assigned to test_user")
    
    # Test search functionality
    logger.info("Testing: Search archived cases...")
    search_results = db.get_archived_cases({'search_term': 'test'})
    logger.info(f"✓ Search found {len(search_results)} matching archived cases")
    
    logger.info("\n" + "="*60)
    logger.info("✅ Archive filter tests completed!")
    logger.info("="*60)


if __name__ == "__main__":
    try:
        logger.info("Starting Archive System Tests\n")
        
        # Run main tests
        if test_archive_database_methods():
            # Run filter tests
            test_archive_filters()
            sys.exit(0)
        else:
            logger.error("\n❌ Tests FAILED!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        sys.exit(1)
