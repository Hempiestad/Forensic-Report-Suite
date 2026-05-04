using System;
using System.Text.RegularExpressions;
using FluentValidation;
using ForensicReportWriter.Application.Interfaces;
using ForensicReportWriter.Domain.Enums;

namespace ForensicReportWriter.Application.Validators
{
    /// <summary>
    /// Validator for CreateUserCommand.
    /// Ensures all user creation input meets business rules and security requirements.
    /// </summary>
    public class CreateUserCommandValidator : AbstractValidator<CreateUserCommand>
    {
        public CreateUserCommandValidator()
        {
            RuleFor(x => x.Username)
                .NotEmpty()
                .WithMessage("Username is required")
                .Length(3, 50)
                .WithMessage("Username must be between 3 and 50 characters")
                .Matches(@"^[a-zA-Z0-9._]+$")
                .WithMessage("Username can only contain letters, digits, periods, and underscores")
                .Must(BeValidUsername)
                .WithMessage("Username cannot start or end with a period");

            RuleFor(x => x.Email)
                .NotEmpty()
                .WithMessage("Email is required")
                .EmailAddress()
                .WithMessage("Email must be in valid format")
                .Length(5, 254)
                .WithMessage("Email must be between 5 and 254 characters");

            RuleFor(x => x.Password)
                .NotEmpty()
                .WithMessage("Password is required")
                .Length(8, 128)
                .WithMessage("Password must be between 8 and 128 characters")
                .Must(ContainUppercase)
                .WithMessage("Password must contain at least one uppercase letter")
                .Must(ContainLowercase)
                .WithMessage("Password must contain at least one lowercase letter")
                .Must(ContainDigit)
                .WithMessage("Password must contain at least one digit")
                .Must(ContainSpecialCharacter)
                .WithMessage("Password must contain at least one special character (!@#$%^&*-_)");

            RuleFor(x => x.FullName)
                .NotEmpty()
                .WithMessage("Full name is required")
                .Length(2, 100)
                .WithMessage("Full name must be between 2 and 100 characters")
                .Matches(@"^[a-zA-Z\s\-'.]+$")
                .WithMessage("Full name can only contain letters, spaces, hyphens, and apostrophes");

            RuleFor(x => x.Department)
                .NotEmpty()
                .WithMessage("Department is required")
                .Length(2, 100)
                .WithMessage("Department must be between 2 and 100 characters");

            RuleFor(x => x.Title)
                .NotEmpty()
                .WithMessage("Title is required")
                .Length(2, 100)
                .WithMessage("Title must be between 2 and 100 characters");

            RuleFor(x => x.Role)
                .IsInEnum()
                .WithMessage("Role must be a valid enum value");

            RuleFor(x => x.CreatedBy)
                .NotEmpty()
                .WithMessage("CreatedBy is required");
        }

        private static bool BeValidUsername(string username)
        {
            if (string.IsNullOrWhiteSpace(username))
                return false;

            return !username.StartsWith(".") && !username.EndsWith(".");
        }

        private static bool ContainUppercase(string password)
        {
            return !string.IsNullOrEmpty(password) && Regex.IsMatch(password, "[A-Z]");
        }

        private static bool ContainLowercase(string password)
        {
            return !string.IsNullOrEmpty(password) && Regex.IsMatch(password, "[a-z]");
        }

        private static bool ContainDigit(string password)
        {
            return !string.IsNullOrEmpty(password) && Regex.IsMatch(password, "[0-9]");
        }

        private static bool ContainSpecialCharacter(string password)
        {
            return !string.IsNullOrEmpty(password) && Regex.IsMatch(password, "[!@#$%^&*\\-_]");
        }
    }

    /// <summary>
    /// Validator for UpdateUserProfileCommand.
    /// Ensures user profile updates meet business rules.
    /// </summary>
    public class UpdateUserProfileCommandValidator : AbstractValidator<UpdateUserProfileCommand>
    {
        public UpdateUserProfileCommandValidator()
        {
            RuleFor(x => x.UserId)
                .NotEmpty()
                .WithMessage("UserId is required");

            RuleFor(x => x.Email)
                .NotEmpty()
                .WithMessage("Email is required")
                .EmailAddress()
                .WithMessage("Email must be in valid format")
                .Length(5, 254)
                .WithMessage("Email must be between 5 and 254 characters");

            RuleFor(x => x.FullName)
                .NotEmpty()
                .WithMessage("Full name is required")
                .Length(2, 100)
                .WithMessage("Full name must be between 2 and 100 characters")
                .Matches(@"^[a-zA-Z\s\-'.]+$")
                .WithMessage("Full name can only contain letters, spaces, hyphens, and apostrophes");

            RuleFor(x => x.Department)
                .NotEmpty()
                .WithMessage("Department is required")
                .Length(2, 100)
                .WithMessage("Department must be between 2 and 100 characters");

            RuleFor(x => x.Title)
                .NotEmpty()
                .WithMessage("Title is required")
                .Length(2, 100)
                .WithMessage("Title must be between 2 and 100 characters");

            RuleFor(x => x.UpdatedBy)
                .NotEmpty()
                .WithMessage("UpdatedBy is required");
        }
    }

    /// <summary>
    /// Validator for password change requests.
    /// Ensures new passwords meet complexity requirements.
    /// </summary>
    public class ChangePasswordCommandValidator : AbstractValidator<ChangePasswordCommand>
    {
        public ChangePasswordCommandValidator()
        {
            RuleFor(x => x.UserId)
                .NotEmpty()
                .WithMessage("UserId is required");

            RuleFor(x => x.CurrentPassword)
                .NotEmpty()
                .WithMessage("Current password is required");

            RuleFor(x => x.NewPassword)
                .NotEmpty()
                .WithMessage("New password is required")
                .Length(8, 128)
                .WithMessage("Password must be between 8 and 128 characters")
                .Must(ContainUppercase)
                .WithMessage("Password must contain at least one uppercase letter")
                .Must(ContainLowercase)
                .WithMessage("Password must contain at least one lowercase letter")
                .Must(ContainDigit)
                .WithMessage("Password must contain at least one digit")
                .Must(ContainSpecialCharacter)
                .WithMessage("Password must contain at least one special character (!@#$%^&*-_)")
                .Must((cmd, newPassword) => cmd.CurrentPassword != newPassword)
                .WithMessage("New password must be different from current password");
        }

        private static bool ContainUppercase(string password)
        {
            return !string.IsNullOrEmpty(password) && Regex.IsMatch(password, "[A-Z]");
        }

        private static bool ContainLowercase(string password)
        {
            return !string.IsNullOrEmpty(password) && Regex.IsMatch(password, "[a-z]");
        }

        private static bool ContainDigit(string password)
        {
            return !string.IsNullOrEmpty(password) && Regex.IsMatch(password, "[0-9]");
        }

        private static bool ContainSpecialCharacter(string password)
        {
            return !string.IsNullOrEmpty(password) && Regex.IsMatch(password, "[!@#$%^&*\\-_]");
        }
    }

    /// <summary>
    /// Validator for role change operations.
    /// Ensures role assignments are valid and properly authorized.
    /// </summary>
    public class ChangeRoleCommandValidator : AbstractValidator<ChangeRoleCommand>
    {
        public ChangeRoleCommandValidator()
        {
            RuleFor(x => x.UserId)
                .NotEmpty()
                .WithMessage("UserId is required");

            RuleFor(x => x.NewRole)
                .IsInEnum()
                .WithMessage("Role must be a valid enum value");

            RuleFor(x => x.ChangedBy)
                .NotEmpty()
                .WithMessage("ChangedBy is required");

            RuleFor(x => x.Reason)
                .NotEmpty()
                .WithMessage("Reason for role change is required")
                .Length(5, 500)
                .WithMessage("Reason must be between 5 and 500 characters");
        }
    }

    /// <summary>
    /// DTO for password change command.
    /// </summary>
    public class ChangePasswordCommand
    {
        public Guid UserId { get; set; }
        public string CurrentPassword { get; set; }
        public string NewPassword { get; set; }
    }

    /// <summary>
    /// DTO for role change command.
    /// </summary>
    public class ChangeRoleCommand
    {
        public Guid UserId { get; set; }
        public UserRole NewRole { get; set; }
        public string ChangedBy { get; set; }
        public string Reason { get; set; }
    }
}
