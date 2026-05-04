# notifications_panel.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QTextBrowser, QSplitter, QGroupBox, QComboBox,
    QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotificationItem(QListWidgetItem):
    """Custom list item for notifications"""
    
    def __init__(self, notification_data, parent=None):
        super().__init__(parent)
        self.notification_data = notification_data
        
        # Set display text
        title = notification_data['title']
        created = datetime.fromisoformat(notification_data['created_date'])
        time_str = created.strftime('%m/%d %H:%M')
        
        self.setText(f"{title}\n{time_str} • {notification_data['case_number']}")
        
        # Set background color for unread
        if not notification_data['read']:
            self.setBackground(QColor(240, 248, 255))  # Light blue for unread
        
        # Store notification ID
        self.setData(Qt.UserRole, notification_data['id'])


class NotificationsPanel(QDialog):
    """Dialog for viewing and managing notifications"""
    
    def __init__(self, notification_manager, parent=None):
        super().__init__(parent)
        self.notification_manager = notification_manager
        self.main_window = parent
        self.setWindowTitle("Notifications")
        self.setMinimumSize(900, 650)
        self.setup_ui()
        self.load_notifications()
    
    def setup_ui(self):
        """Setup the notifications panel UI"""
        layout = QVBoxLayout(self)
        
        # Header with filters
        header_layout = QHBoxLayout()
        
        header_layout.addWidget(QLabel("Filter:"))
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Unread", "Critical", "Warning", "Info", 
                                    "Legal", "Court Dates", "Evidence"])
        self.filter_combo.currentTextChanged.connect(self.load_notifications)
        header_layout.addWidget(self.filter_combo)
        
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_notifications)
        header_layout.addWidget(self.refresh_btn)
        
        self.mark_all_read_btn = QPushButton("Mark All as Read")
        self.mark_all_read_btn.clicked.connect(self.mark_all_as_read)
        header_layout.addWidget(self.mark_all_read_btn)
        
        self.dismiss_all_btn = QPushButton("Dismiss All")
        self.dismiss_all_btn.clicked.connect(self.dismiss_all)
        header_layout.addWidget(self.dismiss_all_btn)
        
        layout.addLayout(header_layout)
        
        # Main content area - split view
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Notification list
        list_widget_container = QGroupBox("Notifications")
        list_layout = QVBoxLayout()
        
        self.notification_list = QListWidget()
        self.notification_list.itemClicked.connect(self.on_notification_selected)
        list_layout.addWidget(self.notification_list)
        
        # Count label
        self.count_label = QLabel("0 notifications")
        self.count_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        list_layout.addWidget(self.count_label)
        
        list_widget_container.setLayout(list_layout)
        splitter.addWidget(list_widget_container)
        
        # Right: Notification details
        detail_widget_container = QGroupBox("Details")
        detail_layout = QVBoxLayout()
        
        self.detail_title = QLabel("Select a notification to view details")
        self.detail_title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        self.detail_title.setWordWrap(True)
        detail_layout.addWidget(self.detail_title)
        
        self.detail_meta = QLabel()
        self.detail_meta.setStyleSheet("color: #666; font-size: 11px; padding: 5px 10px;")
        detail_layout.addWidget(self.detail_meta)
        
        self.detail_message = QTextBrowser()
        self.detail_message.setOpenExternalLinks(False)
        self.detail_message.setStyleSheet("padding: 10px;")
        detail_layout.addWidget(self.detail_message)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.open_case_btn = QPushButton("📂 Open Case")
        self.open_case_btn.clicked.connect(self.open_case)
        action_layout.addWidget(self.open_case_btn)
        
        action_layout.addStretch()
        
        self.mark_read_btn = QPushButton("✓ Mark as Read")
        self.mark_read_btn.clicked.connect(self.mark_as_read)
        action_layout.addWidget(self.mark_read_btn)
        
        self.dismiss_btn = QPushButton("✕ Dismiss")
        self.dismiss_btn.clicked.connect(self.dismiss_notification)
        action_layout.addWidget(self.dismiss_btn)
        
        detail_layout.addLayout(action_layout)
        
        detail_widget_container.setLayout(detail_layout)
        splitter.addWidget(detail_widget_container)
        
        splitter.setSizes([450, 450])
        layout.addWidget(splitter)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
        
        # Initially disable detail buttons
        self.open_case_btn.setEnabled(False)
        self.mark_read_btn.setEnabled(False)
        self.dismiss_btn.setEnabled(False)
    
    def load_notifications(self):
        """Load notifications based on current filter"""
        self.notification_list.clear()
        
        filter_text = self.filter_combo.currentText()
        
        if filter_text == "Unread":
            notifications = self.notification_manager.get_unread_notifications()
        else:
            notifications = self.notification_manager.get_all_notifications()
            
            # Apply additional filters
            if filter_text == "Critical":
                notifications = [n for n in notifications if n['severity'] == 'critical']
            elif filter_text == "Warning":
                notifications = [n for n in notifications if n['severity'] == 'warning']
            elif filter_text == "Info":
                notifications = [n for n in notifications if n['severity'] == 'info']
            elif filter_text == "Legal":
                notifications = [n for n in notifications if n['notification_type'] == 'legal']
            elif filter_text == "Court Dates":
                notifications = [n for n in notifications if n['notification_type'] == 'court_date']
            elif filter_text == "Evidence":
                notifications = [n for n in notifications if n['notification_type'] == 'evidence']
        
        # Add items to list
        for notification in notifications:
            item = NotificationItem(notification)
            self.notification_list.addItem(item)
        
        # Update count label
        unread_count = sum(1 for n in notifications if not n['read'])
        if unread_count > 0:
            self.count_label.setText(f"{len(notifications)} notification(s) - {unread_count} unread")
        else:
            self.count_label.setText(f"{len(notifications)} notification(s)")
        
        logger.info(f"Loaded {len(notifications)} notifications with filter: {filter_text}")
    
    def on_notification_selected(self, item: NotificationItem):
        """Handle notification selection"""
        notification = item.notification_data
        
        # Update detail view
        self.detail_title.setText(notification['title'])
        
        created = datetime.fromisoformat(notification['created_date'])
        severity_emoji = {'critical': '🔴', 'warning': '🟡', 'info': '🔵'}.get(notification['severity'], '🔵')
        
        meta_text = f"{severity_emoji} {notification['severity'].upper()} • {created.strftime('%Y-%m-%d %H:%M:%S')}"
        meta_text += f"\nCase: {notification['case_number']}"
        meta_text += f"\nType: {notification['notification_type'].replace('_', ' ').title()}"
        
        if notification['notification_subtype']:
            meta_text += f" - {notification['notification_subtype'].replace('_', ' ').title()}"
        
        self.detail_meta.setText(meta_text)
        self.detail_message.setPlainText(notification['message'])
        
        # Enable action buttons
        self.open_case_btn.setEnabled(True)
        self.mark_read_btn.setEnabled(not notification['read'])
        self.dismiss_btn.setEnabled(True)
        
        # Mark as read if unread
        if not notification['read']:
            self.notification_manager.mark_as_read(notification['id'])
            item.notification_data['read'] = 1
            item.setBackground(QColor(255, 255, 255))
            
            # Update count label
            self.load_notifications()
    
    def mark_as_read(self):
        """Mark current notification as read"""
        current_item = self.notification_list.currentItem()
        if current_item and isinstance(current_item, NotificationItem):
            notification_id = current_item.data(Qt.UserRole)
            self.notification_manager.mark_as_read(notification_id)
            self.mark_read_btn.setEnabled(False)
            current_item.setBackground(QColor(255, 255, 255))
            logger.info(f"Marked notification {notification_id} as read")
    
    def dismiss_notification(self):
        """Dismiss current notification"""
        current_item = self.notification_list.currentItem()
        if current_item and isinstance(current_item, NotificationItem):
            notification_id = current_item.data(Qt.UserRole)
            self.notification_manager.dismiss_notification(notification_id)
            self.load_notifications()
            logger.info(f"Dismissed notification {notification_id}")
            
            # Clear detail view
            self.detail_title.setText("Select a notification to view details")
            self.detail_meta.setText("")
            self.detail_message.clear()
            self.open_case_btn.setEnabled(False)
            self.mark_read_btn.setEnabled(False)
            self.dismiss_btn.setEnabled(False)
    
    def mark_all_as_read(self):
        """Mark all visible notifications as read"""
        marked_count = 0
        for i in range(self.notification_list.count()):
            item = self.notification_list.item(i)
            if isinstance(item, NotificationItem) and not item.notification_data['read']:
                notification_id = item.notification_data['id']
                self.notification_manager.mark_as_read(notification_id)
                marked_count += 1
        
        if marked_count > 0:
            logger.info(f"Marked {marked_count} notifications as read")
        
        self.load_notifications()
    
    def dismiss_all(self):
        """Dismiss all notifications"""
        reply = QMessageBox.question(
            self, 
            "Dismiss All",
            "Are you sure you want to dismiss all notifications?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.notification_manager.dismiss_all()
            self.load_notifications()
            logger.info("Dismissed all notifications")
            
            # Clear detail view
            self.detail_title.setText("Select a notification to view details")
            self.detail_meta.setText("")
            self.detail_message.clear()
            self.open_case_btn.setEnabled(False)
            self.mark_read_btn.setEnabled(False)
            self.dismiss_btn.setEnabled(False)
    
    def open_case(self):
        """Open the case associated with current notification"""
        current_item = self.notification_list.currentItem()
        if current_item and isinstance(current_item, NotificationItem):
            case_number = current_item.notification_data['case_number']
            
            # Try to open the case in the main window
            if self.main_window and hasattr(self.main_window, 'load_case_from_dashboard'):
                logger.info(f"Opening case {case_number} from notification")
                self.close()  # Close notification panel
                try:
                    # Create a mock event to trigger case loading
                    class MockIndex:
                        def __init__(self, case_number):
                            self._case_number = case_number
                        
                        def data(self, role):
                            if role == Qt.DisplayRole:
                                return self._case_number
                            return None
                    
                    mock_index = MockIndex(case_number)
                    self.main_window.load_case_from_dashboard(mock_index)
                except Exception as e:
                    logger.error(f"Error opening case {case_number}: {e}")
                    QMessageBox.warning(
                        self,
                        "Cannot Open Case",
                        f"Unable to open case {case_number}. Please open it manually from the dashboard."
                    )
            else:
                QMessageBox.information(
                    self,
                    "Case Information",
                    f"Case Number: {case_number}\n\nPlease open this case from the main dashboard."
                )
