# User Management and Role-Based Feature Locking
## Comprehensive Implementation Guide

---

## Table of Contents
1. [Overview](#overview)
2. [Role Definitions](#role-definitions)
3. [Feature Locking Architecture](#feature-locking-architecture)
4. [User.cs Domain Entity](#usercs-domain-entity)
5. [IUserService Interface](#iuserservice-interface)
6. [UserService Implementation](#userservice-implementation)
7. [Integration Patterns](#integration-patterns)
8. [Security Considerations](#security-considerations)
9. [Usage Examples](#usage-examples)
10. [Testing Scenarios](#testing-scenarios)

---

## Overview

The User Management system implements **role-based feature locking** to prevent unauthorized access to investigator-specific or examiner-specific features. The system enforces these restrictions at multiple levels:

- **Domain Level**: User entity validates role transitions
- **Service Level**: IUserService methods throw exceptions for unauthorized access
- **Application Level**: Services check user roles before executing operations
- **UI Level**: Commands and tabs are hidden/disabled based on role (existing implementation extends this)

### Key Design Principles

1. **Fail-Safe**: Operations throw exceptions rather than silently failing
2. **Audit Trail**: All role changes and security events are logged
3. **Account Security**: Password hashing, lockout mechanisms, password strength validation
4. **Separation of Concerns**: Role checking is centralized in service layer
5. **Compliance-Ready**: Audit trails and logging for regulatory requirements

---

## Role Definitions

### Investigator Role
The Investigator role has access to investigative operations and case management workflows:

**Permitted Actions:**
- `ViewCases` - View forensic cases
- `ViewReports` - View generated reports
- `ExportReports` - Export reports for external use
- `EditReports` - Modify reports
- `CreateNotes` - Add notes to cases
- `EditNotes` - Modify notes
- `ManageInvestigativeLeads` - ✅ **INVESTIGATOR-ONLY**
- `ManageLegalProcesses` - ✅ **INVESTIGATOR-ONLY**
- `ApproveCases` - ✅ **INVESTIGATOR-ONLY**
- `ManagePeerReview` - ✅ **INVESTIGATOR-ONLY**
- `ViewInvestigativeReports` - ✅ **INVESTIGATOR-ONLY**
- `InitiateLegalRequest` - ✅ **INVESTIGATOR-ONLY**

**Feature Lock Enforcement:**
```csharp
// Anyone with Investigator role can perform:
await _legalProcessService.ApproveLegalProcessAsync(legalProcessId);

// Examiners calling this will get UnauthorizedAccessException:
// "User 'john.examiner' with role 'Examiner' cannot perform 'ApproveLegalProcess'. 
//  Required role: 'Investigator'"
```

### Examiner Role
The Examiner role is restricted to examination and forensic analysis tasks:

**Permitted Actions:**
- `ViewCases` - View forensic cases
- `ViewReports` - View generated reports
- `ExportReports` - Export reports
- `EditReports` - Modify reports (examination findings)
- `CreateNotes` - Add examination notes
- `EditNotes` - Modify examination notes
- `ExamineCase` - ✅ **EXAMINER-SPECIFIC**
- `GenerateExaminationReport` - ✅ **EXAMINER-SPECIFIC**

**Feature Lock Enforcement:**
```csharp
// Examiners can examine cases:
var examinationResult = await _examinationService.ExamineCaseAsync(caseId);

// Investigators can also examine (not exclusive to examiner):
var result = await _examinationService.ExamineCaseAsync(caseId);

// Neither role can access investigative leads:
await _investigativeLeadService.CreateLeadAsync(leadData); // ❌ UnauthorizedAccessException
```

---

## Feature Locking Architecture

### Three-Layer Enforcement

#### Layer 1: Domain Entity (User.cs)

The User aggregate root enforces role constraints:

```csharp
public void EnsureRole(UserRole requiredRole, string operationName)
{
    if (Role != requiredRole)
        throw new UnauthorizedAccessException(
            $"User '{Username}' with role '{Role}' cannot perform '{operationName}'. " +
            $"Required role: '{requiredRole}'");
}

public void EnsureAnyRole(IEnumerable<UserRole> allowedRoles, string operationName)
{
    if (!allowedRoles.Contains(Role))
        throw new UnauthorizedAccessException(
            $"User '{Username}' with role '{Role}' cannot perform '{operationName}'. " +
            $"Allowed roles: {string.Join(", ", allowedRoles)}");
}
```

#### Layer 2: Service Layer (UserService.cs)

The IUserService provides feature lock enforcement methods:

```csharp
/// Ensures user is an Investigator
public async Task EnsureInvestigatorAccessAsync(Guid userId, string operationName)
{
    var user = await _userRepository.GetByIdAsync(userId);
    user.EnsureRole(UserRole.Investigator, operationName);
}

/// Ensures user can perform a specific action
public async Task<bool> CanPerformActionAsync(
    Guid userId, 
    string actionName)
{
    var actions = await GetPermittedActionsAsync(userId);
    return actions.Contains(actionName);
}
```

#### Layer 3: Business Logic Services

Domain services (LegalProcessService, InvestigativeLeadService, etc.) check roles:

```csharp
public class LegalProcessService
{
    public async Task ApproveLegalProcessAsync(Guid legalProcessId, Guid userId)
    {
        // FEATURE LOCK: Only investigators can approve legal processes
        await _userService.EnsureInvestigatorAccessAsync(
            userId, 
            "ApproveLegalProcess");

        var legalProcess = await _legalProcessRepository.GetByIdAsync(legalProcessId);
        legalProcess.Approve();
        await _legalProcessRepository.SaveChangesAsync();
    }
}
```

---

## User.cs Domain Entity

### Structure

The User entity is a rich domain object that enforces role-based constraints:

```csharp
public class User : IEntity
{
    public Guid Id { get; private set; }
    public string Username { get; private set; }  // Immutable, unique
    public string Email { get; private set; }
    public string PasswordHash { get; private set; }
    public UserRole Role { get; private set; }  // Investigator or Examiner
    public bool IsActive { get; private set; }
    public string FullName { get; private set; }
    public string Department { get; private set; }
    public string Title { get; private set; }
    
    // Security tracking
    public int FailedLoginAttempts { get; private set; }
    public bool IsLockedOut { get; private set; }
    public DateTime? LockoutExpiresAt { get; private set; }
    
    // Audit fields
    public DateTime CreatedAt { get; private set; }
    public string CreatedBy { get; private set; }
    public DateTime UpdatedAt { get; private set; }
    public string UpdatedBy { get; private set; }
    
    // Navigation
    public List<RoleAuditEntry> RoleAuditHistory { get; private set; }
}
```

### Key Methods

#### Creating a User

```csharp
var user = User.Create(
    username: "john.investigator",
    email: "john@forensics.local",
    passwordHash: BCrypt.HashPassword("SecureP@ssw0rd"),
    role: UserRole.Investigator,
    fullName: "John Investigator",
    department: "Investigations",
    title: "Senior Investigator",
    createdBy: "admin");
```

#### Changing Role

```csharp
// Changes role with audit trail
user.ChangeRole(
    newRole: UserRole.Examiner,
    changedBy: "admin",
    reason: "Reassigned to forensic examination team");

// RoleAuditHistory is automatically updated with:
// - Previous role: Investigator
// - New role: Examiner
// - Changed at: timestamp
// - Changed by: admin
// - Reason: Reassigned to forensic examination team
```

#### Updating Password

```csharp
// User-initiated password change
user.UpdatePassword(
    newPasswordHash: BCrypt.HashPassword("NewSecureP@ssw0rd"),
    changedBy: user.Username,
    isAdminReset: false);

// Admin password reset (user must change on next login)
user.UpdatePassword(
    newPasswordHash: hashedTempPassword,
    changedBy: "admin",
    isAdminReset: true);
```

#### Enforcing Role

```csharp
// Will throw UnauthorizedAccessException if role doesn't match
try
{
    user.EnsureRole(UserRole.Investigator, "ApproveLegalProcess");
}
catch (UnauthorizedAccessException ex)
{
    // User role doesn't match - operation blocked
    logger.LogWarning(ex.Message);
}
```

---

## IUserService Interface

### Role-Based Access Control Methods

#### EnsureInvestigatorAccessAsync

**Purpose:** Blocks non-investigator users from accessing investigator features

```csharp
public interface IUserService
{
    /// <summary>
    /// FEATURE LOCK: Ensures only Investigator role can access investigative features.
    /// Throws UnauthorizedAccessException for Examiner and other roles.
    /// </summary>
    Task EnsureInvestigatorAccessAsync(Guid userId, string operationName);
}
```

**Usage Example:**
```csharp
public class LegalProcessService
{
    public async Task InitiateLegalRequestAsync(
        Guid legalRequestId, 
        Guid investigatorId)
    {
        // Prevent examiners from initiating legal requests
        await _userService.EnsureInvestigatorAccessAsync(
            investigatorId, 
            "InitiateLegalRequest");
        
        var request = await _legalRepository.GetByIdAsync(legalRequestId);
        request.Initiate();
        await _legalRepository.SaveChangesAsync();
    }
}
```

#### EnsureExaminerAccessAsync

**Purpose:** Enforces examiner-specific restrictions (if any)

```csharp
/// <summary>
/// FEATURE LOCK: Ensures only Examiner role can access examiner-specific features.
/// </summary>
Task EnsureExaminerAccessAsync(Guid userId, string operationName);
```

#### GetPermittedActionsAsync

**Purpose:** Gets list of actions user can perform based on role

```csharp
var actions = await _userService.GetPermittedActionsAsync(userId);
// Returns: ["ViewCases", "ViewReports", "ManageLegalProcesses", ...]

// Check if user can perform an action
bool canApprove = await _userService.CanPerformActionAsync(userId, "ApproveCases");
```

#### ChangeRoleAsync

**Purpose:** Changes user role with full audit trail

```csharp
var updatedUser = await _userService.ChangeRoleAsync(
    userId: new Guid("..."),
    newRole: UserRole.Investigator,
    changedBy: "admin",
    reason: "Promotion to investigator team");

// Role change is logged to audit history
// Can be queried with GetRoleHistoryAsync
```

---

## UserService Implementation

### Password Security

The UserService implements strong password security:

```csharp
public PasswordValidationResult ValidatePasswordStrength(string password)
{
    var errors = new List<string>();
    
    // Minimum 8 characters
    if (password.Length < 8)
        errors.Add("Password must be at least 8 characters long");
    
    // Must contain uppercase
    if (!password.Any(char.IsUpper))
        errors.Add("Password must contain at least one uppercase letter");
    
    // Must contain lowercase
    if (!password.Any(char.IsLower))
        errors.Add("Password must contain at least one lowercase letter");
    
    // Must contain digit
    if (!password.Any(char.IsDigit))
        errors.Add("Password must contain at least one digit");
    
    // Must contain special character
    if (!password.Any(c => !char.IsLetterOrDigit(c)))
        errors.Add("Password must contain at least one special character");
    
    return errors.Count == 0
        ? PasswordValidationResult.Success()
        : PasswordValidationResult.Failure(errors.ToArray());
}
```

**Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter  
- At least one digit
- At least one special character (!@#$%^&*-_)

### Account Lockout

Failed login attempts trigger automatic account lockout:

```csharp
public async Task<User> ValidateCredentialsAsync(string username, string password)
{
    var user = await GetByUsernameAsync(username);
    
    // Verify password using BCrypt
    if (!BC.Verify(password, user.PasswordHash))
    {
        // Record failed attempt
        user.RecordFailedLoginAttempt(lockoutDurationMinutes: 15);
        
        // After 5 failed attempts (MaxFailedLoginAttempts = 5)
        // User is locked for 15 minutes
        if (user.FailedLoginAttempts >= 5)
        {
            user.IsLockedOut = true;
            user.LockoutExpiresAt = DateTime.UtcNow.AddMinutes(15);
        }
        
        await _userRepository.UpdateAsync(user);
        return null;  // Authentication failed
    }
    
    // Successful login clears all failed attempts
    user.RecordSuccessfulLogin();
    return user;
}
```

### Audit Logging

All user operations are logged:

```csharp
_logger.LogWarning(
    "User '{Username}' role changed from '{OldRole}' to '{NewRole}' " +
    "by '{ChangedBy}'. Reason: {Reason}",
    user.Username, previousRole, newRole, changedBy, reason);

_logger.LogInformation(
    "User '{Username}' created by '{CreatedBy}' with role '{Role}'",
    user.Username, command.CreatedBy, command.Role);
```

---

## Integration Patterns

### Pattern 1: Service Method with Role Check

```csharp
public class InvestigativeLeadService
{
    private readonly IUserService _userService;
    
    public async Task<InvestigativeLead> CreateLeadAsync(
        Guid caseId,
        InvestigativeLeadData leadData,
        Guid investigatorId)
    {
        // FEATURE LOCK: Only investigators can create investigative leads
        await _userService.EnsureInvestigatorAccessAsync(
            investigatorId,
            "CreateInvestigativeLead");
        
        var lead = InvestigativeLead.Create(caseId, leadData, investigatorId);
        await _leadRepository.AddAsync(lead);
        await _leadRepository.SaveChangesAsync();
        
        return lead;
    }
}
```

### Pattern 2: UI Command Binding

```csharp
// In MainWindowViewModel
public class MainWindowViewModel
{
    private readonly IUserService _userService;
    private Guid _currentUserId;
    
    public ICommand ShowInvestigativeLeadsCommand => 
        new AsyncRelayCommand(ShowInvestigativeLeads);
    
    private async Task ShowInvestigativeLeads()
    {
        try
        {
            // Check if user can perform this action
            bool canAccess = await _userService.CanPerformActionAsync(
                _currentUserId,
                "ManageInvestigativeLeads");
            
            if (!canAccess)
            {
                MessageBox.Show(
                    "You do not have permission to manage investigative leads. " +
                    "This feature is restricted to Investigator role.",
                    "Access Denied",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
                return;
            }
            
            // Show investigative leads view
            _navigationService.NavigateTo("InvestigativeLeadsView");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error showing investigative leads");
        }
    }
}
```

### Pattern 3: Authorization Middleware/Filter

```csharp
// In ASP.NET Core API
[ApiController]
[Route("api/legal-processes")]
public class LegalProcessesController : ControllerBase
{
    private readonly IUserService _userService;
    private readonly Guid _userId;  // From claims/token
    
    [HttpPost("{id}/approve")]
    public async Task<IActionResult> ApproveProcess(Guid id)
    {
        try
        {
            // Check authorization before executing
            await _userService.EnsureInvestigatorAccessAsync(
                _userId,
                "ApproveLegalProcess");
            
            await _legalProcessService.ApproveAsync(id);
            return Ok();
        }
        catch (UnauthorizedAccessException ex)
        {
            return Forbid(ex.Message);
        }
    }
}
```

### Pattern 4: Conditional Feature Availability

```csharp
public class CaseViewModel
{
    private readonly IUserService _userService;
    private Guid _currentUserId;
    
    public CaseViewModel(IUserService userService)
    {
        _userService = userService;
    }
    
    public async Task LoadCaseAsync(Guid caseId)
    {
        var case_ = await _caseRepository.GetByIdAsync(caseId);
        
        // Get permitted actions
        var actions = await _userService.GetPermittedActionsAsync(_currentUserId);
        
        // Show/hide features based on actions
        CanManageLegalProcesses = actions.Contains("ManageLegalProcesses");
        CanManageLeads = actions.Contains("ManageInvestigativeLeads");
        CanGenerateReport = actions.Contains("GenerateExaminationReport");
        CanApproveCase = actions.Contains("ApproveCases");
        
        // Render UI accordingly
        RenderLegalProcessesTab(CanManageLegalProcesses);
        RenderInvestigativeLeadsTab(CanManageLeads);
    }
}
```

---

## Security Considerations

### 1. Password Storage

✅ **Correct:** Use BCrypt for password hashing

```csharp
// When creating password
var passwordHash = BC.HashPassword(plainTextPassword);
user.PasswordHash = passwordHash;

// When verifying
if (BC.Verify(providedPassword, storedHash))
{
    // Password correct
}
```

### 2. Never Mix Roles

❌ **Wrong:** User can be both roles simultaneously

```csharp
// Don't do this:
user.Role = UserRole.Investigator | UserRole.Examiner;
```

✅ **Correct:** User has exactly one role

```csharp
// Do this:
user.Role = UserRole.Investigator;  // Single role
```

### 3. Immutable Username

✅ **Correct:** Username cannot be changed after creation

```csharp
public string Username { get; private set; }  // No setter
```

Rationale: Username appears in audit trails and changing it could obscure audit history.

### 4. Audit Trail Completeness

✅ **Always log:**
- Who created the user
- Who changed the role
- Why the role was changed
- When changes occurred
- All login attempts (successful and failed)

```csharp
_logger.LogWarning(
    "User '{Username}' role changed from '{OldRole}' to '{NewRole}' " +
    "by '{ChangedBy}'. Reason: {Reason}",
    user.Username, previousRole, newRole, changedBy, reason);
```

### 5. Account Lockout

✅ **Enable:** Automatic lockout after failed attempts

```csharp
private const int MaxFailedLoginAttempts = 5;
private const int LockoutDurationMinutes = 15;

// After 5 failed attempts, account locks for 15 minutes
```

### 6. Password Strength Validation

✅ **Always validate** before accepting password

```csharp
var validation = ValidatePasswordStrength(password);
if (!validation.IsValid)
    throw new ArgumentException(
        $"Password does not meet requirements: " +
        $"{string.Join("; ", validation.ValidationErrors)}");
```

### 7. Deactivation Instead of Deletion

✅ **Soft delete:** Mark as inactive rather than hard delete

```csharp
// Don't delete - deactivate
user.Deactivate(deactivatedBy, reason);

// User remains in audit trails but cannot log in
if (!user.IsActive)
    return null;  // Cannot authenticate
```

---

## Usage Examples

### Example 1: Creating a New Investigator

```csharp
var createCommand = new CreateUserCommand
{
    Username = "jane.investigator",
    Email = "jane@forensics.local",
    Password = "NewInvestigator@2024",
    FullName = "Jane Investigator",
    Department = "Major Crimes",
    Title = "Investigator",
    Role = UserRole.Investigator,
    CreatedBy = "admin"
};

try
{
    var newUser = await _userService.CreateUserAsync(createCommand);
    messageBox.Show($"User {newUser.Username} created successfully");
}
catch (ArgumentException ex)
{
    messageBox.Show($"Validation error: {ex.Message}");
}
```

### Example 2: Promoting Examiner to Investigator

```csharp
var userId = new Guid("...");
try
{
    var updatedUser = await _userService.ChangeRoleAsync(
        userId: userId,
        newRole: UserRole.Investigator,
        changedBy: "admin",
        reason: "Promotion based on performance review and test passage");
    
    messageBox.Show($"User {updatedUser.Username} promoted to Investigator");
    
    // Role change is now in RoleAuditHistory
    var history = await _userService.GetRoleHistoryAsync(userId);
    foreach (var entry in history)
    {
        logger.LogInformation(
            "{ChangedAt}: {User} changed from {PreviousRole} to {NewRole} ({Reason})",
            entry.ChangedAt, entry.ChangedBy, entry.PreviousRole, entry.NewRole, entry.Reason);
    }
}
catch (InvalidOperationException ex)
{
    messageBox.Show($"Cannot change role: {ex.Message}");
}
```

### Example 3: Handling Role-Based Access Denial

```csharp
public async Task ApproveLegalProcessAsync(Guid processId)
{
    var currentUserId = GetCurrentUserId();
    
    try
    {
        // This will throw if user is not Investigator
        await _userService.EnsureInvestigatorAccessAsync(
            currentUserId,
            "ApproveLegalProcess");
        
        var process = await _legalRepository.GetByIdAsync(processId);
        process.Approve();
        await _legalRepository.SaveChangesAsync();
        
        messageBox.Show("Legal process approved successfully");
    }
    catch (UnauthorizedAccessException ex)
    {
        // User tried to perform operation without required role
        logger.LogWarning(ex.Message);
        messageBox.Show(
            "You do not have permission to approve legal processes. " +
            "This feature is restricted to Investigator role.",
            "Access Denied");
    }
}
```

### Example 4: Resetting Admin Password

```csharp
try
{
    var user = await _userService.ResetPasswordAsync(
        userId: userId,
        resetBy: "admin");
    
    messageBox.Show(
        $"Password reset for {user.Username}. " +
        $"User must change password on next login.");
    
    // Send secure email with password reset link
    await _emailService.SendPasswordResetAsync(
        user.Email,
        user.Username,
        resetToken);
}
catch (InvalidOperationException ex)
{
    messageBox.Show($"Cannot reset password: {ex.Message}");
}
```

---

## Testing Scenarios

### Test 1: Investigator Can Create Legal Process

```csharp
[Test]
public async Task CreateLegalProcess_WithInvestigatorRole_Succeeds()
{
    // Arrange
    var investigator = await CreateUserWithRole(UserRole.Investigator);
    
    // Act
    var result = await _legalProcessService.CreateAsync(
        legalProcessData,
        investigator.Id);
    
    // Assert
    Assert.IsNotNull(result);
    Assert.AreEqual(legalProcessData.Description, result.Description);
}
```

### Test 2: Examiner Cannot Create Legal Process

```csharp
[Test]
public async Task CreateLegalProcess_WithExaminerRole_ThrowsUnauthorized()
{
    // Arrange
    var examiner = await CreateUserWithRole(UserRole.Examiner);
    
    // Act & Assert
    Assert.ThrowsAsync<UnauthorizedAccessException>(
        async () => await _legalProcessService.CreateAsync(
            legalProcessData,
            examiner.Id));
}
```

### Test 3: Role Change Audit Trail

```csharp
[Test]
public async Task ChangeRole_CreatesAuditEntry()
{
    // Arrange
    var user = await CreateUserWithRole(UserRole.Examiner);
    
    // Act
    await _userService.ChangeRoleAsync(
        user.Id,
        UserRole.Investigator,
        "admin",
        "Promotion test");
    
    // Assert
    var history = await _userService.GetRoleHistoryAsync(user.Id);
    Assert.AreEqual(2, history.Count);  // Initial creation + role change
    
    var latestEntry = history.Last();
    Assert.AreEqual(UserRole.Examiner, latestEntry.PreviousRole);
    Assert.AreEqual(UserRole.Investigator, latestEntry.NewRole);
    Assert.AreEqual("admin", latestEntry.ChangedBy);
    Assert.AreEqual("Promotion test", latestEntry.Reason);
}
```

### Test 4: Account Lockout After Failed Attempts

```csharp
[Test]
public async Task ValidateCredentials_AfterFiveFailedAttempts_LocksAccount()
{
    // Arrange
    var user = await CreateUserAsync("testuser");
    
    // Act - fail 5 times
    for (int i = 0; i < 5; i++)
    {
        var result = await _userService.ValidateCredentialsAsync("testuser", "wrongpassword");
        Assert.IsNull(result);
    }
    
    // Assert - Account is locked
    var lockedUser = await _userService.GetByUsernameAsync("testuser");
    Assert.IsTrue(lockedUser.IsLockedOut);
    Assert.IsNotNull(lockedUser.LockoutExpiresAt);
    
    // Try to login - should fail
    var loginResult = await _userService.ValidateCredentialsAsync("testuser", "correctpassword");
    Assert.IsNull(loginResult);
}
```

---

## Integration Checklist

- [ ] User.cs entity created with role enforcement
- [ ] IUserService interface created with feature lock methods
- [ ] UserService implementation complete with password security
- [ ] UserRepository created for persistence
- [ ] UserValidators created with FluentValidation
- [ ] Mappings created for DTOs
- [ ] Exceptions created for role-based errors
- [ ] DbContext updated with User DbSet and RoleAuditEntry
- [ ] Dependency injection configured in startup
- [ ] Existing services updated to call `EnsureInvestigatorAccessAsync`
- [ ] UI commands updated to check `CanPerformActionAsync`
- [ ] Authentication service updated to populate CurrentUser
- [ ] Logging configured for audit trail
- [ ] Unit tests written for role enforcement
- [ ] Integration tests written for role-based access control

---

## Related Files

- **User.cs** - Domain entity with role enforcement
- **IUserService.cs** - Service interface with feature lock methods
- **UserService.cs** - Service implementation with password security
- **UserRepository.cs** - EF Core persistence layer
- **UserValidators.cs** - FluentValidation validators
- **UserMappings.cs** - AutoMapper profiles and DTOs
- **UserExceptions.cs** - Custom exceptions for role-based access
- **UserManagement_DEBUG.md** - Debugging guide (generated separately)

---

## Next Steps

1. **Update DbContext** to include User and RoleAuditEntry DbSets
2. **Configure Dependency Injection** for UserService, UserRepository, validators
3. **Add migrations** for User and RoleAuditEntry tables
4. **Update existing services** to call role check methods
5. **Handle authentication** to populate current user context
6. **Build UI** for user management (admin-only feature)
7. **Run comprehensive tests** for role-based access control
8. **Deploy** with audit trail monitoring enabled

