using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using BC = BCrypt.Net.BCrypt;
using ForensicReportWriter.Application.Interfaces;
using ForensicReportWriter.Domain.Entities;
using ForensicReportWriter.Domain.Enums;
using Microsoft.Extensions.Logging;

namespace ForensicReportWriter.Application.Services
{
    /// <summary>
    /// Service implementation for user management with role-based feature locking.
    /// 
    /// FEATURE LOCKING ARCHITECTURE:
    /// =============================
    /// This service enforces role-based access control through two mechanisms:
    /// 
    /// 1. RUNTIME CHECKS: Methods like EnsureInvestigatorAccessAsync throw UnauthorizedAccessException
    ///    when attempting operations restricted to investigator roles.
    /// 
    /// 2. ROLE-BASED VALIDATION: Role validation occurs during assignment and enforcement
    ///    prevents transitions to invalid states.
    /// 
    /// ROLE SEMANTICS:
    /// ===============
    /// Investigator:
    ///   - Full access to investigative operations (investigative leads, legal processes)
    ///   - Can approve cases and manage workflows requiring investigator signature
    ///   - Typical permissions: ViewCases, ManageInvestigativeLeads, ManageLegalProcesses, ApproveCases
    /// 
    /// Examiner:
    ///   - Access limited to examination and report generation
    ///   - Cannot access investigative or legal workflow features
    ///   - Typical permissions: ViewCases, ViewReports, ExamineCase, GenerateExaminationReport
    /// 
    /// SECURITY FEATURES:
    /// ==================
    /// - Password hashing with BCrypt
    /// - Account lockout after 5 failed login attempts (15 minute lockout)
    /// - Password strength validation (min 8 chars, uppercase, lowercase, digit, special char)
    /// - Admin password resets require password change on next login
    /// - Audit trail for role changes
    /// - Login tracking for compliance
    /// </summary>
    public class UserService : IUserService
    {
        private readonly IRepository<User> _userRepository;
        private readonly ILogger<UserService> _logger;
        private readonly IMapper _mapper;

        private const int MinPasswordLength = 8;
        private const int MaxFailedLoginAttempts = 5;
        private const int LockoutDurationMinutes = 15;

        public UserService(
            IRepository<User> userRepository,
            ILogger<UserService> logger,
            IMapper mapper)
        {
            _userRepository = userRepository ?? throw new ArgumentNullException(nameof(userRepository));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _mapper = mapper ?? throw new ArgumentNullException(nameof(mapper));
        }

        // ===== User CRUD Operations =====

        public async Task<User> CreateUserAsync(CreateUserCommand command)
        {
            ValidateCreateUserCommand(command);

            // Check for duplicate username
            var existingByUsername = await _userRepository.FirstOrDefaultAsync(
                u => u.Username == command.Username);
            if (existingByUsername != null)
                throw new ArgumentException($"Username '{command.Username}' is already taken");

            // Check for duplicate email
            var existingByEmail = await _userRepository.FirstOrDefaultAsync(
                u => u.Email == command.Email);
            if (existingByEmail != null)
                throw new ArgumentException($"Email '{command.Email}' is already registered");

            // Validate password strength
            var passwordValidation = ValidatePasswordStrength(command.Password);
            if (!passwordValidation.IsValid)
                throw new ArgumentException(
                    $"Password does not meet security requirements: {string.Join("; ", passwordValidation.ValidationErrors)}");

            // Hash password
            var passwordHash = BC.HashPassword(command.Password);

            // Create user
            var user = User.Create(
                command.Username,
                command.Email,
                passwordHash,
                command.Role,
                command.FullName,
                command.Department,
                command.Title,
                command.CreatedBy);

            await _userRepository.AddAsync(user);
            await _userRepository.SaveChangesAsync();

            _logger.LogInformation(
                "User '{Username}' created by '{CreatedBy}' with role '{Role}'",
                user.Username, command.CreatedBy, command.Role);

            return user;
        }

        public async Task<User> GetByUsernameAsync(string username)
        {
            return await _userRepository.FirstOrDefaultAsync(u => u.Username == username);
        }

        public async Task<User> GetByIdAsync(Guid userId)
        {
            return await _userRepository.GetByIdAsync(userId);
        }

        public async Task<User> GetByEmailAsync(string email)
        {
            return await _userRepository.FirstOrDefaultAsync(u => u.Email == email);
        }

        public async Task<User> UpdateUserAsync(UpdateUserProfileCommand command)
        {
            var user = await _userRepository.GetByIdAsync(command.UserId);
            if (user == null)
                throw new InvalidOperationException($"User '{command.UserId}' not found");

            user.UpdateContactInfo(
                command.Email,
                command.FullName,
                command.Department,
                command.Title,
                command.UpdatedBy);

            await _userRepository.UpdateAsync(user);
            await _userRepository.SaveChangesAsync();

            _logger.LogInformation("User '{Username}' profile updated by '{UpdatedBy}'", 
                user.Username, command.UpdatedBy);

            return user;
        }

        public async Task<bool> DeleteUserAsync(Guid userId, string deletedBy, string reason)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                return false;

            user.Deactivate(deletedBy, reason);
            await _userRepository.UpdateAsync(user);
            await _userRepository.SaveChangesAsync();

            _logger.LogInformation(
                "User '{Username}' deactivated by '{DeactivatedBy}'. Reason: {Reason}",
                user.Username, deletedBy, reason);

            return true;
        }

        public async Task<IList<User>> GetAllActiveUsersAsync()
        {
            return await _userRepository.ListAsync(u => u.IsActive);
        }

        public async Task<IList<User>> GetAllUsersAsync()
        {
            return await _userRepository.ListAsync();
        }

        // ===== Role Management =====

        public async Task<IList<User>> GetUsersByRoleAsync(UserRole role)
        {
            return await _userRepository.ListAsync(u => u.Role == role && u.IsActive);
        }

        public async Task<User> ChangeRoleAsync(Guid userId, UserRole newRole, string changedBy, string reason)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            // Validate role assignment
            var validation = await ValidateRoleAssignmentAsync(userId, newRole);
            if (!validation.IsValid)
                throw new InvalidOperationException(
                    $"Cannot assign role '{newRole}': {validation.ErrorMessage}");

            var previousRole = user.Role;
            user.ChangeRole(newRole, changedBy, reason);

            await _userRepository.UpdateAsync(user);
            await _userRepository.SaveChangesAsync();

            _logger.LogWarning(
                "User '{Username}' role changed from '{OldRole}' to '{NewRole}' by '{ChangedBy}'. Reason: {Reason}",
                user.Username, previousRole, newRole, changedBy, reason);

            return user;
        }

        public async Task<RoleValidationResult> ValidateRoleAssignmentAsync(Guid userId, UserRole newRole)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                return RoleValidationResult.Failure("User not found");

            if (!user.IsActive)
                return RoleValidationResult.Failure("Cannot assign role to inactive user");

            // Validate that the role is a valid enum value
            if (!Enum.IsDefined(typeof(UserRole), newRole))
                return RoleValidationResult.Failure($"Invalid role '{newRole}'");

            return RoleValidationResult.Success();
        }

        public async Task<IList<RoleAuditEntry>> GetRoleHistoryAsync(Guid userId)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            return user.RoleAuditHistory.OrderBy(r => r.ChangedAt).ToList();
        }

        // ===== Password Management =====

        public async Task<User> ValidateCredentialsAsync(string username, string password)
        {
            if (string.IsNullOrWhiteSpace(username) || string.IsNullOrWhiteSpace(password))
                return null;

            var user = await GetByUsernameAsync(username);
            if (user == null)
                return null;

            // Check account usability
            try
            {
                user.ValidateLoginEligibility();
            }
            catch (InvalidOperationException ex)
            {
                _logger.LogWarning("Login attempt for '{Username}' failed: {Reason}", username, ex.Message);
                return null;
            }

            // Verify password
            if (!BC.Verify(password, user.PasswordHash))
            {
                user.RecordFailedLoginAttempt(LockoutDurationMinutes);
                await _userRepository.UpdateAsync(user);
                await _userRepository.SaveChangesAsync();

                _logger.LogWarning(
                    "Failed login attempt for '{Username}'. Failed attempts: {Attempts}",
                    username, user.FailedLoginAttempts);

                return null;
            }

            return user;
        }

        public async Task<User> ChangePasswordAsync(Guid userId, string currentPassword, string newPassword)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            // Verify current password
            if (!BC.Verify(currentPassword, user.PasswordHash))
                throw new ArgumentException("Current password is incorrect");

            // Validate new password
            var validation = ValidatePasswordStrength(newPassword);
            if (!validation.IsValid)
                throw new ArgumentException(
                    $"New password does not meet security requirements: {string.Join("; ", validation.ValidationErrors)}");

            // Hash and update
            var newHash = BC.HashPassword(newPassword);
            user.UpdatePassword(newHash, user.Username, isAdminReset: false);

            await _userRepository.UpdateAsync(user);
            await _userRepository.SaveChangesAsync();

            _logger.LogInformation("Password changed for user '{Username}'", user.Username);

            return user;
        }

        public async Task<User> ResetPasswordAsync(Guid userId, string resetBy)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            // Generate temporary password
            var tempPassword = GenerateTemporaryPassword();
            var tempHash = BC.HashPassword(tempPassword);

            user.UpdatePassword(tempHash, resetBy, isAdminReset: true);

            await _userRepository.UpdateAsync(user);
            await _userRepository.SaveChangesAsync();

            _logger.LogWarning("Password reset for user '{Username}' by '{ResetBy}'", user.Username, resetBy);

            // In real implementation, send tempPassword to user via email
            // For now, we just log that it should be communicated securely

            return user;
        }

        public async Task<User> SetPasswordAsync(Guid userId, string newPassword, string setBy)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            var validation = ValidatePasswordStrength(newPassword);
            if (!validation.IsValid)
                throw new ArgumentException(
                    $"Password does not meet security requirements: {string.Join("; ", validation.ValidationErrors)}");

            var newHash = BC.HashPassword(newPassword);
            user.UpdatePassword(newHash, setBy, isAdminReset: false);

            await _userRepository.UpdateAsync(user);
            await _userRepository.SaveChangesAsync();

            _logger.LogInformation("Password set for user '{Username}' by '{SetBy}'", user.Username, setBy);

            return user;
        }

        public PasswordValidationResult ValidatePasswordStrength(string password)
        {
            var errors = new List<string>();

            if (string.IsNullOrWhiteSpace(password))
                errors.Add("Password cannot be empty");
            else
            {
                if (password.Length < MinPasswordLength)
                    errors.Add($"Password must be at least {MinPasswordLength} characters long");

                if (!password.Any(char.IsUpper))
                    errors.Add("Password must contain at least one uppercase letter");

                if (!password.Any(char.IsLower))
                    errors.Add("Password must contain at least one lowercase letter");

                if (!password.Any(char.IsDigit))
                    errors.Add("Password must contain at least one digit");

                if (!password.Any(c => !char.IsLetterOrDigit(c)))
                    errors.Add("Password must contain at least one special character");
            }

            return errors.Count == 0
                ? PasswordValidationResult.Success()
                : PasswordValidationResult.Failure(errors.ToArray());
        }

        // ===== Account Status Management =====

        public async Task<User> ActivateUserAsync(Guid userId, string activatedBy)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            user.Reactivate(activatedBy);
            await _userRepository.UpdateAsync(user);
            await _userRepository.SaveChangesAsync();

            _logger.LogInformation("User '{Username}' activated by '{ActivatedBy}'", user.Username, activatedBy);

            return user;
        }

        public async Task<User> DeactivateUserAsync(Guid userId, string deactivatedBy, string reason)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            user.Deactivate(deactivatedBy, reason);
            await _userRepository.UpdateAsync(user);
            await _userRepository.SaveChangesAsync();

            _logger.LogInformation(
                "User '{Username}' deactivated by '{DeactivatedBy}'. Reason: {Reason}",
                user.Username, deactivatedBy, reason);

            return user;
        }

        public async Task<User> UnlockAccountAsync(Guid userId, string unlockedBy)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            user.UnlockAccount(unlockedBy);
            await _userRepository.UpdateAsync(user);
            await _userRepository.SaveChangesAsync();

            _logger.LogInformation("User '{Username}' unlocked by '{UnlockedBy}'", user.Username, unlockedBy);

            return user;
        }

        public async Task<bool> IsAccountUsableAsync(Guid userId)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            return user?.IsUsable() ?? false;
        }

        public async Task<User> RecordLoginSuccessAsync(Guid userId)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            user.RecordSuccessfulLogin();
            await _userRepository.UpdateAsync(user);
            await _userRepository.SaveChangesAsync();

            return user;
        }

        // ===== Feature Access Control =====

        /// <summary>
        /// FEATURE LOCK: Ensures only Investigator role can access investigative features.
        /// Throws UnauthorizedAccessException for Examiner and other roles.
        /// </summary>
        public async Task EnsureInvestigatorAccessAsync(Guid userId, string operationName)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            user.EnsureRole(UserRole.Investigator, operationName);
        }

        /// <summary>
        /// FEATURE LOCK: Ensures only Examiner role can access examiner-specific features.
        /// </summary>
        public async Task EnsureExaminerAccessAsync(Guid userId, string operationName)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            user.EnsureRole(UserRole.Examiner, operationName);
        }

        /// <summary>
        /// FEATURE LOCK: Generic role validation for feature access.
        /// </summary>
        public async Task EnsureRoleAsync(Guid userId, IEnumerable<UserRole> allowedRoles, string operationName)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            user.EnsureAnyRole(allowedRoles, operationName);
        }

        public async Task<IList<string>> GetPermittedActionsAsync(Guid userId)
        {
            var user = await _userRepository.GetByIdAsync(userId);
            if (user == null)
                throw new InvalidOperationException($"User '{userId}' not found");

            return user.GetPermittedActions();
        }

        public async Task<bool> CanPerformActionAsync(Guid userId, string actionName)
        {
            var actions = await GetPermittedActionsAsync(userId);
            return actions.Contains(actionName);
        }

        // ===== Statistics and Monitoring =====

        public async Task<Dictionary<UserRole, int>> GetUserCountByRoleAsync()
        {
            var allUsers = await GetAllActiveUsersAsync();
            return allUsers
                .GroupBy(u => u.Role)
                .ToDictionary(g => g.Key, g => g.Count());
        }

        public async Task<(int ActiveCount, int InactiveCount)> GetAccountStatusCountsAsync()
        {
            var allUsers = await GetAllUsersAsync();
            var activeCount = allUsers.Count(u => u.IsActive);
            var inactiveCount = allUsers.Count(u => !u.IsActive);
            return (activeCount, inactiveCount);
        }

        public async Task<IList<User>> GetInactiveUsersAsync(int days = 30)
        {
            var cutoffDate = DateTime.UtcNow.AddDays(-days);
            var allUsers = await GetAllActiveUsersAsync();

            return allUsers
                .Where(u => u.LastLoginAt == null || u.LastLoginAt < cutoffDate)
                .ToList();
        }

        public async Task<IList<User>> GetRecentlyActiveUsersAsync(int hours = 24)
        {
            var cutoffDate = DateTime.UtcNow.AddHours(-hours);
            var allUsers = await GetAllActiveUsersAsync();

            return allUsers
                .Where(u => u.LastLoginAt != null && u.LastLoginAt > cutoffDate)
                .ToList();
        }

        public async Task<IList<UserExportDto>> ExportUsersAsync()
        {
            var allUsers = await GetAllUsersAsync();
            return _mapper.MapList<User, UserExportDto>(allUsers);
        }

        // ===== Helper Methods =====

        private void ValidateCreateUserCommand(CreateUserCommand command)
        {
            if (command == null)
                throw new ArgumentNullException(nameof(command));

            if (string.IsNullOrWhiteSpace(command.Username))
                throw new ArgumentException("Username is required");

            if (string.IsNullOrWhiteSpace(command.Email))
                throw new ArgumentException("Email is required");

            if (string.IsNullOrWhiteSpace(command.Password))
                throw new ArgumentException("Password is required");

            if (string.IsNullOrWhiteSpace(command.FullName))
                throw new ArgumentException("Full name is required");

            if (string.IsNullOrWhiteSpace(command.CreatedBy))
                throw new ArgumentException("CreatedBy is required");
        }

        private static string GenerateTemporaryPassword()
        {
            const string chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%";
            var random = new Random();
            var result = new System.Text.StringBuilder(12);
            for (int i = 0; i < 12; i++)
                result.Append(chars[random.Next(chars.Length)]);
            return result.ToString();
        }
    }
}
