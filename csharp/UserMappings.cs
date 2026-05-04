using System.Collections.Generic;
using AutoMapper;
using ForensicReportWriter.Application.Interfaces;
using ForensicReportWriter.Domain.Entities;

namespace ForensicReportWriter.Application.Mappings
{
    /// <summary>
    /// AutoMapper profile for User entity and data transfer objects.
    /// Handles mapping between domain entities and DTOs for API/service boundaries.
    /// </summary>
    public class UserMappingProfile : Profile
    {
        public UserMappingProfile()
        {
            // User entity to export DTO (read-only, no sensitive data)
            CreateMap<User, UserExportDto>()
                .ForMember(
                    dest => dest.UserId,
                    opt => opt.MapFrom(src => src.Id))
                .ReverseMap()
                .ForMember(dest => dest.Id, opt => opt.MapFrom(src => src.UserId));

            // User entity to profile DTO (public-facing user info)
            CreateMap<User, UserProfileDto>()
                .ForMember(
                    dest => dest.UserId,
                    opt => opt.MapFrom(src => src.Id));

            // User entity to detailed admin DTO (full info for admin dashboards)
            CreateMap<User, UserDetailedDto>()
                .ForMember(
                    dest => dest.UserId,
                    opt => opt.MapFrom(src => src.Id))
                .ForMember(
                    dest => dest.RoleAuditHistory,
                    opt => opt.MapFrom(src => src.RoleAuditHistory));

            // Role audit entry mapping
            CreateMap<RoleAuditEntry, RoleAuditEntryDto>()
                .ReverseMap();
        }
    }

    /// <summary>
    /// DTO for public-facing user profile information.
    /// Does not expose sensitive fields like password hash or failed login attempts.
    /// </summary>
    public class UserProfileDto
    {
        public string Username { get; set; }
        public string Email { get; set; }
        public string FullName { get; set; }
        public string Department { get; set; }
        public string Title { get; set; }
        public bool IsActive { get; set; }
    }

    /// <summary>
    /// DTO for detailed user information in admin dashboards.
    /// Includes security-related information for administrative purposes.
    /// Must be restricted to authorized admin users.
    /// </summary>
    public class UserDetailedDto
    {
        public System.Guid UserId { get; set; }
        public string Username { get; set; }
        public string Email { get; set; }
        public string FullName { get; set; }
        public string Department { get; set; }
        public string Title { get; set; }
        public string Role { get; set; }
        public bool IsActive { get; set; }
        public bool IsLockedOut { get; set; }
        public int FailedLoginAttempts { get; set; }
        public System.DateTime CreatedAt { get; set; }
        public string CreatedBy { get; set; }
        public System.DateTime UpdatedAt { get; set; }
        public string UpdatedBy { get; set; }
        public System.DateTime? LastLoginAt { get; set; }
        public System.DateTime? LastPasswordChangeAt { get; set; }
        public bool MustChangePasswordOnLogin { get; set; }
        public List<RoleAuditEntryDto> RoleAuditHistory { get; set; }
    }

    /// <summary>
    /// DTO for role audit trail entries.
    /// Used in compliance and security audits.
    /// </summary>
    public class RoleAuditEntryDto
    {
        public System.Guid Id { get; set; }
        public System.Guid UserId { get; set; }
        public string PreviousRole { get; set; }
        public string NewRole { get; set; }
        public System.DateTime ChangedAt { get; set; }
        public string ChangedBy { get; set; }
        public string Reason { get; set; }
    }

    /// <summary>
    /// Interface for mapper operations.
    /// Provides abstraction for AutoMapper operations.
    /// </summary>
    public interface IMapper
    {
        TDestination Map<TSource, TDestination>(TSource source);
        TDestination Map<TSource, TDestination>(TSource source, Action<IMappingOperationOptions<TSource, TDestination>> opts);
        IList<TDestination> MapList<TSource, TDestination>(IList<TSource> source);
    }

    /// <summary>
    /// Mapper implementation using AutoMapper.
    /// </summary>
    public class MapperAdapter : IMapper
    {
        private readonly IMapper _autoMapper;

        public MapperAdapter(IMapper autoMapper)
        {
            _autoMapper = autoMapper ?? throw new System.ArgumentNullException(nameof(autoMapper));
        }

        public TDestination Map<TSource, TDestination>(TSource source)
        {
            return _autoMapper.Map<TSource, TDestination>(source);
        }

        public TDestination Map<TSource, TDestination>(
            TSource source,
            Action<IMappingOperationOptions<TSource, TDestination>> opts)
        {
            return _autoMapper.Map<TSource, TDestination>(source, opts);
        }

        public IList<TDestination> MapList<TSource, TDestination>(IList<TSource> source)
        {
            return _autoMapper.Map<IList<TSource>, IList<TDestination>>(source);
        }
    }
}
