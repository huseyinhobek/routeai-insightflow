import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowLeft, Building2, Users, Shield, Settings, Database, Activity, RefreshCw, Mail, Send, Check, X, ChevronDown, ChevronUp } from 'lucide-react';

interface Organization {
  id: string;
  name: string;
  settings: {
    export_formats?: string[];
    max_users?: number;
  };
  created_at: string;
  user_count?: number;
}

interface SystemStats {
  total_organizations: number;
  total_users: number;
  total_datasets: number;
  total_transforms: number;
  active_sessions: number;
}

interface UserInfo {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  org_id: string;
  org_name: string;
  created_at: string;
  last_login_at: string | null;
}

const SuperAdminPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
  const [sendingCredentials, setSendingCredentials] = useState(false);
  const [showUsers, setShowUsers] = useState(true);
  const [showOrgs, setShowOrgs] = useState(false);

  useEffect(() => {
    if (user?.role !== 'super_admin') {
      navigate('/');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [orgsRes, statsRes, usersRes] = await Promise.all([
        fetch('/sav-api/admin/organizations', { credentials: 'include' }),
        fetch('/sav-api/admin/system-stats', { credentials: 'include' }),
        fetch('/sav-api/admin/users/all', { credentials: 'include' })
      ]);

      if (orgsRes.ok) {
        const orgsData = await orgsRes.json();
        setOrganizations(orgsData);
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      if (usersRes.ok) {
        const usersData = await usersRes.json();
        setUsers(usersData);
      }
    } catch (err) {
      setError('Failed to load data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const toggleUserSelection = (userId: string) => {
    const newSelected = new Set(selectedUsers);
    if (newSelected.has(userId)) {
      newSelected.delete(userId);
    } else {
      newSelected.add(userId);
    }
    setSelectedUsers(newSelected);
  };

  const selectAllUsers = () => {
    if (selectedUsers.size === users.length) {
      setSelectedUsers(new Set());
    } else {
      setSelectedUsers(new Set(users.map(u => u.id)));
    }
  };

  const sendCredentialsToUser = async (userId: string) => {
    setSendingCredentials(true);
    setError(null);
    try {
      const res = await fetch(`/sav-api/admin/users/${userId}/send-credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ user_id: userId })
      });

      if (res.ok) {
        const data = await res.json();
        setSuccessMessage(`Credentials sent to ${data.email}`);
        setTimeout(() => setSuccessMessage(null), 5000);
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to send credentials');
      }
    } catch (err) {
      setError('Failed to send credentials');
    } finally {
      setSendingCredentials(false);
    }
  };

  const sendCredentialsToSelected = async () => {
    if (selectedUsers.size === 0) {
      setError('Please select at least one user');
      return;
    }

    setSendingCredentials(true);
    setError(null);
    try {
      const res = await fetch('/sav-api/admin/users/bulk-send-credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ user_ids: Array.from(selectedUsers) })
      });

      if (res.ok) {
        const data = await res.json();
        setSuccessMessage(data.message);
        setSelectedUsers(new Set());
        setTimeout(() => setSuccessMessage(null), 5000);
      } else {
        const err = await res.json();
        setError(err.detail || 'Failed to send credentials');
      }
    } catch (err) {
      setError('Failed to send credentials');
    } finally {
      setSendingCredentials(false);
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'super_admin': return 'bg-red-500/20 text-red-300 border-red-500/30';
      case 'org_admin': return 'bg-orange-500/20 text-orange-300 border-orange-500/30';
      case 'transformer': return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      case 'reviewer': return 'bg-green-500/20 text-green-300 border-green-500/30';
      default: return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500/20 text-green-300';
      case 'pending': return 'bg-yellow-500/20 text-yellow-300';
      case 'disabled': return 'bg-red-500/20 text-red-300';
      default: return 'bg-gray-500/20 text-gray-300';
    }
  };

  if (user?.role !== 'super_admin') {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="bg-black/30 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/')}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-white/70" />
              </button>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gradient-to-br from-red-500 to-orange-500 rounded-lg">
                  <Shield className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Super Admin Panel</h1>
                  <p className="text-sm text-white/60">System-wide management</p>
                </div>
              </div>
            </div>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-white"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-200 flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)}>
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {successMessage && (
          <div className="mb-6 p-4 bg-green-500/20 border border-green-500/30 rounded-lg text-green-200 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Check className="w-4 h-4" />
              {successMessage}
            </span>
            <button onClick={() => setSuccessMessage(null)}>
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* System Stats */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
          <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <Building2 className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats?.total_organizations ?? '-'}</p>
                <p className="text-sm text-white/60">Organizations</p>
              </div>
            </div>
          </div>
          <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <Users className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats?.total_users ?? '-'}</p>
                <p className="text-sm text-white/60">Total Users</p>
              </div>
            </div>
          </div>
          <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Database className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats?.total_datasets ?? '-'}</p>
                <p className="text-sm text-white/60">Datasets</p>
              </div>
            </div>
          </div>
          <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-500/20 rounded-lg">
                <Settings className="w-5 h-5 text-orange-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats?.total_transforms ?? '-'}</p>
                <p className="text-sm text-white/60">Transforms</p>
              </div>
            </div>
          </div>
          <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-cyan-500/20 rounded-lg">
                <Activity className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats?.active_sessions ?? '-'}</p>
                <p className="text-sm text-white/60">Active Sessions</p>
              </div>
            </div>
          </div>
        </div>

        {/* Users List */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl overflow-hidden mb-8">
          <div 
            className="p-4 border-b border-white/10 flex items-center justify-between cursor-pointer hover:bg-white/5"
            onClick={() => setShowUsers(!showUsers)}
          >
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Users className="w-5 h-5" />
              All Users ({users.length})
            </h2>
            <div className="flex items-center gap-3">
              {selectedUsers.size > 0 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    sendCredentialsToSelected();
                  }}
                  disabled={sendingCredentials}
                  className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 rounded-lg text-white text-sm font-medium disabled:opacity-50"
                >
                  <Send className={`w-4 h-4 ${sendingCredentials ? 'animate-pulse' : ''}`} />
                  Send Credentials to {selectedUsers.size} Users
                </button>
              )}
              {showUsers ? <ChevronUp className="w-5 h-5 text-white/60" /> : <ChevronDown className="w-5 h-5 text-white/60" />}
            </div>
          </div>
          
          {showUsers && (
            <>
              {loading ? (
                <div className="p-8 text-center">
                  <RefreshCw className="w-8 h-8 text-white/40 animate-spin mx-auto mb-2" />
                  <p className="text-white/60">Loading...</p>
                </div>
              ) : users.length === 0 ? (
                <div className="p-8 text-center text-white/60">
                  No users found.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-white/5">
                      <tr>
                        <th className="px-4 py-3 text-left">
                          <input
                            type="checkbox"
                            checked={selectedUsers.size === users.length && users.length > 0}
                            onChange={selectAllUsers}
                            className="w-4 h-4 rounded border-white/30 bg-white/10 text-blue-500"
                          />
                        </th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">User</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Role</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Organization</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Status</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Last Login</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/10">
                      {users.map((u) => (
                        <tr key={u.id} className="hover:bg-white/5">
                          <td className="px-4 py-3">
                            <input
                              type="checkbox"
                              checked={selectedUsers.has(u.id)}
                              onChange={() => toggleUserSelection(u.id)}
                              className="w-4 h-4 rounded border-white/30 bg-white/10 text-blue-500"
                            />
                          </td>
                          <td className="px-4 py-3">
                            <div>
                              <p className="font-medium text-white">{u.name || u.email.split('@')[0]}</p>
                              <p className="text-sm text-white/60">{u.email}</p>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getRoleBadgeColor(u.role)}`}>
                              {u.role.replace('_', ' ')}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-white/80 text-sm">
                            {u.org_name}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeColor(u.status)}`}>
                              {u.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-white/60 text-sm">
                            {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : 'Never'}
                          </td>
                          <td className="px-4 py-3">
                            <button
                              onClick={() => sendCredentialsToUser(u.id)}
                              disabled={sendingCredentials}
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-lg text-sm text-blue-300 transition-colors disabled:opacity-50"
                              title="Send login credentials via email"
                            >
                              <Mail className="w-3.5 h-3.5" />
                              Send Credentials
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>

        {/* Organizations List */}
        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl overflow-hidden">
          <div 
            className="p-4 border-b border-white/10 flex items-center justify-between cursor-pointer hover:bg-white/5"
            onClick={() => setShowOrgs(!showOrgs)}
          >
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Building2 className="w-5 h-5" />
              All Organizations ({organizations.length})
            </h2>
            {showOrgs ? <ChevronUp className="w-5 h-5 text-white/60" /> : <ChevronDown className="w-5 h-5 text-white/60" />}
          </div>
          
          {showOrgs && (
            <>
              {loading ? (
                <div className="p-8 text-center">
                  <RefreshCw className="w-8 h-8 text-white/40 animate-spin mx-auto mb-2" />
                  <p className="text-white/60">Loading...</p>
                </div>
              ) : organizations.length === 0 ? (
                <div className="p-8 text-center text-white/60">
                  No organizations found.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-white/5">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Organization</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">ID</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Users</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Export Formats</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Created</th>
                        <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/10">
                      {organizations.map((org) => (
                        <tr key={org.id} className="hover:bg-white/5">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-3">
                              <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-lg">
                                <Building2 className="w-4 h-4 text-white" />
                              </div>
                              <span className="font-medium text-white">{org.name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-white/60 font-mono text-sm">
                            {org.id.substring(0, 8)}...
                          </td>
                          <td className="px-4 py-3 text-white/80">
                            {org.user_count ?? '-'}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex gap-1 flex-wrap">
                              {org.settings?.export_formats?.map((fmt) => (
                                <span
                                  key={fmt}
                                  className="px-2 py-0.5 bg-white/10 rounded text-xs text-white/70"
                                >
                                  {fmt}
                                </span>
                              )) ?? <span className="text-white/40">-</span>}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-white/60 text-sm">
                            {new Date(org.created_at).toLocaleDateString()}
                          </td>
                          <td className="px-4 py-3">
                            <button className="px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">
                              Manage
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>

        {/* Quick Actions */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() => navigate('/admin')}
            className="p-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-colors text-left"
          >
            <div className="flex items-center gap-3 mb-2">
              <Users className="w-5 h-5 text-blue-400" />
              <span className="font-medium text-white">User Management</span>
            </div>
            <p className="text-sm text-white/60">Manage users in your organization</p>
          </button>
          
          <button
            onClick={() => navigate('/admin/audit')}
            className="p-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-colors text-left"
          >
            <div className="flex items-center gap-3 mb-2">
              <Activity className="w-5 h-5 text-green-400" />
              <span className="font-medium text-white">Audit Logs</span>
            </div>
            <p className="text-sm text-white/60">View system activity logs</p>
          </button>
          
          <button
            onClick={() => navigate('/')}
            className="p-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-colors text-left"
          >
            <div className="flex items-center gap-3 mb-2">
              <Database className="w-5 h-5 text-purple-400" />
              <span className="font-medium text-white">Dataset Analysis</span>
            </div>
            <p className="text-sm text-white/60">Return to main application</p>
          </button>
        </div>
      </main>
    </div>
  );
};

export default SuperAdminPage;
