# notification_manager.py
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon

logger = logging.getLogger(__name__)


class NotificationManager(QObject):
    """Manages notifications for legal processes, court dates, and evidence"""
    
    # Signals
    notification_created = pyqtSignal(dict)  # Emitted when new notification is created
    notification_read = pyqtSignal(int)      # Emitted when notification is read
    notification_dismissed = pyqtSignal(int) # Emitted when notification is dismissed
    badge_count_changed = pyqtSignal(int)    # Emitted when unread count changes
    
    def __init__(self, db_manager, config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.config = config.get('notifications', {})
        self.enabled = self.config.get('enabled', True)
        
        # Store reference for status change notifications
        self.db.notification_manager = self
        
        # Notification checking timer
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_notifications)
        
        # System tray icon (optional)
        self.tray_icon = None
        if self.config.get('show_system_tray', False):
            self.setup_system_tray(parent)
        
        # Start checking timer
        if self.enabled:
            interval = self.config.get('check_interval_seconds', 300) * 1000  # Convert to ms
            self.check_timer.start(interval)
            logger.info(f"Notification checker started with {interval/1000}s interval")
            # Run an immediate first check instead of waiting for the first interval
            self.check_notifications()
    
    def setup_system_tray(self, main_window):
        """Setup system tray icon with notification badge"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available")
            return
        
        try:
            # Try to use application icon
            self.tray_icon = QSystemTrayIcon(main_window.windowIcon(), main_window)
        except Exception as e:
            logger.warning(f"Failed to create tray icon with main window icon: {e}")
            self.tray_icon = QSystemTrayIcon(main_window)
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_notifications_action = QAction("Show Notifications", main_window)
        show_notifications_action.triggered.connect(lambda: self.show_notifications_panel(main_window))
        tray_menu.addAction(show_notifications_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", main_window)
        quit_action.triggered.connect(main_window.close)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Connect double-click to show notifications
        self.tray_icon.activated.connect(
            lambda reason: self.show_notifications_panel(main_window) 
            if reason == QSystemTrayIcon.DoubleClick else None
        )
        
        logger.info("System tray icon initialized")
    
    def check_notifications(self):
        """Main notification checking routine - runs periodically"""
        if not self.enabled:
            return
        
        try:
            current_time = datetime.now()
            
            # Check legal process notifications
            if self.config.get('legal_notifications', {}).get('enabled', True):
                self._check_legal_notifications(current_time)
            
            # Check court date notifications
            if self.config.get('court_date_notifications', {}).get('enabled', True):
                self._check_court_date_notifications(current_time)
            
            # Update badge count
            self._update_badge_count()
            
        except Exception as e:
            logger.error(f"Error checking notifications: {e}", exc_info=True)
    
    def _check_legal_notifications(self, current_time: datetime):
        """Check for legal process notifications"""
        legal_config = self.config.get('legal_notifications', {})
        
        # Get all active legal processes
        cursor = self.db.conn.execute('''
            SELECT id, case_number, process_type, provider, status, 
                   due_date, expiration_date, submission_date
            FROM legal_processes 
            WHERE status NOT IN ('completed', 'no_longer_needed')
        ''')
        
        for row in cursor.fetchall():
            process_id = row['id']
            case_number = row['case_number']
            process_type = row['process_type']
            status = row['status']
            
            # Check due date warnings
            if row['due_date'] and legal_config.get('due_date_warning_days'):
                try:
                    due_date = datetime.fromisoformat(row['due_date'])
                    days_until_due = (due_date - current_time).days
                    
                    warning_days = legal_config['due_date_warning_days']
                    
                    # Check if we should create a warning
                    for warning_day in warning_days:
                        if days_until_due == warning_day:
                            # Check if notification already exists
                            if not self._notification_exists(
                                case_number, 'legal', 'due_date', process_id, 
                                current_time.date().isoformat()
                            ):
                                self.create_notification(
                                    case_number=case_number,
                                    notification_type='legal',
                                    notification_subtype='due_date',
                                    related_id=process_id,
                                    title=f"Legal Process Due Soon",
                                    message=f"{process_type.replace('_', ' ').title()} for case {case_number} due in {warning_day} day(s)",
                                    severity='warning' if warning_day <= 3 else 'info',
                                    trigger_date=current_time.date().isoformat()
                                )
                    
                    # Check overdue
                    if days_until_due < 0 and legal_config.get('overdue_alert', True):
                        if not self._notification_exists(
                            case_number, 'legal', 'overdue', process_id, 
                            current_time.date().isoformat()
                        ):
                            self.create_notification(
                                case_number=case_number,
                                notification_type='legal',
                                notification_subtype='overdue',
                                related_id=process_id,
                                title=f"Legal Process OVERDUE",
                                message=f"{process_type.replace('_', ' ').title()} for case {case_number} is {abs(days_until_due)} day(s) overdue",
                                severity='critical',
                                trigger_date=current_time.date().isoformat()
                            )
                except ValueError as e:
                    logger.warning(f"Invalid due_date format for legal process {process_id}: {e}")
            
            # Check expiration warnings (for preservation letters, warrants)
            if row['expiration_date'] and legal_config.get('expiration_warning_days'):
                try:
                    expiration_date = datetime.fromisoformat(row['expiration_date'])
                    days_until_expiration = (expiration_date - current_time).days
                    
                    warning_days = legal_config['expiration_warning_days']
                    
                    for warning_day in warning_days:
                        if days_until_expiration == warning_day:
                            if not self._notification_exists(
                                case_number, 'legal', 'expiration', process_id, 
                                current_time.date().isoformat()
                            ):
                                severity = 'critical' if warning_day <= 7 else 'warning'
                                self.create_notification(
                                    case_number=case_number,
                                    notification_type='legal',
                                    notification_subtype='expiration',
                                    related_id=process_id,
                                    title=f"{process_type.replace('_', ' ').title()} Expiring Soon",
                                    message=f"{process_type.replace('_', ' ').title()} for case {case_number} expires in {warning_day} day(s)",
                                    severity=severity,
                                    trigger_date=current_time.date().isoformat()
                                )
                except ValueError as e:
                    logger.warning(f"Invalid expiration_date format for legal process {process_id}: {e}")
    
    def _check_court_date_notifications(self, current_time: datetime):
        """Check for court date notifications"""
        court_config = self.config.get('court_date_notifications', {})
        
        # Get all upcoming court dates
        cursor = self.db.conn.execute('''
            SELECT id, case_number, date_type, court_date, event_time, location, notes
            FROM court_dates 
            WHERE court_date >= date('now')
            ORDER BY court_date ASC
        ''')
        
        for row in cursor.fetchall():
            court_id = row['id']
            case_number = row['case_number']
            date_type = row['date_type']
            
            try:
                court_date = datetime.fromisoformat(row['court_date'])
                days_until = (court_date - current_time).days
                
                # Check advance warnings
                if court_config.get('advance_warning_days'):
                    warning_days = court_config['advance_warning_days']
                    
                    for warning_day in warning_days:
                        if days_until == warning_day:
                            if not self._notification_exists(
                                case_number, 'court_date', 'upcoming', court_id, 
                                current_time.date().isoformat()
                            ):
                                severity = 'critical' if warning_day <= 1 else 'warning'
                                time_str = f" at {row['event_time']}" if row['event_time'] else ""
                                location_str = f" - {row['location']}" if row['location'] else ""
                                
                                self.create_notification(
                                    case_number=case_number,
                                    notification_type='court_date',
                                    notification_subtype='upcoming',
                                    related_id=court_id,
                                    title=f"Court Date in {warning_day} Day(s)",
                                    message=f"{date_type.replace('_', ' ').title()} for case {case_number} on {court_date.strftime('%Y-%m-%d')}{time_str}{location_str}",
                                    severity=severity,
                                    trigger_date=current_time.date().isoformat()
                                )
                
                # Same day reminder
                if days_until == 0 and court_config.get('same_day_reminder', True):
                    reminder_time = court_config.get('same_day_reminder_time', '08:00')
                    reminder_hour, reminder_minute = map(int, reminder_time.split(':'))
                    
                    # Only trigger if we're past the reminder time and haven't sent today
                    if current_time.hour >= reminder_hour and current_time.minute >= reminder_minute:
                        if not self._notification_exists(
                            case_number, 'court_date', 'same_day', court_id, 
                            current_time.date().isoformat()
                        ):
                            time_str = f" at {row['event_time']}" if row['event_time'] else ""
                            location_str = f" at {row['location']}" if row['location'] else ""
                            
                            self.create_notification(
                                case_number=case_number,
                                notification_type='court_date',
                                notification_subtype='same_day',
                                related_id=court_id,
                                title=f"⚠️ COURT DATE TODAY",
                                message=f"{date_type.replace('_', ' ').title()} for case {case_number}{time_str}{location_str}",
                                severity='critical',
                                trigger_date=current_time.date().isoformat()
                            )
            except ValueError as e:
                logger.warning(f"Invalid court_date format for court date {court_id}: {e}")
    
    def create_notification(
        self, 
        case_number: str, 
        notification_type: str,
        notification_subtype: str,
        related_id: Optional[int],
        title: str,
        message: str,
        severity: str = 'info',
        trigger_date: Optional[str] = None
    ) -> int:
        """Create a new notification"""
        created_date = datetime.now().isoformat()
        trigger_date = trigger_date or created_date.split('T')[0]
        
        cursor = self.db.conn.execute('''
            INSERT INTO notifications 
            (case_number, notification_type, notification_subtype, related_id, 
             title, message, severity, created_date, trigger_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (case_number, notification_type, notification_subtype, related_id,
              title, message, severity, created_date, trigger_date))
        
        self.db.conn.commit()
        notification_id = cursor.lastrowid
        
        # Emit signal
        notification_data = {
            'id': notification_id,
            'case_number': case_number,
            'type': notification_type,
            'subtype': notification_subtype,
            'title': title,
            'message': message,
            'severity': severity,
            'created_date': created_date
        }
        self.notification_created.emit(notification_data)
        
        # Show popup if configured
        self._show_notification_popup(notification_data)
        
        logger.info(f"Created notification: {title} for case {case_number}")
        return notification_id
    
    def _notification_exists(
        self, 
        case_number: str, 
        notification_type: str,
        notification_subtype: str,
        related_id: int,
        trigger_date: str
    ) -> bool:
        """Check if notification already exists for today"""
        cursor = self.db.conn.execute('''
            SELECT COUNT(*) as count FROM notifications
            WHERE case_number = ? 
              AND notification_type = ?
              AND notification_subtype = ?
              AND related_id = ?
              AND trigger_date = ?
              AND dismissed = 0
        ''', (case_number, notification_type, notification_subtype, related_id, trigger_date))
        
        row = cursor.fetchone()
        return row['count'] > 0
    
    def _show_notification_popup(self, notification: Dict[str, Any]):
        """Show a popup notification (system tray or Qt notification)"""
        display_settings = self.config.get('display_settings', {})
        
        if self.tray_icon and self.tray_icon.isVisible():
            # Show system tray notification
            icon_map = {
                'critical': QSystemTrayIcon.Critical,
                'warning': QSystemTrayIcon.Warning,
                'info': QSystemTrayIcon.Information
            }
            icon = icon_map.get(notification['severity'], QSystemTrayIcon.Information)
            
            duration = display_settings.get('popup_duration_seconds', 10) * 1000
            self.tray_icon.showMessage(
                notification['title'],
                notification['message'],
                icon,
                duration
            )
    
    def get_unread_notifications(self) -> List[Dict[str, Any]]:
        """Get all unread notifications"""
        cursor = self.db.conn.execute('''
            SELECT * FROM notifications
            WHERE read = 0 AND dismissed = 0
            ORDER BY 
                CASE severity
                    WHEN 'critical' THEN 1
                    WHEN 'warning' THEN 2
                    WHEN 'info' THEN 3
                END,
                created_date DESC
        ''')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_notifications(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all notifications (for history view)"""
        cursor = self.db.conn.execute('''
            SELECT * FROM notifications
            WHERE dismissed = 0
            ORDER BY created_date DESC
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_as_read(self, notification_id: int):
        """Mark a notification as read"""
        self.db.conn.execute('''
            UPDATE notifications 
            SET read = 1, acknowledged_date = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), notification_id))
        self.db.conn.commit()
        
        self.notification_read.emit(notification_id)
        self._update_badge_count()
    
    def dismiss_notification(self, notification_id: int):
        """Dismiss a notification"""
        self.db.conn.execute('''
            UPDATE notifications 
            SET dismissed = 1, acknowledged_date = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), notification_id))
        self.db.conn.commit()
        
        self.notification_dismissed.emit(notification_id)
        self._update_badge_count()
    
    def dismiss_all(self):
        """Dismiss all notifications"""
        self.db.conn.execute('''
            UPDATE notifications 
            SET dismissed = 1, acknowledged_date = ?
            WHERE dismissed = 0
        ''', (datetime.now().isoformat(),))
        self.db.conn.commit()
        
        self._update_badge_count()
    
    def _update_badge_count(self):
        """Update unread notification count"""
        cursor = self.db.conn.execute('''
            SELECT COUNT(*) as count FROM notifications
            WHERE read = 0 AND dismissed = 0
        ''')
        
        count = cursor.fetchone()['count']
        self.badge_count_changed.emit(count)
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications"""
        cursor = self.db.conn.execute('''
            SELECT COUNT(*) as count FROM notifications
            WHERE read = 0 AND dismissed = 0
        ''')
        return cursor.fetchone()['count']
    
    def show_notifications_panel(self, main_window):
        """Show the notifications panel/dialog"""
        from notifications_panel import NotificationsPanel
        panel = NotificationsPanel(self, main_window)
        panel.exec_()
    
    def trigger_manual_check(self):
        """Manually trigger notification check"""
        logger.info("Manual notification check triggered")
        self.check_notifications()


def create_status_change_notification(
    notification_manager: NotificationManager,
    case_number: str,
    item_type: str,  # 'legal', 'evidence'
    item_id: int,
    old_status: str,
    new_status: str,
    description: str
):
    """Helper function to create status change notifications"""
    # Check if status change notifications are enabled
    if item_type == 'legal':
        if not notification_manager.config.get('legal_notifications', {}).get('status_changes', True):
            return
        
        title = "Legal Process Status Changed"
        message = f"{description} for case {case_number}: {old_status} → {new_status}"
        notification_type = 'legal'
        notification_subtype = 'status_change'
    elif item_type == 'evidence':
        if not notification_manager.config.get('evidence_notifications', {}).get('status_change_alert', True):
            return
        
        title = "Evidence Status Changed"
        message = f"{description} for case {case_number}: {old_status} → {new_status}"
        notification_type = 'evidence'
        notification_subtype = 'status_change'
    else:
        return
    
    notification_manager.create_notification(
        case_number=case_number,
        notification_type=notification_type,
        notification_subtype=notification_subtype,
        related_id=item_id,
        title=title,
        message=message,
        severity='info'
    )
