# legal_workflow_helpers.py
# Helper methods for legal process approval workflow and SLA tracking

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def mark_investigator_approved(db_manager, process_id: int, approved_date: str, investigator_name: str) -> bool:
    """Mark legal process as approved by investigator"""
    try:
        cursor = db_manager.conn.execute(
            'SELECT case_number, process_type FROM legal_processes WHERE id = ?',
            (process_id,)
        )
        row = cursor.fetchone()
        if not row:
            logger.error(f"Legal process {process_id} not found")
            return False
        
        case_number = row['case_number']
        process_type = row['process_type']
        
        with db_manager.conn:
            db_manager.conn.execute('''
                UPDATE legal_processes 
                SET investigator_approved_date = ?, investigator_name = ?,
                    status = 'in_progress'
                WHERE id = ?
            ''', (approved_date, investigator_name, process_id))
        
        # Create notification
        if hasattr(db_manager, 'notification_manager'):
            db_manager.notification_manager.create_notification(
                case_number=case_number,
                notification_type='legal',
                notification_subtype='investigator_approved',
                related_id=process_id,
                title=f"Legal Process: Investigator Approval",
                message=f"{process_type.replace('_', ' ').title()} approved by {investigator_name}",
                severity='info'
            )
        
        # Create calendar event
        db_manager.add_case_event(
            case_number=case_number,
            event_type='legal_investigator_approved',
            event_date=approved_date,
            title=f"{process_type.replace('_', ' ').title()}: Investigator Approved",
            details=f"Approved by {investigator_name}",
            related_id=process_id,
            severity='info'
        )
        
        logger.info(f"Legal process {process_id} approved by investigator {investigator_name}")
        return True
    except Exception as e:
        logger.error(f"Error marking investigator approval: {e}", exc_info=True)
        return False


def mark_state_attorney_approved(db_manager, process_id: int, approved_date: str, attorney_name: str) -> bool:
    """Mark legal process as approved by state's attorney"""
    try:
        cursor = db_manager.conn.execute(
            'SELECT case_number, process_type FROM legal_processes WHERE id = ?',
            (process_id,)
        )
        row = cursor.fetchone()
        if not row:
            logger.error(f"Legal process {process_id} not found")
            return False
        
        case_number = row['case_number']
        process_type = row['process_type']
        
        with db_manager.conn:
            db_manager.conn.execute('''
                UPDATE legal_processes 
                SET state_attorney_approved_date = ?, state_attorney_name = ?
                WHERE id = ?
            ''', (approved_date, attorney_name, process_id))
        
        # Create notification
        if hasattr(db_manager, 'notification_manager'):
            db_manager.notification_manager.create_notification(
                case_number=case_number,
                notification_type='legal',
                notification_subtype='state_attorney_approved',
                related_id=process_id,
                title=f"Legal Process: State Attorney Approval",
                message=f"{process_type.replace('_', ' ').title()} approved by State's Attorney {attorney_name}",
                severity='info'
            )
        
        # Create calendar event
        db_manager.add_case_event(
            case_number=case_number,
            event_type='legal_state_attorney_approved',
            event_date=approved_date,
            title=f"{process_type.replace('_', ' ').title()}: Attorney Approved",
            details=f"Approved by State's Attorney {attorney_name}",
            related_id=process_id,
            severity='info'
        )
        
        logger.info(f"Legal process {process_id} approved by state's attorney {attorney_name}")
        return True
    except Exception as e:
        logger.error(f"Error marking state attorney approval: {e}", exc_info=True)
        return False


def mark_judicial_approval(db_manager, process_id: int, approval_date: str, court_name: str, judge_name: str) -> bool:
    """Mark legal process as judicially approved (warrant/subpoena signed by judge)"""
    try:
        cursor = db_manager.conn.execute(
            'SELECT case_number, process_type FROM legal_processes WHERE id = ?',
            (process_id,)
        )
        row = cursor.fetchone()
        if not row:
            logger.error(f"Legal process {process_id} not found")
            return False
        
        case_number = row['case_number']
        process_type = row['process_type']
        
        with db_manager.conn:
            db_manager.conn.execute('''
                UPDATE legal_processes 
                SET judicial_approval_date = ?, court_name = ?, judge_name = ?
                WHERE id = ?
            ''', (approval_date, court_name, judge_name, process_id))
        
        # Create notification
        if hasattr(db_manager, 'notification_manager'):
            db_manager.notification_manager.create_notification(
                case_number=case_number,
                notification_type='legal',
                notification_subtype='judicial_approval',
                related_id=process_id,
                title=f"Legal Process: Judicial Approval",
                message=f"{process_type.replace('_', ' ').title()} approved by Judge {judge_name} ({court_name})",
                severity='warning'  # Important milestone
            )
        
        # Create calendar event
        db_manager.add_case_event(
            case_number=case_number,
            event_type='legal_judicial_approval',
            event_date=approval_date,
            title=f"{process_type.replace('_', ' ').title()}: Judge Signed",
            details=f"Approved by Judge {judge_name}, {court_name}",
            related_id=process_id,
            severity='warning'
        )
        
        logger.info(f"Legal process {process_id} judicially approved by Judge {judge_name}")
        return True
    except Exception as e:
        logger.error(f"Error marking judicial approval: {e}", exc_info=True)
        return False


def mark_sent_to_provider(
    db_manager, 
    process_id: int, 
    sent_date: str, 
    transmission_method: str,
    expected_response_days: Optional[int] = None
) -> bool:
    """Mark legal process as sent to provider (SLA clock starts here)"""
    try:
        cursor = db_manager.conn.execute(
            'SELECT case_number, process_type, provider, expected_response_days FROM legal_processes WHERE id = ?',
            (process_id,)
        )
        row = cursor.fetchone()
        if not row:
            logger.error(f"Legal process {process_id} not found")
            return False
        
        case_number = row['case_number']
        process_type = row['process_type']
        provider = row['provider']
        
        # Use existing expected_response_days if not provided
        response_days = expected_response_days or row['expected_response_days']
        
        # Calculate SLA due date
        sla_due_date = None
        if response_days:
            sent_dt = datetime.fromisoformat(sent_date) if 'T' in sent_date else datetime.strptime(sent_date, '%Y-%m-%d')
            due_dt = sent_dt + timedelta(days=response_days)
            sla_due_date = due_dt.strftime('%Y-%m-%d')
        
        with db_manager.conn:
            db_manager.conn.execute('''
                UPDATE legal_processes 
                SET sent_to_provider_date = ?, 
                    transmission_method = ?,
                    expected_response_days = ?,
                    sla_due_date = ?,
                    submission_date = ?,
                    status = 'in_progress'
                WHERE id = ?
            ''', (sent_date, transmission_method, response_days, sla_due_date, sent_date, process_id))
        
        # Create notification
        if hasattr(db_manager, 'notification_manager'):
            db_manager.notification_manager.create_notification(
                case_number=case_number,
                notification_type='legal',
                notification_subtype='sent_to_provider',
                related_id=process_id,
                title=f"Legal Process: Sent to Provider",
                message=f"{process_type.replace('_', ' ').title()} sent to {provider} via {transmission_method}. Due: {sla_due_date or 'Not set'}",
                severity='warning'
            )
        
        # Create calendar event for sent
        db_manager.add_case_event(
            case_number=case_number,
            event_type='legal_sent_to_provider',
            event_date=sent_date,
            title=f"{process_type.replace('_', ' ').title()}: Sent to {provider}",
            details=f"Sent via {transmission_method}. SLA: {response_days} days",
            related_id=process_id,
            severity='warning'
        )
        
        # Create calendar event for SLA due date
        if sla_due_date:
            db_manager.add_case_event(
                case_number=case_number,
                event_type='legal_sla_due',
                event_date=sla_due_date,
                title=f"{process_type.replace('_', ' ').title()}: SLA Due from {provider}",
                details=f"Provider SLA deadline ({response_days} days from {sent_date})",
                related_id=process_id,
                severity='critical'
            )
        
        logger.info(f"Legal process {process_id} sent to provider {provider} on {sent_date}")
        return True
    except Exception as e:
        logger.error(f"Error marking sent to provider: {e}", exc_info=True)
        return False


def mark_provider_acknowledged(db_manager, process_id: int, acknowledged_date: str) -> bool:
    """Mark that provider acknowledged receipt"""
    try:
        cursor = db_manager.conn.execute(
            'SELECT case_number, process_type, provider FROM legal_processes WHERE id = ?',
            (process_id,)
        )
        row = cursor.fetchone()
        if not row:
            logger.error(f"Legal process {process_id} not found")
            return False
        
        case_number = row['case_number']
        process_type = row['process_type']
        provider = row['provider']
        
        with db_manager.conn:
            db_manager.conn.execute('''
                UPDATE legal_processes 
                SET provider_acknowledged_date = ?
                WHERE id = ?
            ''', (acknowledged_date, process_id))
        
        # Create notification
        if hasattr(db_manager, 'notification_manager'):
            db_manager.notification_manager.create_notification(
                case_number=case_number,
                notification_type='legal',
                notification_subtype='provider_acknowledged',
                related_id=process_id,
                title=f"Legal Process: Provider Acknowledged",
                message=f"{provider} acknowledged receipt of {process_type.replace('_', ' ').title()}",
                severity='info'
            )
        
        # Create calendar event
        db_manager.add_case_event(
            case_number=case_number,
            event_type='legal_provider_acknowledged',
            event_date=acknowledged_date,
            title=f"{process_type.replace('_', ' ').title()}: {provider} Acknowledged",
            details=f"{provider} confirmed receipt",
            related_id=process_id,
            severity='info'
        )
        
        logger.info(f"Legal process {process_id} acknowledged by provider {provider}")
        return True
    except Exception as e:
        logger.error(f"Error marking provider acknowledgment: {e}", exc_info=True)
        return False


def calculate_legal_sla_breach(db_manager, process_id: int, received_date: str) -> bool:
    """Calculate SLA breach status when response is received"""
    try:
        cursor = db_manager.conn.execute('''
            SELECT case_number, process_type, provider, sent_to_provider_date, 
                   sla_due_date, expected_response_days
            FROM legal_processes WHERE id = ?
        ''', (process_id,))
        row = cursor.fetchone()
        
        if not row or not row['sent_to_provider_date']:
            logger.warning(f"Legal process {process_id} has no sent_to_provider_date, cannot calculate SLA")
            return False
        
        case_number = row['case_number']
        process_type = row['process_type']
        provider = row['provider']
        sent_date_str = row['sent_to_provider_date']
        sla_due_date_str = row['sla_due_date']
        
        # Parse dates
        sent_date = datetime.fromisoformat(sent_date_str) if 'T' in sent_date_str else datetime.strptime(sent_date_str, '%Y-%m-%d')
        received_dt = datetime.fromisoformat(received_date) if 'T' in received_date else datetime.strptime(received_date, '%Y-%m-%d')
        
        actual_days = (received_dt - sent_date).days
        
        sla_breach = False
        days_late = 0
        
        if sla_due_date_str:
            sla_due_dt = datetime.strptime(sla_due_date_str, '%Y-%m-%d')
            if received_dt > sla_due_dt:
                sla_breach = True
                days_late = (received_dt - sla_due_dt).days
        
        with db_manager.conn:
            db_manager.conn.execute('''
                UPDATE legal_processes 
                SET sla_breach = ?, days_late = ?
                WHERE id = ?
            ''', (int(sla_breach), days_late, process_id))
        
        # Create notification and event if breached
        if sla_breach:
            if hasattr(db_manager, 'notification_manager'):
                db_manager.notification_manager.create_notification(
                    case_number=case_number,
                    notification_type='legal',
                    notification_subtype='sla_breach',
                    related_id=process_id,
                    title=f"⚠️ SLA BREACH: {provider}",
                    message=f"{provider} missed SLA for {process_type.replace('_', ' ').title()} by {days_late} days",
                    severity='critical'
                )
            
            db_manager.add_case_event(
                case_number=case_number,
                event_type='legal_sla_breach',
                event_date=received_date,
                title=f"⚠️ SLA BREACH: {provider} ({days_late}d late)",
                details=f"{provider} responded {days_late} days late for {process_type.replace('_', ' ').title()}",
                related_id=process_id,
                severity='critical'
            )
        
        logger.info(f"Legal process {process_id} SLA calculated: breach={sla_breach}, days_late={days_late}")
        return True
    except Exception as e:
        logger.error(f"Error calculating SLA breach: {e}", exc_info=True)
        return False
