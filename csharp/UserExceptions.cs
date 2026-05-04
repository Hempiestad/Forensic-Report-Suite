using System;
using System.Collections.Generic;
using ForensicReportWriter.Domain.Enums;

namespace ForensicReportWriter.Domain.Exceptions
{
    /// <summary>
    /// Base exception for user management operations.
    /// </summary>
    public class UserManagementException : Exception
    {
        public UserManagementException(string message) : base(message) { }
        public UserManagementException(string message, Exception innerException) 
            : base(message, innerException) { }
    }

    /// <summary>
    /// Exception thrown when a user attempts to perform an operation without required role.
    /// FEATURE LOCK: Used to enforce investigator/examiner role restrictions.
    /// 
    /// Examples:
    /// - Examiner attempting to access investigative leads (investigator-only)
    /// - Non-investigator attempting to approve legal processes
    /// - User attempting to manage investigative workflows
    /// </summary>
    public class UnauthorizedRoleAccessException : UnauthorizedAccessException
    {
        public Guid UserId { get; }
        public string Username { get; }
        public UserRole ActualRole { get; }
        public UserRole RequiredRole { get; }
        public string OperationName { get; }

        public UnauthorizedRoleAccessException(
            Guid userId,
            string username,
            UserRole actualRole,
            UserRole requiredRole,
            string operationName)
            : base(BuildMessage(username, actualRole, requiredRole, operationName))
        {
            UserId = userId;
            Username = username;
            ActualRole = actualRole;
            RequiredRole = requiredRole;
            OperationName = operationName;
        }

        private static string BuildMessage(
            string username,
            UserRole actualRole,
            UserRole requiredRole,
            string operationName)
        {
            return $"User '{username}' with role '{actualRole}' cannot perform '{operationName}'. " +
                   $"Required role: '{requiredRole}'";
        }
    }

    /// <summary>
    /// Exception thrown when a user's account is locked due to failed login attempts.
    /// </summary>
    public class AccountLockedException : UserManagementException
    {
        public Guid UserId { get; }
        public string Username { get; }
        public DateTime? LockoutExpiresAt { get; }
        public int FailedAttempts { get; }

        public AccountLockedException(
            Guid userId,
            string username,
            DateTime? lockoutExpiresAt,
            int failedAttempts)
            : base(BuildMessage(username, lockoutExpiresAt))
        {
            UserId = userId;
            Username = username;
            LockoutExpiresAt = lockoutExpiresAt;
            FailedAttempts = failedAttempts;
        }

        private static string BuildMessage(string username, DateTime? lockoutExpiresAt)
        {
            var expiryMessage = lockoutExpiresAt.HasValue
                ? $" Please try again after {lockoutExpiresAt:g}"
                : " Please contact an administrator to unlock your account.";

            return $"Account for user '{username}' is locked due to failed login attempts.{expiryMessage}";
        }
    }

    /// <summary>
    /// Exception thrown when an operation is attempted on an inactive user account.
    /// </summary>
    public class InactiveAccountException : UserManagementException
    {
        public Guid UserId { get; }
        public string Username { get; }
        public string OperationName { get; }

        public InactiveAccountException(Guid userId, string username, string operationName = null)
            : base(BuildMessage(username, operationName))
        {
            UserId = userId;
            Username = username;
            OperationName = operationName;
        }

        private static string BuildMessage(string username, string operationName)
        {
            return string.IsNullOrEmpty(operationName)
                ? $"Cannot perform operation on inactive account '{username}'"
                : $"Cannot perform '{operationName}' on inactive account '{username}'";
        }
    }

    /// <summary>
    /// Exception thrown when attempting to create a user with a duplicate username.
    /// </summary>
    public class DuplicateUsernameException : UserManagementException
    {
        public string Username { get; }

        public DuplicateUsernameException(string username)
            : base($"Username '{username}' is already taken. Please choose a different username.")
        {
            Username = username;
        }
    }

    /// <summary>
    /// Exception thrown when attempting to create a user with a duplicate email.
    /// </summary>
    public class DuplicateEmailException : UserManagementException
    {
        public string Email { get; }

        public DuplicateEmailException(string email)
            : base($"Email '{email}' is already registered. Please use a different email address.")
        {
            Email = email;
        }
    }

    /// <summary>
    /// Exception thrown when a password does not meet security requirements.
    /// </summary>
    public class WeakPasswordException : UserManagementException
    {
        public List<string> ValidationErrors { get; }

        public WeakPasswordException(List<string> validationErrors)
            : base(BuildMessage(validationErrors))
        {
            ValidationErrors = validationErrors;
        }

        private static string BuildMessage(List<string> errors)
        {
            return "Password does not meet security requirements:\n" +
                   string.Join("\n", errors);
        }
    }

    /// <summary>
    /// Exception thrown when an invalid password is provided during authentication.
    /// </summary>
    public class InvalidCredentialsException : UserManagementException
    {
        public string Username { get; }
        public string Reason { get; }

        public InvalidCredentialsException(string username, string reason = null)
            : base(BuildMessage(username, reason))
        {
            Username = username;
            Reason = reason ?? "The username or password is incorrect";
        }

        private static string BuildMessage(string username, string reason)
        {
            return $"Authentication failed for user '{username}': {reason ?? "Invalid credentials"}";
        }
    }

    /// <summary>
    /// Exception thrown when a role assignment violates business rules.
    /// </summary>
    public class InvalidRoleAssignmentException : UserManagementException
    {
        public Guid UserId { get; }
        public UserRole RequestedRole { get; }
        public string Reason { get; }

        public InvalidRoleAssignmentException(Guid userId, UserRole requestedRole, string reason)
            : base($"Cannot assign role '{requestedRole}' to user '{userId}': {reason}")
        {
            UserId = userId;
            RequestedRole = requestedRole;
            Reason = reason;
        }
    }

    /// <summary>
    /// Exception thrown when a required field is missing in user data.
    /// </summary>
    public class MissingUserDataException : UserManagementException
    {
        public string FieldName { get; }

        public MissingUserDataException(string fieldName)
            : base($"Required user field '{fieldName}' is missing or empty.")
        {
            FieldName = fieldName;
        }
    }

    /// <summary>
    /// Exception thrown when an unknown or non-existent user is referenced.
    /// </summary>
    public class UserNotFoundException : UserManagementException
    {
        public Guid? UserId { get; }
        public string Username { get; }

        public UserNotFoundException(Guid userId)
            : base($"User with ID '{userId}' was not found.")
        {
            UserId = userId;
        }

        public UserNotFoundException(string username)
            : base($"User '{username}' was not found.")
        {
            Username = username;
        }
    }

    /// <summary>
    /// Exception thrown when attempting operations restricted to administrators.
    /// </summary>
    public class AdminOperationException : UnauthorizedAccessException
    {
        public Guid UserId { get; }
        public string Username { get; }
        public string OperationName { get; }

        public AdminOperationException(Guid userId, string username, string operationName)
            : base($"User '{username}' does not have permission to perform admin operation '{operationName}'")
        {
            UserId = userId;
            Username = username;
            OperationName = operationName;
        }
    }

    /// <summary>
    /// Exception thrown when a password change operation fails validation.
    /// </summary>
    public class PasswordChangeException : UserManagementException
    {
        public Guid UserId { get; }
        public string Reason { get; }

        public PasswordChangeException(Guid userId, string reason)
            : base($"Cannot change password for user '{userId}': {reason}")
        {
            UserId = userId;
            Reason = reason;
        }
    }

    /// <summary>
    /// Exception thrown when transaction with multiple operations fails.
    /// </summary>
    public class UserTransactionException : UserManagementException
    {
        public List<string> FailedOperations { get; }

        public UserTransactionException(string message, List<string> failedOperations = null)
            : base(message)
        {
            FailedOperations = failedOperations ?? new List<string>();
        }
    }
}
