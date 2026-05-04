"""application/interfaces/i_note_service.py - Notes service contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class INoteService(ABC):

    # ------------------------------------------------------------------ #
    # CRUD (original)                                                      #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def create_note(self, dto) -> object:
        """Create a new note. Returns NoteDto."""

    @abstractmethod
    def update_note(self, dto) -> object:
        """Update an existing note. Returns NoteDto."""

    @abstractmethod
    def delete_note(self, note_id: str, deleted_by: str) -> None:
        """Delete a note by identifier."""

    @abstractmethod
    def get_note(self, note_id: str) -> Optional[object]:
        """Return NoteDto or None."""

    @abstractmethod
    def get_notes_for_case(self, case_number: str) -> List[object]:
        """Return active note list for a case."""

    @abstractmethod
    def search_notes(self, query: str, case_number: Optional[str] = None) -> List[object]:
        """Search notes globally or for one case."""

    @abstractmethod
    def insert_note_into_report(self, note_id: str, report_id: int, inserted_by: str) -> None:
        """Insert note content into a report body with audit event."""

    # ------------------------------------------------------------------ #
    # Archive / restore                                                    #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def archive_note(self, note_id: str, archived_by: str) -> object:
        """Archive a note. Returns updated NoteDto."""

    @abstractmethod
    def restore_note(self, note_id: str, restored_by: str) -> object:
        """Restore an archived note to active. Returns updated NoteDto."""

    @abstractmethod
    def get_archived_notes(self, case_number: str) -> List[object]:
        """Return all archived notes for a case."""

    # ------------------------------------------------------------------ #
    # Approval workflow                                                    #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def submit_for_approval(self, note_id: str, submitted_by: str) -> object:
        """Submit a note for peer approval. Returns updated NoteDto."""

    @abstractmethod
    def approve_note(self, note_id: str, approved_by: str, comments: Optional[str] = None) -> object:
        """Approve a pending note. Returns updated NoteDto."""

    @abstractmethod
    def reject_note(self, note_id: str, rejected_by: str, reason: str) -> object:
        """Reject a pending note. Returns updated NoteDto."""

    @abstractmethod
    def get_pending_approval(self, case_number: str) -> List[object]:
        """Return notes in pending_approval status for a case."""

    # ------------------------------------------------------------------ #
    # Tag management                                                       #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def add_tag(self, note_id: str, tag_name: str, added_by: str) -> object:
        """Add a tag to a note. Returns updated NoteDto."""

    @abstractmethod
    def remove_tag(self, note_id: str, tag_name: str, removed_by: str) -> object:
        """Remove a tag from a note. Returns updated NoteDto."""

    @abstractmethod
    def get_notes_by_tag(self, case_number: str, tag_name: str) -> List[object]:
        """Return notes carrying the given tag for a case."""

    @abstractmethod
    def get_available_tags(self, case_number: str) -> List[str]:
        """Return sorted unique tags used across all notes for a case."""

    # ------------------------------------------------------------------ #
    # Filtering                                                            #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def get_notes_by_type(self, case_number: str, note_type: str) -> List[object]:
        """Return notes of a specific type for a case."""

    @abstractmethod
    def get_notes_by_priority(self, case_number: str, priority: str) -> List[object]:
        """Return notes of a specific priority for a case."""

    # ------------------------------------------------------------------ #
    # Task management                                                      #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def get_pending_tasks(self, case_number: str) -> List[object]:
        """Return task-notes that are not completed for the case."""

    @abstractmethod
    def get_completed_tasks(self, case_number: str) -> List[object]:
        """Return task-notes completed for the case."""

    @abstractmethod
    def complete_task(self, note_id: str, completed_by: str) -> object:
        """Mark a task-note as completed. Returns updated NoteDto."""

    @abstractmethod
    def reopen_task(self, note_id: str, reopened_by: str) -> object:
        """Reopen a completed task-note. Returns updated NoteDto."""

    @abstractmethod
    def reassign_task(self, note_id: str, assigned_to: str, reassigned_by: str) -> object:
        """Reassign task-note ownership. Returns updated NoteDto."""

    @abstractmethod
    def get_tasks_assigned_to(self, case_number: str, username: str) -> List[object]:
        """Return task-notes assigned to the specified user for a case."""

    @abstractmethod
    def get_overdue_tasks(self, case_number: str) -> List[object]:
        """Return pending task-notes whose due timestamp is before now."""

    # ------------------------------------------------------------------ #
    # Attachments                                                         #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def add_attachment(
        self,
        note_id: str,
        file_path: str,
        file_name: str,
        mime_type: str,
        added_by: str,
    ) -> dict:
        """Attach a file reference to a note and return attachment metadata."""

    @abstractmethod
    def remove_attachment(self, note_id: str, attachment_id: str, removed_by: str) -> None:
        """Remove a file attachment from a note by attachment identifier."""

    @abstractmethod
    def get_attachments(self, note_id: str) -> List[dict]:
        """Return all attachment metadata records for a note."""

    # ------------------------------------------------------------------ #
    # Entity linking                                                      #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def add_link(
        self,
        note_id: str,
        target_type: str,
        target_id: str,
        label: str,
        linked_by: str,
    ) -> dict:
        """Create a typed link from a note to another entity and return link metadata."""

    @abstractmethod
    def remove_link(self, note_id: str, link_id: str, removed_by: str) -> None:
        """Remove a link from a note by link identifier."""

    @abstractmethod
    def get_links(self, note_id: str) -> List[dict]:
        """Return all typed links for a note."""

    @abstractmethod
    def get_notes_linking_to(self, case_number: str, target_type: str, target_id: str) -> List[object]:
        """Return notes in a case that link to the specified target entity."""

    # ------------------------------------------------------------------ #
    # Redaction / visibility / sharing                                    #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def redact_note(self, note_id: str, reason: str, redacted_by: str) -> object:
        """Redact sensitive note body content while retaining reversible metadata."""

    @abstractmethod
    def unredact_note(self, note_id: str, unredacted_by: str) -> object:
        """Restore previously redacted note content."""

    @abstractmethod
    def share_note(self, note_id: str, usernames: List[str], shared_by: str) -> object:
        """Grant note access to one or more usernames."""

    @abstractmethod
    def unshare_note(self, note_id: str, usernames: List[str], unshared_by: str) -> object:
        """Revoke note access for one or more usernames."""

    @abstractmethod
    def change_visibility(self, note_id: str, visibility: str, changed_by: str) -> object:
        """Change note visibility scope (private/team/case_level/public)."""

    # ------------------------------------------------------------------ #
    # Timeline / metrics / exports                                        #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def generate_timeline(self, case_number: str) -> List[dict]:
        """Generate a chronologically sorted timeline from case note activity."""

    @abstractmethod
    def get_activity_metrics(self, case_number: str) -> dict:
        """Return activity metrics (created/updated counts and most active user)."""

    @abstractmethod
    def export_to_pdf(self, case_number: str, output_path: str) -> str:
        """Export case notes to PDF-like output and return output_path."""

    @abstractmethod
    def export_to_docx(self, case_number: str, output_path: str) -> str:
        """Export case notes to DOCX-like output and return output_path."""

    @abstractmethod
    def export_timeline(self, case_number: str, output_path: str) -> str:
        """Export generated timeline to file and return output_path."""

    # ------------------------------------------------------------------ #
    # Statistics                                                           #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def get_statistics(self, case_number: str) -> object:
        """Return NoteStatisticsDto with counts by status, type, and priority."""

    # ------------------------------------------------------------------ #
    # Geocoding                                                            #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def forward_geocode(self, address: str) -> dict:
        """Geocode an address string to lat/lon. Returns dict with lat, lon, display_name."""

    @abstractmethod
    def reverse_geocode(self, lat: float, lon: float) -> str:
        """Reverse geocode a coordinate pair to a human-readable address string."""

    @abstractmethod
    def extract_locations(self, note_id: str) -> List[dict]:
        """Parse note body for location strings and return list of {text, lat, lon} dicts."""

    # ------------------------------------------------------------------ #
    # Voice Transcription                                                  #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def create_from_voice_transcription(
        self,
        case_number: str,
        audio_path: str,
        created_by: str,
        title: Optional[str] = None,
    ) -> object:
        """Create a note from a voice recording file. Returns NoteDto."""

    @abstractmethod
    def get_voice_transcription_confidence(self, note_id: str) -> Optional[float]:
        """Return the stored transcription confidence score (0.0–1.0) for a note, or None."""

    # ------------------------------------------------------------------ #
    # NLP Entity Extraction                                                #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def extract_entities(self, note_id: str) -> dict:
        """
        Extract named entities from a note's body.
        Returns dict with keys: people, places, evidence_refs, dates, organisations.
        """

    # ------------------------------------------------------------------ #
    # Export                                                               #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def export_to_csv(self, case_number: str) -> str:
        """Return all notes for a case as a CSV string."""

