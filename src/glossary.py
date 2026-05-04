# glossary.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QMessageBox

GLOSSARY = {
    "Acquisition": "The process of collecting digital evidence from a source, such as a hard drive, mobile device, or network, while preserving its integrity.",
    "Allocation Unit": "The smallest amount of disk space that can be allocated to hold a file or a portion of a file.",
    "Artifact": "Any item of evidence that is relevant to an investigation, including digital files, metadata, or system logs.",
    "Authentication": "The process of verifying the identity of a user, device, or system.",
    "Bitstream Image": "An exact duplicate of a digital storage device created by copying data at the bit level.",
    "Chain of Custody": "The chronological documentation or paper trail that records the sequence of custody, control, transfer, analysis, and disposition of physical or electronic evidence.",
    "Cloud Computing": "A model for enabling ubiquitous, convenient, on-demand network access to a shared pool of configurable computing resources.",
    "Computer Forensics": "The application of investigation and analysis techniques to gather and preserve evidence from a particular computing device in a way that is suitable for presentation in a court of law.",
    "Data Carving": "The process of extracting files or data from a larger data set without the assistance of file system metadata.",
    "Data Recovery": "The process of retrieving data from damaged, failed, corrupted, or inaccessible storage media.",
    "Digital Evidence": "Information stored or transmitted in binary form that may be relied on in court.",
    "Digital Forensics": "The use of scientifically derived and proven methods toward the preservation, collection, validation, identification, analysis, interpretation, documentation, and presentation of digital evidence.",
    "Encryption": "The process of converting plaintext into ciphertext to prevent unauthorized access.",
    "Evidence Integrity": "The assurance that digital evidence has not been altered or tampered with.",
    "File Allocation Table (FAT)": "A file system used by various operating systems to organize and manage files on a disk.",
    "File Carving": "A data recovery technique used to extract files from a data stream by identifying file headers and footers.",
    "File Signature": "A unique sequence of bytes at the beginning of a file that identifies the file type.",
    "File System": "A method used by operating systems to organize and store files on a storage device.",
    "Forensic Copy": "An exact duplicate of digital evidence that preserves the original data and metadata.",
    "Forensic Image": "A bit-for-bit copy of a digital storage device or media.",
    "Hash Value": "A fixed-size string of characters that uniquely identifies a piece of data, often used to verify data integrity.",
    "HDD (Hard Disk Drive)": "A non-volatile storage device that stores data on rotating magnetic disks.",
    "Hex Editor": "A tool used to view and edit binary files in hexadecimal format.",
    "Image Analysis": "The examination of digital images to extract information such as metadata, compression artifacts, or hidden data.",
    "Information Assurance": "The practice of managing risks related to the use, processing, storage, and transmission of information.",
    "Internet of Things (IoT)": "A network of physical devices, vehicles, home appliances, and other items embedded with electronics, software, sensors, and connectivity.",
    "Log Analysis": "The process of examining log files to identify security incidents, policy violations, or operational issues.",
    "Malware": "Software designed to disrupt, damage, or gain unauthorized access to computer systems.",
    "Master Boot Record (MBR)": "The first sector of a hard disk that contains the boot loader and partition table.",
    "Metadata": "Data that provides information about other data, such as file creation date, author, or location.",
    "Mobile Device Forensics": "The science of recovering digital evidence from mobile devices such as smartphones and tablets.",
    "Network Forensics": "The investigation of network traffic and communications to identify security incidents or criminal activity.",
    "Partition": "A division of a hard disk into separate areas that can be formatted and used as separate drives.",
    "Password Cracking": "The process of recovering passwords from data that has been stored or transmitted in a cryptographically secure manner.",
    "RAM (Random Access Memory)": "A type of computer memory that can be accessed randomly, used for temporary storage of data.",
    "Registry Analysis": "The examination of the Windows registry to extract information about system configuration, user activity, and installed software.",
    "Rootkit": "A set of software tools that enable an unauthorized user to gain administrator-level access to a computer system.",
    "Sector": "The smallest unit of storage on a hard disk, typically 512 bytes.",
    "Slack Space": "The unused space at the end of a cluster that is not occupied by file data.",
    "SSD (Solid State Drive)": "A storage device that uses integrated circuit assemblies to store data persistently.",
    "Stealth Mode": "A technique used by malware to hide its presence from antivirus software and system administrators.",
    "Steganography": "The practice of concealing messages or information within other non-secret text or data.",
    "Timeline Analysis": "The process of creating a chronological sequence of events based on digital evidence.",
    "Unallocated Space": "Disk space that is not currently assigned to any file or directory.",
    "USB Forensics": "The investigation of USB devices to recover data and analyze usage patterns.",
    "Virtual Machine": "A software emulation of a computer system that runs on a host computer.",
    "Volatile Memory": "Computer memory that requires power to maintain stored information, such as RAM.",
    "Web Browser Forensics": "The analysis of web browser artifacts to reconstruct user activity and browsing history.",
    "Wi-Fi Forensics": "The investigation of wireless network communications and access points.",
    "Windows Registry": "A hierarchical database that stores configuration settings and options for the Windows operating system.",
    "Write Blocker": "A hardware device that prevents write operations to a storage device, used to preserve evidence integrity."
}

class GlossaryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SWGDE Glossary Search")
        self.setMinimumSize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search term (case-insensitive)...")
        self.search_input.textChanged.connect(self.filter_terms)
        layout.addWidget(self.search_input)

        self.results_list = QListWidget()
        layout.addWidget(self.results_list)

        self.all_terms = sorted(GLOSSARY.keys(), key=str.lower)
        self.update_list(self.all_terms)

        self.results_list.itemClicked.connect(self.show_definition)

    def update_list(self, terms):
        self.results_list.clear()
        for term in terms:
            self.results_list.addItem(term)

    def filter_terms(self):
        query = self.search_input.text().lower()
        if not query:
            self.update_list(self.all_terms)
            return
        # Search in both term names and definitions
        matched = []
        for term in self.all_terms:
            if query in term.lower() or query in GLOSSARY[term].lower():
                matched.append(term)
        self.update_list(matched)

    def show_definition(self, item):
        term = item.text()
        definition = GLOSSARY.get(term, "Not found.")
        QMessageBox.information(self, term, definition)