# Legal Workflow UI Dialogs — FuDog Labs Forensic Report Suite

## Overview

The Python application now includes comprehensive **UI dialogs for managing the legal process approval workflow**. These dialogs make it easy for forensic investigators and supervisors to track each stage of the legal approval process directly from the application interface.

## Accessing the Workflow Dialogs

All workflow dialogs are accessible from the **Tracker → ⚖️ Legal Workflow** menu in the main application window.

### Prerequisites
1. Have a case tab open (select case from dashboard)
2. Have a legal process created in that case (Tracker → Add Legal Process)
3. Select the legal process when prompted

---

## Workflow Stages & Dialogs

### 1️⃣ Investigator Approval

**Menu:** Tracker → ⚖️ Legal Workflow → Mark Investigator Approved

**Purpose:** Record when the investigator has reviewed and approved the legal process

**Fields:**
- **Investigator Name** (required): Name of the investigator approving
  - Example: "Det. John Smith"
- **Approval Date** (required): Date of investigator approval
  - Defaults to today, can be changed via calendar picker
- **Notes** (optional): Additional details about the approval
  - Special conditions, signature method, etc.

**Output:**
- ✓ Green calendar event on the approval date
- Notification created
- Database updated with investigator_approved_date and investigator_name

**Example:**
```
Investigator Name: Det. Sarah Johnson
Approval Date: 2026-02-10
Notes: Reviewed evidence, search warrant procedure verified
```

---

### 2️⃣ State Attorney Approval

**Menu:** Tracker → ⚖️ Legal Workflow → Mark State Attorney Approved

**Purpose:** Record when the state attorney has reviewed and approved the legal process

**Fields:**
- **Attorney Name** (required): Name of the state attorney
  - Example: "ADA Robert Martinez"
- **Approval Date** (required): Date of attorney approval
  - Defaults to today
- **Notes** (optional): Office location, conditions, etc.

**Output:**
- Cyan calendar event on the approval date
- Notification created
- Database updated with state_attorney_approved_date and state_attorney_name

**Example:**
```
Attorney Name: ADA Michelle Chen
Approval Date: 2026-02-13
Notes: State Attorney's Office, Criminal Division
```

---

### 3️⃣ Judicial Approval

**Menu:** Tracker → ⚖️ Legal Workflow → Mark Judicial Approval

**Purpose:** Record when a judge has signed/approved the legal process (e.g., search warrant signed)

**Fields:**
- **Court Name** (required): Name of the court
  - Example: "Circuit Court", "Federal District Court"
- **Judge Name** (required): Name of the judge (with title)
  - Example: "Hon. Patricia Montgomery"
- **Signature Date** (required): Date judge signed the order
  - Defaults to today
- **Notes** (optional): Order number, conditions, limitations

**Output:**
- Purple calendar event on the signature date
- Notification created
- Database updated with judicial_approval_date, court_name, and judge_name

**Example:**
```
Court Name: Circuit Court, Miami-Dade County
Judge Name: Hon. Alexander Graham
Signature Date: 2026-02-14
Notes: Order #2024-CV-12345, Valid for 10 days from issue date
```

---

### 4️⃣ Send to Provider (⏱️ SLA CLOCK STARTS HERE)

**Menu:** Tracker → ⚖️ Legal Workflow → Send to Provider (⏱️ SLA Starts)

**Purpose:** Record when the legal document is transmitted to the service provider (e.g., Google, Meta, etc.)

⚠️ **CRITICAL:** This is when the SLA (Service Level Agreement) clock officially starts!

**Fields:**
- **Transmission Method** (required): How the document was sent
  - Law Enforcement Portal
  - Certified Mail
  - Email (with Read Receipt)
  - In-person Delivery
  - Other
  
- **Date Sent** (required): Actual date of transmission
  - Defaults to today
  
- **Expected Response Time** (required): Number of days provider has to respond
  - Default: 45 days (typical for legal holds)
  - Range: 1-180 days
  - Accepts provider-specific SLA requirements
  
- **Notes** (optional): Tracking number, recipient, special instructions

**Auto-Calculated:**
- **SLA Due Date:** Automatically calculated as (Date Sent + Expected Days)
  - Displayed in the dialog for verification
  - Shows as yellow calendar event on that date

**Output:**
- Orange calendar event on send date ("Sent to Provider")
- Yellow calendar event on SLA due date ("SLA Due")
- Two notifications created (one for send, one for due date)
- Database updated with:
  - sent_to_provider_date
  - transmission_method
  - expected_response_days
  - sla_due_date (auto-calculated)

**Example:**
```
Transmission Method: Law Enforcement Portal
Date Sent: 2026-02-14
Expected Response Time: 45 days
SLA Due Date: 2026-03-31 (calculated)
Notes: Tracking ID: LEP-2026-0045, Recipient: Legal Compliance Team
```

---

### 5️⃣ Provider Acknowledged

**Menu:** Tracker → ⚖️ Legal Workflow → Provider Acknowledged

**Purpose:** Record when the provider has confirmed receipt of the legal document

**Fields:**
- **Date Acknowledged** (required): When provider confirmed receipt
  - Defaults to today
  - Can be different from send date
  
- **Notes** (optional): Confirmation number, contact person, details

**Output:**
- Blue calendar event on acknowledgment date
- Notification created
- Database updated with provider_acknowledged_date

**Example:**
```
Date Acknowledged: 2026-02-15
Notes: Confirmation #GP-2026-789456, Contact: John Willis (john.willis@provider.com)
```

---

### 🚨 Record SLA Breach

**Menu:** Tracker → ⚖️ Legal Workflow → Record SLA Breach

**Purpose:** Record when the provider's response is received AFTER the SLA due date

⚠️ **CRITICAL ALERT:** SLA breaches indicate the service provider failed to meet the agreement!

**Fields:**
- **Response Received Date** (required): Date the provider's response was received
  - Defaults to today
  - Must be AFTER the SLA due date to be a breach
  
- **Days Late** (auto-calculated): Shows how many days late the response is
  - Updated in real-time as you change the date
  - Positive = late by N days
  - Negative = early by N days
  
- **Breach Reason** (optional): Document why the provider missed the SLA
  - System outages, high volume request, technical issues, etc.

**Output:**
- Red calendar event on breach date ("SLA Breach")
- **Critical notification** marked in red
- Database updated with:
  - sla_breach = 1
  - days_late = (received_date - sla_due_date).days
  - breach_reason

**Example:**
```
Response Received Date: 2026-04-06
Days Late: 6 days
Breach Reason: Provider reported systems issue delayed data compilation. 
              Requested expedited processing for ongoing investigation.
```

---

## Workflow Flow Diagram

```
Investigation Starts
        ↓
1. Investigator Approves (Green Dot)
        ↓
2. State Attorney Approves (Cyan Dot)
        ↓
3. Judge Signs (Purple Dot)
        ↓
4. Send to Provider (Orange Dot) ⏱️ SLA CLOCK STARTS
        ↓
5. Provider Acknowledges (Blue Dot)
        ↓
⏳ Wait for Response (SLA Due Date = Yellow Dot)
        ↓
    Response Received
        ├─ On/Before Due Date → ✓ SLA MET
        └─ After Due Date → 🚨 SLA BREACH (Red Dot)
```

---

## Calendar Color Legend

When you open **Tools → Case Calendar**, you'll see colored dots for legal workflow events:

| Color | Event | Stage |
|-------|-------|-------|
| 🟢 Green | Investigator Approved | Stage 1 |
| 🔵 Cyan | State Attorney Approved | Stage 2 |
| 🟣 Purple | Judicial Approval | Stage 3 |
| 🟠 Orange | Sent to Provider | Stage 4 (SLA Starts) |
| 🔷 Blue | Provider Acknowledged | Optional |
| 🟡 Yellow | SLA Due Date | Deadline |
| 🔴 Red | SLA Breach | Overdue Response |

---

## Important SLA Timing Notes

### ✓ When SLA Clock STARTS
The SLA clock starts when you use **"Send to Provider"** dialog.

**Key Point:** The SLA timer begins from the transmission date, NOT from when the legal document was created or approved. This ensures accurate SLA tracking independent of internal approval delays.

### ⏱️ How Due Date is Calculated

```
SLA Due Date = Send Date + Expected Response Days

Example:
  Send Date: 2026-02-14
  Expected Days: 45
  Due Date: 2026-03-31
```

### 🚨 When Breach is Recorded

A breach is recorded when the provider's response is received **AFTER** the SLA due date.

```
SLA Met: Response received on or before 2026-03-31
SLA Breach: Response received on 2026-04-01 or later
```

---

## Workflow Best Practices

### 📋 Required Order
Complete stages in order: Investigator → Attorney → Judge → Provider

### ⏱️ Timing
- Most internal approvals: 1-10 business days
- Send to provider: Same day or next business day after judge approval
- Expected response times vary:
  - Google Legal Holds: 15-30 days typically
  - Meta/Facebook: 30-45 days typical
  - Check provider's specific SLA terms

### 📝 Documentation
Use the **Notes** field in each dialog to record:
- Contact people and phone numbers
- Confirmation numbers and tracking IDs
- Any special conditions or expedited requests
- Reasons for delays or breaches

### 🔔 Notifications
Each stage creates:
1. A **calendar event** (colored dot on calendar)
2. A **notification** (in Notifications panel)
3. A **database entry** (audit trail)

Check **Tools → View Notifications** to see all pending SLA events.

---

## Troubleshooting

### "No Legal Processes Found"
- Create a legal process first: **Tracker → Add Legal Process**
- Make sure you have a case tab open

### "Multiple Processes" Dialog Appears
- The case has more than one legal process
- Select the specific process you want to update
- Common when tracking multiple simultaneous legal holds (e.g., Subpoena A and Subpoena B)

### SLA Due Date Seems Wrong
- Verify the "Expected Response Days" you entered
- Check that "Date Sent" is correct
- Due Date = Sent Date + Expected Days

### Can't Record SLA Breach
- The response date must be AFTER the SLA due date
- If the date you entered is on or before due date, you won't see a breach warning
- Check your calendar on Tools → Case Calendar for the due date

---

## Integration with Dashboard

After updating any workflow stage:
1. Calendar events automatically appear (colors vary by stage)
2. Dashboard refreshes with latest status
3. Notifications show in Notifications panel
4. Audit log records all changes

---

## Quick Reference

| Action | Menu Path | Shortcut | Calendar Color |
|--------|-----------|----------|-----------------|
| Investigator Approval | Tracker → ⚖️ → 1️⃣ | None | 🟢 Green |
| State Attorney | Tracker → ⚖️ → 2️⃣ | None | 🔵 Cyan |
| Judge Approval | Tracker → ⚖️ → 3️⃣ | None | 🟣 Purple |
| Send to Provider | Tracker → ⚖️ → 4️⃣ | None | 🟠 Orange |
| Provider Ack | Tracker → ⚖️ → 5️⃣ | None | 🔷 Blue |
| Record Breach | Tracker → ⚖️ → 🚨 | None | 🔴 Red |

---

## Related Documentation

- [README](README.md) — Project overview and quick start
- [Legal Process Approval Workflow](LEGAL_WORKFLOW_GUIDE.md) — Python helper functions and SLA reference
- [Main Application User Guide](MAIN_USER_GUIDE.md) — Dashboard, menus, and case management
- [Server User Guide](SERVER_USER_GUIDE.md) — Server API and legal endpoint documentation

