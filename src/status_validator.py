# status_validator.py
# State machine validation for status transitions
"""
Provides validation for status transitions across the forensic case management system.
Ensures that status changes follow valid workflows and prevents invalid state transitions.
"""

import logging
from typing import Optional, Dict, List, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class StatusTransitionError(Exception):
    """Raised when an invalid status transition is attempted"""
    pass


class StatusValidator:
    """Validates status transitions using state machine rules"""
    
    # Define valid transitions for each status type
    CASE_STATUS_TRANSITIONS: Dict[str, Set[str]] = {
        'draft': {'submitted', 'closed'},  # Can submit or close draft
        'submitted': {'approved', 'revisions_needed', 'draft'},  # Under review
        'approved': {'completed', 'revisions_needed'},  # Approved can be completed or sent back
        'revisions_needed': {'draft', 'submitted'},  # Return to editing or resubmit
        'completed': set(),  # Terminal state - no transitions allowed
        'closed': set()  # Terminal state
    }
    
    EVIDENCE_STATUS_TRANSITIONS: Dict[str, Set[str]] = {
        'not_imaged': {'imaged', 'analyzed', 'other'},
        'imaged': {'analyzed', 'not_imaged'},  # Can go back if re-imaging needed
        'analyzed': {'imaged'},  # Can revert if analysis needs to be redone
        'other': {'not_imaged', 'imaged', 'analyzed'}
    }
    
    LEGAL_STATUS_TRANSITIONS: Dict[str, Set[str]] = {
        'pending': {'in_progress', 'completed', 'no_longer_needed', 'cancelled'},
        'in_progress': {'completed', 'pending', 'no_longer_needed', 'cancelled'},
        'completed': set(),  # Terminal state
        'no_longer_needed': set(),  # Terminal state
        'cancelled': set()  # Terminal state
    }
    
    @classmethod
    def validate_case_status_transition(cls, current_status: Optional[str], 
                                       new_status: str) -> bool:
        """
        Validate a case status transition.
        
        Args:
            current_status: Current status (None for new cases)
            new_status: Proposed new status
            
        Returns:
            True if transition is valid
            
        Raises:
            StatusTransitionError: If transition is invalid
        """
        # New cases can start as draft
        if current_status is None:
            if new_status in ['draft', 'submitted']:
                return True
            raise StatusTransitionError(
                f"New cases must start as 'draft' or 'submitted', not '{new_status}'"
            )
        
        # Normalize statuses
        current_status = current_status.lower()
        new_status = new_status.lower()
        
        # Allow same-status transitions (no-op)
        if current_status == new_status:
            return True
        
        # Check if current status is known
        if current_status not in cls.CASE_STATUS_TRANSITIONS:
            logger.warning(f"Unknown current status: {current_status}")
            return True  # Allow transition from unknown status
        
        # Check if transition is valid
        valid_transitions = cls.CASE_STATUS_TRANSITIONS[current_status]
        
        if new_status not in valid_transitions:
            raise StatusTransitionError(
                f"Invalid case status transition from '{current_status}' to '{new_status}'. "
                f"Valid transitions: {', '.join(valid_transitions) if valid_transitions else 'none (terminal state)'}"
            )
        
        logger.info(f"Valid case status transition: {current_status} → {new_status}")
        return True
    
    @classmethod
    def validate_evidence_status_transition(cls, current_status: Optional[str],
                                           new_status: str) -> bool:
        """
        Validate an evidence status transition.
        
        Args:
            current_status: Current status (None for new evidence)
            new_status: Proposed new status
            
        Returns:
            True if transition is valid
            
        Raises:
            StatusTransitionError: If transition is invalid
        """
        # New evidence items start as not_imaged
        if current_status is None:
            if new_status in ['not_imaged', 'other']:
                return True
            raise StatusTransitionError(
                f"New evidence must start as 'not_imaged' or 'other', not '{new_status}'"
            )
        
        # Normalize statuses
        current_status = current_status.lower()
        new_status = new_status.lower()
        
        # Allow same-status transitions (no-op)
        if current_status == new_status:
            return True
        
        # Check if current status is known
        if current_status not in cls.EVIDENCE_STATUS_TRANSITIONS:
            logger.warning(f"Unknown current evidence status: {current_status}")
            return True  # Allow transition from unknown status
        
        # Check if transition is valid
        valid_transitions = cls.EVIDENCE_STATUS_TRANSITIONS[current_status]
        
        if new_status not in valid_transitions:
            raise StatusTransitionError(
                f"Invalid evidence status transition from '{current_status}' to '{new_status}'. "
                f"Valid transitions: {', '.join(valid_transitions)}"
            )
        
        logger.info(f"Valid evidence status transition: {current_status} → {new_status}")
        return True
    
    @classmethod
    def validate_legal_status_transition(cls, current_status: Optional[str],
                                        new_status: str) -> bool:
        """
        Validate a legal process status transition.
        
        Args:
            current_status: Current status (None for new legal process)
            new_status: Proposed new status
            
        Returns:
            True if transition is valid
            
        Raises:
            StatusTransitionError: If transition is invalid
        """
        # New legal processes start as pending
        if current_status is None:
            if new_status in ['pending', 'in_progress']:
                return True
            raise StatusTransitionError(
                f"New legal processes must start as 'pending' or 'in_progress', not '{new_status}'"
            )
        
        # Normalize statuses
        current_status = current_status.lower()
        new_status = new_status.lower()
        
        # Allow same-status transitions (no-op)
        if current_status == new_status:
            return True
        
        # Check if current status is known
        if current_status not in cls.LEGAL_STATUS_TRANSITIONS:
            logger.warning(f"Unknown current legal status: {current_status}")
            return True  # Allow transition from unknown status
        
        # Check if transition is valid
        valid_transitions = cls.LEGAL_STATUS_TRANSITIONS[current_status]
        
        if new_status not in valid_transitions:
            raise StatusTransitionError(
                f"Invalid legal status transition from '{current_status}' to '{new_status}'. "
                f"Valid transitions: {', '.join(valid_transitions) if valid_transitions else 'none (terminal state)'}"
            )
        
        logger.info(f"Valid legal status transition: {current_status} → {new_status}")
        return True
    
    @classmethod
    def get_valid_case_transitions(cls, current_status: str) -> List[str]:
        """Get list of valid case status transitions from current state"""
        current_status = current_status.lower() if current_status else 'draft'
        return list(cls.CASE_STATUS_TRANSITIONS.get(current_status, set()))
    
    @classmethod
    def get_valid_evidence_transitions(cls, current_status: str) -> List[str]:
        """Get list of valid evidence status transitions from current state"""
        current_status = current_status.lower() if current_status else 'not_imaged'
        return list(cls.EVIDENCE_STATUS_TRANSITIONS.get(current_status, set()))
    
    @classmethod
    def get_valid_legal_transitions(cls, current_status: str) -> List[str]:
        """Get list of valid legal status transitions from current state"""
        current_status = current_status.lower() if current_status else 'pending'
        return list(cls.LEGAL_STATUS_TRANSITIONS.get(current_status, set()))
    
    @classmethod
    def is_terminal_state(cls, status: str, status_type: str = 'case') -> bool:
        """
        Check if a status is a terminal state (no further transitions allowed).
        
        Args:
            status: Status to check
            status_type: Type of status ('case', 'evidence', or 'legal')
            
        Returns:
            True if status is terminal
        """
        status = status.lower()
        
        if status_type == 'case':
            transitions = cls.CASE_STATUS_TRANSITIONS.get(status, set())
        elif status_type == 'evidence':
            transitions = cls.EVIDENCE_STATUS_TRANSITIONS.get(status, set())
        elif status_type == 'legal':
            transitions = cls.LEGAL_STATUS_TRANSITIONS.get(status, set())
        else:
            raise ValueError(f"Unknown status type: {status_type}")
        
        return len(transitions) == 0
