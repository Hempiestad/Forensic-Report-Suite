using System;
using System.Collections.Generic;
using System.Linq;
using ForensicReportWriter.Domain.Enums;

namespace ForensicReportWriter.Domain.Entities
{
    /// <summary>
    /// Represents a user in the forensic system with role-based feature locking.
    /// Role determines which investigative and examination features are accessible:
    /// - Investigator: Full access to investigative leads, legal processes, case approvals
    /// - Examiner: Restricted to examination and report generation tasks
    /// </summary>
    public class User : IEntity
    {
        public Guid Id { get; private set; }

        /// <summary>
        /// Unique username for login and identification across audit trails.
        /// Immutable after creation to maintain audit trail consistency.
        /// </summary>
        public string Username { get; private set; }

        /// <summary>
        /// User email address - required for notifications and recovery.
        /// Must be unique within the system.
        /// </summary>
        public string Email { get; private set; }

        /// <summary>
        /// BCrypt-hashed password. Never expose the hash in APIs.
        /// </summary>
        public string PasswordHash { get; private set; }

        /// <summary>
        /// User's role that determines feature access and permissions.
        /// - Investigator: Can perform investigative operations, approve cases, manage legal processes
        /// - Examiner: Can only examine cases and generate reports
        /// Changes require audit logging and potentially action approval.
        /// </summary>
        public UserRole Role { get; private set; }

        /// <summary>
        /// Indicates whether the user account is active.
        /// Deactivated accounts cannot log in but maintain audit trail.
        /// </summary>
        public bool IsActive { get; private set; }

        /// <summary>
        /// User's full name for display and reporting purposes.
        /// </summary>
        public string FullName { get; private set; }

        /// <summary>
        /// Department or unit assignment for organizational tracking.
        /// </summary>
        public string Department { get; private set; }

        /// <summary>
        /// Title or position for context and access decisions.
        /// </summary>
        public string Title { get; private set; }

        /// <summary>
        /// Timestamp of user creation - immutable.
        /// </summary>
        public DateTime CreatedAt { get; private set; }

        /// <summary>
        /// Username of the user who created this account.
        /// </summary>
        public string CreatedBy { get; private set; }

        /// <summary>
        /// Timestamp of last modification.
        /// </summary>
        public DateTime UpdatedAt { get; private set; }

        /// <summary>
        /// Username of the user who last modified this account.
        /// </summary>
        public string UpdatedBy { get; private set; }

        /// <summary>
        /// Timestamp of the last successful login.
        /// Used to track active users and detect stale accounts.
        /// </summary>
        public DateTime? LastLoginAt { get; private set; }

        /// <summary>
        /// Timestamp of the last failed login attempt.
        /// Used for security monitoring and lockout logic.
        /// </summary>
        public DateTime? LastFailedLoginAt { get; private set; }

        /// <summary>
        /// Count of consecutive failed login attempts.
        /// Used to implement account lockout after threshold.
        /// </summary>
        public int FailedLoginAttempts { get; private set; }

        /// <summary>
        /// Whether the account is locked due to failed login attempts.
        /// Locked accounts cannot log in but can be unlocked by administrators.
        /// </summary>
        public bool IsLockedOut { get; private set; }

        /// <summary>
        /// Timestamp when the account lock expires (if locked).
        /// </summary>
        public DateTime? LockoutExpiresAt { get; private set; }

        /// <summary>
        /// Flag indicating if the user must change password on next login.
        /// Set to true when password is reset by administrator.
        /// </summary>
        public bool MustChangePasswordOnLogin { get; private set; }

        /// <summary>
        /// Timestamp of the last password change.
        /// Used for security policies like password expiration.
        /// </summary>
        public DateTime? LastPasswordChangeAt { get; private set; }

        /// <summary>
        /// Track role assignments and changes for audit purposes.
        /// </summary>
        public List<RoleAuditEntry> RoleAuditHistory { get; private set; } = new();

        // Private constructor for EF Core
        private User() { }

        /// <summary>
        /// Creates a new user account with the specified credentials and role.
        /// </summary>
        /// <param name="username">Unique username for login</param>
        /// <param name="email">User email address</param>
        /// <param name="passwordHash">BCrypt-hashed password</param>
        /// <param name="role">Initial user role</param>
        /// <param name="fullName">User's full name</param>
        /// <param name="department">User's department</param>
        /// <param name="title">User's job title</param>
        /// <param name="createdBy">Username of creator</param>
        /// <returns>New User instance</returns>
        /// <exception cref="ArgumentException">If username or email are invalid</exception>
        public static User Create(
            string username,
            string email,
            string passwordHash,
            UserRole role,
            string fullName,
            string department,
            string title,
            string createdBy)
        {
            ValidateUsername(username);
            ValidateEmail(email);

            var user = new User
            {
                Id = Guid.NewGuid(),
                Username = username,
                Email = email,
                PasswordHash = passwordHash,
                Role = role,
                FullName = fullName,
                Department = department,
                Title = title,
                IsActive = true,
                CreatedAt = DateTime.UtcNow,
                CreatedBy = createdBy,
                UpdatedAt = DateTime.UtcNow,
                UpdatedBy = createdBy,
                FailedLoginAttempts = 0,
                IsLockedOut = false,
                MustChangePasswordOnLogin = false
            };

            // Add initial role assignment to audit history
            user.RoleAuditHistory.Add(new RoleAuditEntry
            {
                Id = Guid.NewGuid(),
                UserId = user.Id,
                PreviousRole = null,
                NewRole = role,
                ChangedAt = user.CreatedAt,
                ChangedBy = createdBy,
                Reason = "Initial user creation"
            });

            return user;
        }

        /// <summary>
        /// Changes the user's role with full audit trail.
        /// This is a critical operation that should be restricted to administrators.
        /// </summary>
        /// <param name="newRole">The new role to assign</param>
        /// <param name="changedBy">Username of administrator making the change</param>
        /// <param name="reason">Reason for role change, for audit purposes</param>
        /// <exception cref="InvalidOperationException">If user is inactive</exception>
        public void ChangeRole(UserRole newRole, string changedBy, string reason)
        {
            if (!IsActive)
                throw new InvalidOperationException("Cannot change role for inactive user");

            var previousRole = Role;
            Role = newRole;
            UpdatedAt = DateTime.UtcNow;
            UpdatedBy = changedBy;

            // Record in audit history
            RoleAuditHistory.Add(new RoleAuditEntry
            {
                Id = Guid.NewGuid(),
                UserId = Id,
                PreviousRole = previousRole,
                NewRole = newRole,
                ChangedAt = UpdatedAt,
                ChangedBy = changedBy,
                Reason = reason ?? "Role reassignment"
            });
        }

        /// <summary>
        /// Updates the user's password hash and tracks the change.
        /// Should be called after verifying old password or in admin reset scenarios.
        /// </summary>
        /// <param name="newPasswordHash">New BCrypt-hashed password</param>
        /// <param name="changedBy">Username of user making the change</param>
        /// <param name="isAdminReset">True if this is an admin password reset</param>
        public void UpdatePassword(string newPasswordHash, string changedBy, bool isAdminReset = false)
        {
            PasswordHash = newPasswordHash;
            LastPasswordChangeAt = DateTime.UtcNow;
            UpdatedAt = DateTime.UtcNow;
            UpdatedBy = changedBy;

            // If admin reset, user must change password on next login
            if (isAdminReset)
                MustChangePasswordOnLogin = true;
            else
                MustChangePasswordOnLogin = false;

            FailedLoginAttempts = 0;
            IsLockedOut = false;
            LockoutExpiresAt = null;
        }

        /// <summary>
        /// Called after successful login to update tracking information.
        /// </summary>
        public void RecordSuccessfulLogin()
        {
            LastLoginAt = DateTime.UtcNow;
            FailedLoginAttempts = 0;
            IsLockedOut = false;
            LockoutExpiresAt = null;
            MustChangePasswordOnLogin = false;
        }

        /// <summary>
        /// Called after failed login attempt to track security metrics.
        /// Implements account lockout after threshold (default: 5 attempts).
        /// </summary>
        /// <param name="lockoutDurationMinutes">Duration to lock account (default: 15 minutes)</param>
        public void RecordFailedLoginAttempt(int lockoutDurationMinutes = 15)
        {
            LastFailedLoginAt = DateTime.UtcNow;
            FailedLoginAttempts++;

            if (FailedLoginAttempts >= 5)
            {
                IsLockedOut = true;
                LockoutExpiresAt = DateTime.UtcNow.AddMinutes(lockoutDurationMinutes);
            }
        }

        /// <summary>
        /// Unlocks a lockedout account (for admin use).
        /// </summary>
        /// <param name="unlockedBy">Username of administrator unlocking the account</param>
        public void UnlockAccount(string unlockedBy)
        {
            IsLockedOut = false;
            LockoutExpiresAt = null;
            FailedLoginAttempts = 0;
            UpdatedAt = DateTime.UtcNow;
            UpdatedBy = unlockedBy;
        }

        /// <summary>
        /// Deactivates a user account.
        /// Deactivated accounts cannot log in but maintain audit trail.
        /// </summary>
        /// <param name="deactivatedBy">Username of user deactivating the account</param>
        /// <param name="reason">Reason for deactivation</param>
        public void Deactivate(string deactivatedBy, string reason)
        {
            IsActive = false;
            UpdatedAt = DateTime.UtcNow;
            UpdatedBy = deactivatedBy;
        }

        /// <summary>
        /// Reactivates a deactivated user account.
        /// </summary>
        /// <param name="reactivatedBy">Username of user reactivating the account</param>
        public void Reactivate(string reactivatedBy)
        {
            IsActive = true;
            UpdatedAt = DateTime.UtcNow;
            UpdatedBy = reactivatedBy;
        }

        /// <summary>
        /// Determines if user account is currently usable.
        /// An account must be active and not locked out.
        /// </summary>
        public bool IsUsable()
        {
            if (!IsActive)
                return false;

            if (IsLockedOut && LockoutExpiresAt > DateTime.UtcNow)
                return false;

            return true;
        }

        /// <summary>
        /// Updates user contact and organizational information.
        /// </summary>
        public void UpdateContactInfo(string email, string fullName, string department, string title, string updatedBy)
        {
            ValidateEmail(email);
            Email = email;
            FullName = fullName;
            Department = department;
            Title = title;
            UpdatedAt = DateTime.UtcNow;
            UpdatedBy = updatedBy;
        }

        /// <summary>
        /// Gets a list of actions permitted for this user based on their role.
        /// Used by authorization system to make quick access decisions.
        /// </summary>
        public List<string> GetPermittedActions()
        {
            var actions = new List<string>
            {
                "ViewCases",
                "ViewReports",
                "ExportReports",
                "EditReports",
                "CreateNotes",
                "EditNotes"
            };

            // Investigator-specific permissions
            if (Role == UserRole.Investigator)
            {
                actions.AddRange(new[]
                {
                    "ManageInvestigativeLeads",
                    "ManageLegalProcesses",
                    "ApproveCases",
                    "ManagePeerReview",
                    "ViewInvestigativeReports",
                    "InitiateLegalRequest"
                });
            }

            // Examiner has limited permissions (report generation and examination)
            if (Role == UserRole.Examiner)
            {
                actions.AddRange(new[]
                {
                    "ExamineCase",
                    "GenerateExaminationReport"
                });
            }

            return actions;
        }

        /// <summary>
        /// Validates that the user has the required role for an operation.
        /// Throws exception if role requirements not met.
        /// </summary>
        /// <param name="requiredRole">The role required for the operation</param>
        /// <param name="operationName">Name of the operation for error message</param>
        /// <exception cref="UnauthorizedAccessException">If user's role doesn't match requirement</exception>
        public void EnsureRole(UserRole requiredRole, string operationName)
        {
            if (Role != requiredRole)
                throw new UnauthorizedAccessException(
                    $"User '{Username}' with role '{Role}' cannot perform '{operationName}'. " +
                    $"Required role: '{requiredRole}'");
        }

        /// <summary>
        /// Validates that user has one of the specified roles.
        /// </summary>
        public void EnsureAnyRole(IEnumerable<UserRole> allowedRoles, string operationName)
        {
            if (!allowedRoles.Contains(Role))
                throw new UnauthorizedAccessException(
                    $"User '{Username}' with role '{Role}' cannot perform '{operationName}'. " +
                    $"Allowed roles: {string.Join(", ", allowedRoles)}");
        }

        /// <summary>
        /// Validates that the user account can perform login-related operations.
        /// </summary>
        /// <exception cref="InvalidOperationException">If account is inactive, locked, or locked for too long</exception>
        public void ValidateLoginEligibility()
        {
            if (!IsActive)
                throw new InvalidOperationException("Cannot log in with an inactive account");

            if (IsLockedOut)
            {
                if (LockoutExpiresAt > DateTime.UtcNow)
                    throw new InvalidOperationException(
                        $"Account is locked due to failed login attempts. " +
                        $"Please try again after {LockoutExpiresAt:g}");

                // Lockout expired, unlock the account
                IsLockedOut = false;
                FailedLoginAttempts = 0;
            }
        }

        // ===== Validation Helpers =====

        private static void ValidateUsername(string username)
        {
            if (string.IsNullOrWhiteSpace(username))
                throw new ArgumentException("Username cannot be empty", nameof(username));

            if (username.Length < 3 || username.Length > 50)
                throw new ArgumentException("Username must be between 3 and 50 characters", nameof(username));

            if (!username.All(c => char.IsLetterOrDigit(c) || c == '_' || c == '.'))
                throw new ArgumentException("Username can only contain letters, digits, underscores, and periods", nameof(username));
        }

        private static void ValidateEmail(string email)
        {
            if (string.IsNullOrWhiteSpace(email))
                throw new ArgumentException("Email cannot be empty", nameof(email));

            try
            {
                var addr = new System.Net.Mail.MailAddress(email);
                if (addr.Address != email)
                    throw new ArgumentException("Invalid email format", nameof(email));
            }
            catch
            {
                throw new ArgumentException("Invalid email format", nameof(email));
            }
        }
    }

    /// <summary>
    /// Audit entry tracking role changes for compliance and security.
    /// Part of User aggregate to maintain referential integrity.
    /// </summary>
    public class RoleAuditEntry
    {
        public Guid Id { get; set; }
        public Guid UserId { get; set; }
        public UserRole? PreviousRole { get; set; }
        public UserRole NewRole { get; set; }
        public DateTime ChangedAt { get; set; }
        public string ChangedBy { get; set; }
        public string Reason { get; set; }
    }

    /// <summary>
    /// Marker interface for domain entities.
    /// </summary>
    public interface IEntity
    {
        Guid Id { get; }
    }
}
