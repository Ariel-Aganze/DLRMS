// Enhanced User Management JavaScript for DLRMS Dashboard

class UserManagement {
    constructor() {
        this.isUserManagementVisible = false;
        this.init();
    }

    init() {
        // Initialize event listeners
        this.setupEventListeners();
        
        // Load initial data if user management is shown
        if (document.getElementById('user-management-section')) {
            this.loadUserStats();
        }
    }

    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('user-search');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.searchUsers(e.target.value);
                }, 300);
            });
        }

        // Filter functionality
        const roleFilter = document.getElementById('role-filter');
        const statusFilter = document.getElementById('status-filter');
        
        if (roleFilter) {
            roleFilter.addEventListener('change', () => this.filterUsers());
        }
        
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.filterUsers());
        }
    }

    showUserManagement() {
        const userManagementSection = document.getElementById('user-management-section');
        const landownerContent = document.getElementById('landowner-content');
        
        if (userManagementSection && landownerContent) {
            if (userManagementSection.classList.contains('hidden')) {
                userManagementSection.classList.remove('hidden');
                landownerContent.style.display = 'none';
                this.isUserManagementVisible = true;
                this.loadUserStats();
            } else {
                userManagementSection.classList.add('hidden');
                landownerContent.style.display = 'block';
                this.isUserManagementVisible = false;
            }
        }
    }

    async loadUserStats() {
        try {
            const response = await fetch('/admin/user-stats/', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.updateStatsDisplay(data.stats);
            }
        } catch (error) {
            console.error('Error loading user stats:', error);
        }
    }

    updateStatsDisplay(stats) {
        // Update stats cards if they exist
        const statsElements = {
            'total_users': document.querySelector('[data-stat="total_users"]'),
            'verified_users': document.querySelector('[data-stat="verified_users"]'),
            'unverified_users': document.querySelector('[data-stat="unverified_users"]'),
            'total_landowners': document.querySelector('[data-stat="total_landowners"]'),
            'total_officers': document.querySelector('[data-stat="total_officers"]')
        };

        Object.keys(statsElements).forEach(key => {
            if (statsElements[key] && stats[key] !== undefined) {
                statsElements[key].textContent = stats[key];
            }
        });
    }

    async verifyUser(userId) {
        if (!confirm('Are you sure you want to verify this user?')) {
            return;
        }

        try {
            const response = await fetch(`/admin/verify-user/${userId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showMessage(data.message, 'success');
                this.refreshUserRow(userId);
                this.loadUserStats();
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            console.error('Error verifying user:', error);
            this.showMessage('An error occurred while verifying the user.', 'error');
        }
    }

    async toggleUserActive(userId, isActive) {
        const action = isActive ? 'deactivate' : 'activate';
        if (!confirm(`Are you sure you want to ${action} this user?`)) {
            return;
        }

        try {
            const response = await fetch(`/admin/toggle-user-active/${userId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showMessage(data.message, 'success');
                this.refreshUserRow(userId);
                this.loadUserStats();
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            console.error('Error toggling user status:', error);
            this.showMessage('An error occurred while updating the user status.', 'error');
        }
    }

    async bulkVerifyUsers() {
        if (!confirm('This will verify all unverified users. Are you sure?')) {
            return;
        }

        try {
            const response = await fetch('/admin/bulk-verify-users/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.showMessage(data.message, 'success');
                this.refreshUserList();
                this.loadUserStats();
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            console.error('Error in bulk verification:', error);
            this.showMessage('An error occurred during bulk verification.', 'error');
        }
    }

    async searchUsers(query) {
        const roleFilter = document.getElementById('role-filter')?.value || '';
        const statusFilter = document.getElementById('status-filter')?.value || '';

        try {
            const params = new URLSearchParams({
                q: query,
                role: roleFilter,
                status: statusFilter
            });

            const response = await fetch(`/admin/search-users/?${params}`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            
            if (data.success) {
                this.updateUserTable(data.users);
            } else {
                this.showMessage(data.message, 'error');
            }
        } catch (error) {
            console.error('Error searching users:', error);
            this.showMessage('An error occurred while searching users.', 'error');
        }
    }

    filterUsers() {
        const searchQuery = document.getElementById('user-search')?.value || '';
        this.searchUsers(searchQuery);
    }

    updateUserTable(users) {
        const tbody = document.getElementById('user-list-tbody');
        if (!tbody) return;

        if (users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-4 text-center text-gray-500">No users found</td></tr>';
            return;
        }

        tbody.innerHTML = users.map(user => this.generateUserRow(user)).join('');
    }

    generateUserRow(user) {
        const roleClasses = {
            'admin': 'bg-purple-100 text-purple-800',
            'registry_officer': 'bg-blue-100 text-blue-800',
            'surveyor': 'bg-green-100 text-green-800',
            'notary': 'bg-orange-100 text-orange-800',
            'landowner': 'bg-gray-100 text-gray-800'
        };

        const verificationStatus = user.is_verified 
            ? '<span class="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">✓ Verified</span>'
            : '<span class="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">⚠ Pending</span>';

        const activeStatus = user.is_active 
            ? '' 
            : '<span class="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800 ml-1">Inactive</span>';

        const actions = [
            `<a href="/admin/accounts/user/${user.id}/change/" class="text-blue-600 hover:text-blue-900">Edit</a>`
        ];

        if (!user.is_verified) {
            actions.push(`<button onclick="userManagement.verifyUser(${user.id})" class="text-green-600 hover:text-green-900">Verify</button>`);
        }

        if (user.is_active) {
            actions.push(`<button onclick="userManagement.toggleUserActive(${user.id}, true)" class="text-red-600 hover:text-red-900">Deactivate</button>`);
        } else {
            actions.push(`<button onclick="userManagement.toggleUserActive(${user.id}, false)" class="text-green-600 hover:text-green-900">Activate</button>`);
        }

        return `
            <tr class="hover:bg-gray-50" data-user-id="${user.id}">
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        <div class="flex-shrink-0 h-8 w-8">
                            <div class="h-8 w-8 bg-blue-600 rounded-full flex items-center justify-center">
                                <span class="text-xs font-medium text-white">
                                    ${user.first_name.charAt(0)}${user.last_name.charAt(0)}
                                </span>
                            </div>
                        </div>
                        <div class="ml-3">
                            <div class="text-sm font-medium text-gray-900">
                                ${user.first_name} ${user.last_name}
                            </div>
                            <div class="text-sm text-gray-500">${user.email}</div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex px-2 py-1 text-xs font-medium rounded-full ${roleClasses[user.role] || 'bg-gray-100 text-gray-800'}">
                        ${user.role_display}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        ${verificationStatus}
                        ${activeStatus}
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${user.date_joined}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div class="flex gap-2">
                        ${actions.join('')}
                    </div>
                </td>
            </tr>
        `;
    }

    refreshUserRow(userId) {
        // In a real implementation, you would fetch the updated user data
        // For now, we'll just refresh the entire list
        this.refreshUserList();
    }

    refreshUserList() {
        const searchQuery = document.getElementById('user-search')?.value || '';
        this.searchUsers(searchQuery);
    }

    exportUsers() {
        // Trigger CSV export
        window.location.href = '/admin/export-users/';
    }

    showMessage(message, type = 'info') {
        // Create and show a temporary message
        const messageDiv = document.createElement('div');
        messageDiv.className = `fixed top-4 right-4 px-4 py-2 rounded-lg text-white z-50 ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 
            'bg-blue-500'
        }`;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            messageDiv.remove();
        }, 5000);
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Initialize user management when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.userManagement = new UserManagement();
});

// Legacy functions for backward compatibility
function showUserManagement() {
    if (window.userManagement) {
        window.userManagement.showUserManagement();
    }
}

function refreshUserList() {
    if (window.userManagement) {
        window.userManagement.refreshUserList();
    }
}

function verifyUser(userId) {
    if (window.userManagement) {
        window.userManagement.verifyUser(userId);
    }
}

function deactivateUser(userId) {
    if (window.userManagement) {
        window.userManagement.toggleUserActive(userId, true);
    }
}

function activateUser(userId) {
    if (window.userManagement) {
        window.userManagement.toggleUserActive(userId, false);
    }
}

function bulkVerifyUsers() {
    if (window.userManagement) {
        window.userManagement.bulkVerifyUsers();
    }
}

function exportUsers() {
    if (window.userManagement) {
        window.userManagement.exportUsers();
    }
}