/**
 * Session Management
 * Maneja la identidad del usuario (Mock)
 */
const Session = {
    getUserId() {
        return localStorage.getItem('poc_user_id') || 'user_123';
    },

    getUserRole() {
        return localStorage.getItem('poc_user_role') || 'employee';
    },

    setRole(role) {
        localStorage.setItem('poc_user_role', role);
    },

    clear() {
        localStorage.clear();
    }
};
