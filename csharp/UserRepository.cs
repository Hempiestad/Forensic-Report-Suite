using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using System.Threading.Tasks;
using ForensicReportWriter.Domain.Entities;
using ForensicReportWriter.Domain.Enums;
using ForensicReportWriter.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace ForensicReportWriter.Infrastructure.Repositories
{
    /// <summary>
    /// Repository for User entity persistence using Entity Framework Core.
    /// Implements the repository pattern for data access abstraction.
    /// </summary>
    public class UserRepository : IRepository<User>
    {
        private readonly ForensicDbContext _context;
        private readonly DbSet<User> _dbSet;

        public UserRepository(ForensicDbContext context)
        {
            _context = context ?? throw new ArgumentNullException(nameof(context));
            _dbSet = context.Set<User>();
        }

        /// <summary>
        /// Gets a user by their unique ID, including role audit history.
        /// </summary>
        public async Task<User> GetByIdAsync(Guid id)
        {
            return await _dbSet
                .Include(u => u.RoleAuditHistory)
                .FirstOrDefaultAsync(u => u.Id == id);
        }

        /// <summary>
        /// Gets the first user matching the specified condition.
        /// </summary>
        public async Task<User> FirstOrDefaultAsync(Expression<Func<User, bool>> predicate)
        {
            return await _dbSet
                .Include(u => u.RoleAuditHistory)
                .FirstOrDefaultAsync(predicate);
        }

        /// <summary>
        /// Gets all users matching the specified condition.
        /// </summary>
        public async Task<IList<User>> ListAsync(Expression<Func<User, bool>> predicate = null)
        {
            var query = _dbSet
                .Include(u => u.RoleAuditHistory)
                .AsQueryable();

            if (predicate != null)
                query = query.Where(predicate);

            return await query.ToListAsync();
        }

        /// <summary>
        /// Gets all users with pagination support.
        /// </summary>
        public async Task<(IList<User> Items, int Total)> GetPagedAsync(
            int pageNumber,
            int pageSize,
            Expression<Func<User, bool>> predicate = null,
            Expression<Func<User, object>> orderBy = null)
        {
            var query = _dbSet
                .Include(u => u.RoleAuditHistory)
                .AsQueryable();

            if (predicate != null)
                query = query.Where(predicate);

            var total = await query.CountAsync();

            if (orderBy != null)
                query = query.OrderBy(orderBy);

            var items = await query
                .Skip((pageNumber - 1) * pageSize)
                .Take(pageSize)
                .ToListAsync();

            return (items, total);
        }

        /// <summary>
        /// Adds a new user to the repository.
        /// </summary>
        public async Task AddAsync(User entity)
        {
            if (entity == null)
                throw new ArgumentNullException(nameof(entity));

            await _dbSet.AddAsync(entity);
        }

        /// <summary>
        /// Updates an existing user in the repository.
        /// </summary>
        public async Task UpdateAsync(User entity)
        {
            if (entity == null)
                throw new ArgumentNullException(nameof(entity));

            _dbSet.Update(entity);
            await Task.CompletedTask;
        }

        /// <summary>
        /// Deletes a user from the repository.
        /// Note: Users are typically soft-deleted (IsActive = false) for audit purposes.
        /// </summary>
        public async Task DeleteAsync(User entity)
        {
            if (entity == null)
                throw new ArgumentNullException(nameof(entity));

            _dbSet.Remove(entity);
            await Task.CompletedTask;
        }

        /// <summary>
        /// Checks if a user exists with the given ID.
        /// </summary>
        public async Task<bool> ExistsAsync(Guid id)
        {
            return await _dbSet.AnyAsync(u => u.Id == id);
        }

        /// <summary>
        /// Checks if a user exists matching the specified condition.
        /// </summary>
        public async Task<bool> ExistsAsync(Expression<Func<User, bool>> predicate)
        {
            return await _dbSet.AnyAsync(predicate);
        }

        /// <summary>
        /// Saves all pending changes to the database.
        /// </summary>
        public async Task SaveChangesAsync()
        {
            await _context.SaveChangesAsync();
        }

        // ===== Specialized Queries =====

        /// <summary>
        /// Gets a user by username.
        /// </summary>
        public async Task<User> GetByUsernameAsync(string username)
        {
            return await FirstOrDefaultAsync(u => u.Username == username);
        }

        /// <summary>
        /// Gets a user by email address.
        /// </summary>
        public async Task<User> GetByEmailAsync(string email)
        {
            return await FirstOrDefaultAsync(u => u.Email == email);
        }

        /// <summary>
        /// Gets all users with a specific role.
        /// </summary>
        public async Task<IList<User>> GetByRoleAsync(UserRole role)
        {
            return await ListAsync(u => u.Role == role);
        }

        /// <summary>
        /// Gets all active users.
        /// </summary>
        public async Task<IList<User>> GetActiveUsersAsync()
        {
            return await ListAsync(u => u.IsActive);
        }

        /// <summary>
        /// Gets all inactive (deactivated) users.
        /// </summary>
        public async Task<IList<User>> GetInactiveUsersAsync()
        {
            return await ListAsync(u => !u.IsActive);
        }

        /// <summary>
        /// Gets all locked out users.
        /// </summary>
        public async Task<IList<User>> GetLockedOutUsersAsync()
        {
            return await ListAsync(u => u.IsLockedOut);
        }

        /// <summary>
        /// Gets users by department.
        /// </summary>
        public async Task<IList<User>> GetByDepartmentAsync(string department)
        {
            return await ListAsync(u => u.Department == department && u.IsActive);
        }

        /// <summary>
        /// Gets users who haven't logged in for a specified number of days.
        /// Useful for identifying stale accounts that may need deactivation.
        /// </summary>
        public async Task<IList<User>> GetInactiveLoginUsersAsync(int days)
        {
            var cutoffDate = DateTime.UtcNow.AddDays(-days);
            return await ListAsync(u =>
                u.IsActive &&
                (u.LastLoginAt == null || u.LastLoginAt < cutoffDate));
        }

        /// <summary>
        /// Gets users who logged in within the specified hours.
        /// Useful for session monitoring and compliance reporting.
        /// </summary>
        public async Task<IList<User>> GetRecentLoginUsersAsync(int hours)
        {
            var cutoffDate = DateTime.UtcNow.AddHours(-hours);
            return await ListAsync(u =>
                u.IsActive &&
                u.LastLoginAt != null &&
                u.LastLoginAt > cutoffDate);
        }

        /// <summary>
        /// Gets count of users by role.
        /// </summary>
        public async Task<Dictionary<UserRole, int>> GetCountByRoleAsync()
        {
            var data = await _dbSet
                .Where(u => u.IsActive)
                .GroupBy(u => u.Role)
                .Select(g => new { Role = g.Key, Count = g.Count() })
                .ToListAsync();

            return data.ToDictionary(x => x.Role, x => x.Count);
        }

        /// <summary>
        /// Gets user statistics for administrative dashboard.
        /// </summary>
        public async Task<UserStatistics> GetStatisticsAsync()
        {
            var totalUsers = await _dbSet.CountAsync();
            var activeUsers = await _dbSet.CountAsync(u => u.IsActive);
            var inactiveUsers = totalUsers - activeUsers;
            var lockedOutUsers = await _dbSet.CountAsync(u => u.IsLockedOut);

            var loginStats = await _dbSet
                .GroupBy(u => new { IsLoggedIn = u.LastLoginAt != null })
                .Select(g => new { HasLogged = g.Key.IsLoggedIn, Count = g.Count() })
                .ToListAsync();

            var neverLoggedIn = loginStats.FirstOrDefault(x => !x.HasLogged)?.Count ?? 0;
            var hasLoggedIn = loginStats.FirstOrDefault(x => x.HasLogged)?.Count ?? 0;

            return new UserStatistics
            {
                TotalUsers = totalUsers,
                ActiveUsers = activeUsers,
                InactiveUsers = inactiveUsers,
                LockedOutUsers = lockedOutUsers,
                UsersNeverLoggedIn = neverLoggedIn,
                UsersWithLogins = hasLoggedIn,
                CountByRole = await GetCountByRoleAsync()
            };
        }

        /// <summary>
        /// Checks if a username is already taken.
        /// </summary>
        public async Task<bool> IsUsernameAvailableAsync(string username)
        {
            return !await ExistsAsync(u => u.Username == username);
        }

        /// <summary>
        /// Checks if an email is already registered.
        /// </summary>
        public async Task<bool> IsEmailAvailableAsync(string email)
        {
            return !await ExistsAsync(u => u.Email == email);
        }

        /// <summary>
        /// Gets the most recently created users (for new user monitoring).
        /// </summary>
        public async Task<IList<User>> GetRecentlyCreatedAsync(int count = 10)
        {
            return await _dbSet
                .OrderByDescending(u => u.CreatedAt)
                .Take(count)
                .Include(u => u.RoleAuditHistory)
                .ToListAsync();
        }

        /// <summary>
        /// Gets users who have recently changed their password.
        /// </summary>
        public async Task<IList<User>> GetRecentPasswordChangesAsync(int days = 30)
        {
            var cutoffDate = DateTime.UtcNow.AddDays(-days);
            return await ListAsync(u =>
                u.IsActive &&
                u.LastPasswordChangeAt != null &&
                u.LastPasswordChangeAt > cutoffDate);
        }

        /// <summary>
        /// Gets users whose password has never been changed (initial state or admin reset state).
        /// </summary>
        public async Task<IList<User>> GetNeverChangedPasswordAsync()
        {
            return await ListAsync(u =>
                u.IsActive &&
                u.LastPasswordChangeAt == null);
        }

        /// <summary>
        /// Searches users by name or email.
        /// </summary>
        public async Task<IList<User>> SearchAsync(string searchTerm)
        {
            if (string.IsNullOrWhiteSpace(searchTerm))
                return new List<User>();

            var term = searchTerm.ToLower().Trim();
            return await ListAsync(u =>
                u.IsActive &&
                (u.FullName.ToLower().Contains(term) ||
                 u.Username.ToLower().Contains(term) ||
                 u.Email.ToLower().Contains(term)));
        }
    }

    /// <summary>
    /// Statistics about users in the system for administrative dashboards.
    /// </summary>
    public class UserStatistics
    {
        public int TotalUsers { get; set; }
        public int ActiveUsers { get; set; }
        public int InactiveUsers { get; set; }
        public int LockedOutUsers { get; set; }
        public int UsersNeverLoggedIn { get; set; }
        public int UsersWithLogins { get; set; }
        public Dictionary<UserRole, int> CountByRole { get; set; } = new();
    }

    /// <summary>
    /// Generic repository interface used by repositories.
    /// </summary>
    public interface IRepository<TEntity> where TEntity : class
    {
        Task<TEntity> GetByIdAsync(Guid id);
        Task<TEntity> FirstOrDefaultAsync(Expression<Func<TEntity, bool>> predicate);
        Task<IList<TEntity>> ListAsync(Expression<Func<TEntity, bool>> predicate = null);
        Task<(IList<TEntity> Items, int Total)> GetPagedAsync(
            int pageNumber,
            int pageSize,
            Expression<Func<TEntity, bool>> predicate = null,
            Expression<Func<TEntity, object>> orderBy = null);
        Task AddAsync(TEntity entity);
        Task UpdateAsync(TEntity entity);
        Task DeleteAsync(TEntity entity);
        Task<bool> ExistsAsync(Guid id);
        Task<bool> ExistsAsync(Expression<Func<TEntity, bool>> predicate);
        Task SaveChangesAsync();
    }
}
