using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using ForensicReportWriter.Domain.Entities;
using ForensicReportWriter.Domain.Enums;

namespace ForensicReportWriter.Application.Interfaces
{
    /// <summary>
    /// Service for managing user accounts, roles, and authentication.
    /// Enforces role-based feature locking to prevent unauthorized access to investigator or examiner operations.
    /// 
    /// Feature Locking Patterns:
    /// - Investigator operations (legal processes, investigative leads, approvals) throw UnauthorizedAccessException for Examiners
    /// - Examiner operations are allowed for both roles but may have limited scope for Investigators
    /// - Admin operations (user creation, role changes) restricted to administrative users
    /// </summary>
    public interface IUserService
    {
        // ===== User CRUD Operations =====

        /// <summary>
        /// Creates a new user account with the specified credentials and role.
        /// Admin operation - restricted to administrative users.
        /// </summary>
        /// <param name="command">Create user command with username, email, password, role, etc.</param>
        /// <returns>Newly created user</returns>
        /// <exception cref="ArgumentException">If validation fails (duplicate username, invalid email, weak password)</exception>
        Task<User> CreateUserAsync(CreateUserCommand command);

        /// <summary>
        /// Retrieves a user by their username.
        /// </summary>
        /// <param name="username">Username to search for</param>
        /// <returns>User if found, null otherwise</returns>
        Task<User> GetByUsernameAsync(string username);

        /// <summary>
        /// Retrieves a user by their unique ID.
        /// </summary>
        /// <param name="userId">User ID to retrieve</param>
        /// <returns>User if found, null otherwise</returns>
        Task<User> GetByIdAsync(Guid userId);

        /// <summary>
        /// Retrieves a user by their email address.
        /// </summary>
        /// <param name="email">Email to search for</param>
        /// <returns>User if found, null otherwise</returns>
        Task<User> GetByEmailAsync(string email);

        /// <summary>
        /// Updates user contact and organizational information.
        /// </summary>
        /// <param name="command">Update user profile command</param>
        /// <returns>Updated user</returns>
        Task<User> UpdateUserAsync(UpdateUserProfileCommand command);

        /// <summary>
        /// Deletes a user account (soft delete - marks as inactive).
        /// Admin operation. Maintains audit trail.
        /// </summary>
        /// <param name="userId">User to delete</param>
        /// <param name="deletedBy">Username of admin performing deletion</param>
        /// <param name="reason">Reason for deletion</param>
        /// <returns>True if successful, false if user not found</returns>
        Task<bool> DeleteUserAsync(Guid userId, string deletedBy, string reason);

        /// <summary>
        /// Gets all active users in the system.
        /// </summary>
        /// <returns>List of active users</returns>
        Task<IList<User>> GetAllActiveUsersAsync();

        /// <summary>
        /// Gets all users (including inactive).
        /// Admin operation - may be restricted to administrators.
        /// </summary>
        /// <returns>List of all users</returns>
        Task<IList<User>> GetAllUsersAsync();

        // ===== Role Management =====

        /// <summary>
        /// Gets all users with a specific role.
        /// </summary>
        /// <param name="role">Role to filter by</param>
        /// <returns>List of users with the specified role</returns>
        Task<IList<User>> GetUsersByRoleAsync(UserRole role);

        /// <summary>
        /// Changes a user's role with full audit trail.
        /// Admin operation. Restricted to administrators.
        /// FEATURE LOCK: Enforces role-based access restrictions.
        /// </summary>
        /// <param name="userId">User whose role is being changed</param>
        /// <param name="newRole">New role to assign</param>
        /// <param name="changedBy">Username of administrator making the change</param>
        /// <param name="reason">Reason for role change (audit purposes)</param>
        /// <returns>Updated user with new role</returns>
        /// <exception cref="InvalidOperationException">If user is inactive or role change invalid</exception>
        Task<User> ChangeRoleAsync(Guid userId, UserRole newRole, string changedBy, string reason);

        /// <summary>
        /// Validates that a role assignment is permitted.
        /// Business rule validation for role transitions.
        /// </summary>
        /// <param name="userId">User being assigned role</param>
        /// <param name="newRole">Role being assigned</param>
        /// <returns>Validation result with any error messages</returns>
        Task<RoleValidationResult> ValidateRoleAssignmentAsync(Guid userId, UserRole newRole);

        /// <summary>
        /// Gets the complete role assignment history for a user.
        /// </summary>
        /// <param name="userId">User whose role history is being queried</param>
        /// <returns>List of role changes in chronological order</returns>
        Task<IList<RoleAuditEntry>> GetRoleHistoryAsync(Guid userId);

        // ===== Password Management =====

        /// <summary>
        /// Validates login credentials (username and password).
        /// Tracks failed login attempts for security.
        /// </summary>
        /// <param name="username">Username attempting to log in</param>
        /// <param name="password">Password to validate</param>
        /// <returns>User if credentials valid, null if invalid</returns>
        /// <exception cref="InvalidOperationException">If account is inactive or locked</exception>
        Task<User> ValidateCredentialsAsync(string username, string password);

        /// <summary>
        /// Changes a user's password (user-initiated change).
        /// Requires verification of current password.
        /// </summary>
        /// <param name="userId">User changing password</param>
        /// <param name="currentPassword">Current password for verification</param>
        /// <param name="newPassword">New password to set</param>
        /// <returns>Updated user</returns>
        /// <exception cref="ArgumentException">If password validation fails or current password incorrect</exception>
        Task<User> ChangePasswordAsync(Guid userId, string currentPassword, string newPassword);

        /// <summary>
        /// Resets a user's password (admin-initiated reset).
        /// User will be prompted to change password on next login.
        /// </summary>
        /// <param name="userId">User whose password is reset</param>
        /// <param name="resetBy">Username of administrator performing reset</param>
        /// <returns>Updated user with password reset flag</returns>
        Task<User> ResetPasswordAsync(Guid userId, string resetBy);

        /// <summary>
        /// Sets a user's password to a specific value (admin use only).
        /// </summary>
        /// <param name="userId">User whose password is being set</param>
        /// <param name="newPassword">New password</param>
        /// <param name="setBy">Username of administrator setting the password</param>
        /// <returns>Updated user</returns>
        Task<User> SetPasswordAsync(Guid userId, string newPassword, string setBy);

        /// <summary>
        /// Validates password strength according to organization policy.
        /// </summary>
        /// <param name="password">Password to validate</param>
        /// <returns>Validation result with any error messages</returns>
        PasswordValidationResult ValidatePasswordStrength(string password);

        // ===== Account Status Management =====

        /// <summary>
        /// Activates a user account (allows login).
        /// </summary>
        /// <param name="userId">User to activate</param>
        /// <param name="activatedBy">Username of user activating account</param>
        /// <returns>Updated user</returns>
        Task<User> ActivateUserAsync(Guid userId, string activatedBy);

        /// <summary>
        /// Deactivates a user account (prevents login).
        /// Admin operation. Maintains audit trail.
        /// </summary>
        /// <param name="userId">User to deactivate</param>
        /// <param name="deactivatedBy">Username of admin</param>
        /// <param name="reason">Reason for deactivation</param>
        /// <returns>Updated user</returns>
        Task<User> DeactivateUserAsync(Guid userId, string deactivatedBy, string reason);

        /// <summary>
        /// Unlocks a user account that was locked due to failed login attempts.
        /// Admin operation.
        /// </summary>
        /// <param name="userId">User to unlock</param>
        /// <param name="unlockedBy">Username of admin</param>
        /// <returns>Updated user</returns>
        Task<User> UnlockAccountAsync(Guid userId, string unlockedBy);

        /// <summary>
        /// Checks if a user account is currently usable (active and not locked out).
        /// </summary>
        /// <param name="userId">User to check</param>
        /// <returns>True if account is usable, false otherwise</returns>
        Task<bool> IsAccountUsableAsync(Guid userId);

        /// <summary>
        /// Records a successful login event.
        /// Updates last login timestamp and clears failed attempts.
        /// </summary>
        /// <param name="userId">User logging in</param>
        /// <returns>Updated user</returns>
        Task<User> RecordLoginSuccessAsync(Guid userId);

        // ===== Feature Access Control =====

        /// <summary>
        /// Ensures the user is an Investigator or throws exception.
        /// Used internally by investigator-only operations.
        /// FEATURE LOCK: Blocks Examiner access to investigative features.
        /// </summary>
        /// <param name="userId">User whose role is being checked</param>
        /// <param name="operationName">Name of operation for error message</param>
        /// <exception cref="UnauthorizedAccessException">If user is not an Investigator</exception>
        Task EnsureInvestigatorAccessAsync(Guid userId, string operationName);

        /// <summary>
        /// Ensures the user is an Examiner or throws exception.
        /// FEATURE LOCK: Blocks non-Examiner access to examiner-specific features.
        /// </summary>
        /// <param name="userId">User whose role is being checked</param>
        /// <param name="operationName">Name of operation for error message</param>
        /// <exception cref="UnauthorizedAccessException">If user is not an Examiner</exception>
        Task EnsureExaminerAccessAsync(Guid userId, string operationName);

        /// <summary>
        /// Ensures the user has one of the specified roles.
        /// Generic role validation for feature access control.
        /// </summary>
        /// <param name="userId">User whose role is being checked</param>
        /// <param name="allowedRoles">Roles permitted for the operation</param>
        /// <param name="operationName">Name of operation for error message</param>
        /// <exception cref="UnauthorizedAccessException">If user's role not in allowed list</exception>
        Task EnsureRoleAsync(Guid userId, IEnumerable<UserRole> allowedRoles, string operationName);

        /// <summary>
        /// Gets list of actions the user is permitted to perform based on their role.
        /// Used by authorization system and UI to show/hide features.
        /// </summary>
        /// <param name="userId">User whose permissions are being queried</param>
        /// <returns>List of permitted action names</returns>
        Task<IList<string>> GetPermittedActionsAsync(Guid userId);

        /// <summary>
        /// Checks if a user can perform a specific action.
        /// </summary>
        /// <param name="userId">User being checked</param>
        /// <param name="actionName">Action name to check</param>
        /// <returns>True if user can perform action, false otherwise</returns>
        Task<bool> CanPerformActionAsync(Guid userId, string actionName);

        // ===== Statistics and Monitoring =====

        /// <summary>
        /// Gets user count by role for administrative dashboard.
        /// </summary>
        /// <returns>Dictionary mapping role to user count</returns>
        Task<Dictionary<UserRole, int>> GetUserCountByRoleAsync();

        /// <summary>
        /// Gets count of active and inactive users for administrative dashboard.
        /// </summary>
        /// <returns>Tuple of (active count, inactive count)</returns>
        Task<(int ActiveCount, int InactiveCount)> GetAccountStatusCountsAsync();

        /// <summary>
        /// Gets list of users who haven't logged in recently.
        /// Admin operation for account maintenance and compliance.
        /// </summary>
        /// <param name="days">Number of days to consider "recently" (default: 30)</param>
        /// <returns>List of inactive users</returns>
        Task<IList<User>> GetInactiveUsersAsync(int days = 30);

        /// <summary>
        /// Gets recently logged in users for session monitoring.
        /// </summary>
        /// <param name="hours">Number of hours to look back (default: 24)</param>
        /// <returns>List of recently active users</returns>
        Task<IList<User>> GetRecentlyActiveUsersAsync(int hours = 24);

        /// <summary>
        /// Exports user list with roles for compliance and auditing.
        /// </summary>
        /// <returns>List of user export DTOs</returns>
        Task<IList<UserExportDto>> ExportUsersAsync();
    }

    /// <summary>
    /// Command for creating a new user.
    /// </summary>
    public class CreateUserCommand
    {
        public string Username { get; set; }
        public string Email { get; set; }
        public string Password { get; set; }
        public string FullName { get; set; }
        public string Department { get; set; }
        public string Title { get; set; }
        public UserRole Role { get; set; }
        public string CreatedBy { get; set; }
    }

    /// <summary>
    /// Command for updating user profile information.
    /// </summary>
    public class UpdateUserProfileCommand
    {
        public Guid UserId { get; set; }
        public string Email { get; set; }
        public string FullName { get; set; }
        public string Department { get; set; }
        public string Title { get; set; }
        public string UpdatedBy { get; set; }
    }

    /// <summary>
    /// Result of role assignment validation.
    /// </summary>
    public class RoleValidationResult
    {
        public bool IsValid { get; set; }
        public string ErrorMessage { get; set; }
        public List<string> ValidationErrors { get; set; } = new();

        public static RoleValidationResult Success() => new() { IsValid = true };
        public static RoleValidationResult Failure(string errorMessage) => 
            new() { IsValid = false, ErrorMessage = errorMessage };
    }

    /// <summary>
    /// Result of password strength validation.
    /// </summary>
    public class PasswordValidationResult
    {
        public bool IsValid { get; set; }
        public List<string> ValidationErrors { get; set; } = new();

        public static PasswordValidationResult Success() => new() { IsValid = true };
        public static PasswordValidationResult Failure(params string[] errors) => 
            new() { IsValid = false, ValidationErrors = new(errors) };
    }

    /// <summary>
    /// DTO for exporting user information for compliance/auditing.
    /// </summary>
    public class UserExportDto
    {
        public Guid UserId { get; set; }
        public string Username { get; set; }
        public string Email { get; set; }
        public string FullName { get; set; }
        public string Department { get; set; }
        public string Title { get; set; }
        public UserRole Role { get; set; }
        public bool IsActive { get; set; }
        public DateTime CreatedAt { get; set; }
        public string CreatedBy { get; set; }
        public DateTime? LastLoginAt { get; set; }
    }
}
