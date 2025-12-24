import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Users, Settings, Shield, UserPlus, Trash2, Edit2, Check, X,
  Loader2, AlertCircle, ChevronLeft, History, Building2
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { adminService, UserListItem, OrganizationInfo } from '../services/adminService';

const ROLE_LABELS: Record<string, string> = {
  super_admin: 'Super Admin',
  org_admin: 'Org Admin',
  transformer: 'Transformer',
  reviewer: 'Reviewer',
  viewer: 'Viewer',
};

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  active: { label: 'Active', color: 'bg-green-100 text-green-700' },
  pending: { label: 'Pending', color: 'bg-amber-100 text-amber-700' },
  disabled: { label: 'Disabled', color: 'bg-gray-100 text-gray-700' },
};

const AdminPage: React.FC = () => {
  const { user, hasRole } = useAuth();
  const [activeTab, setActiveTab] = useState<'users' | 'org'>('users');
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [org, setOrg] = useState<OrganizationInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Invite modal state
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');
  const [isInviting, setIsInviting] = useState(false);
  const [inviteResult, setInviteResult] = useState<{ success: boolean; message: string; link?: string } | null>(null);

  // Edit user state
  const [editingUser, setEditingUser] = useState<string | null>(null);
  const [editRole, setEditRole] = useState('');
  const [editStatus, setEditStatus] = useState('');

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (activeTab === 'users') {
        const userList = await adminService.listUsers();
        setUsers(userList);
      } else {
        const orgData = await adminService.getOrganization();
        setOrg(orgData);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return;
    
    setIsInviting(true);
    setInviteResult(null);
    
    try {
      const result = await adminService.inviteUser(inviteEmail, inviteName || undefined, inviteRole);
      setInviteResult({
        success: true,
        message: 'User invited successfully',
        link: result.invite_url,
      });
      loadData();
    } catch (err: any) {
      setInviteResult({
        success: false,
        message: err.message || 'Failed to send invitation',
      });
    } finally {
      setIsInviting(false);
    }
  };

  const handleUpdateUser = async (userId: string) => {
    try {
      await adminService.updateUser(userId, {
        role: editRole || undefined,
        status: editStatus || undefined,
      });
      setEditingUser(null);
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteUser = async (userId: string, email: string) => {
    if (!confirm(`${email} kullanıcısını silmek istediğinizden emin misiniz?`)) return;
    
    try {
      await adminService.deleteUser(userId);
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUpdateOrgSettings = async (key: string, value: any) => {
    if (!org) return;
    try {
      await adminService.updateOrganizationSettings({ [key]: value });
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Link to="/" className="p-2 hover:bg-white rounded-lg transition-colors">
              <ChevronLeft className="w-5 h-5 text-gray-600" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
              <p className="text-gray-500">Manage users and organization settings</p>
            </div>
          </div>
          <Link
            to="/admin/audit"
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <History className="w-4 h-4" />
            Audit Logs
          </Link>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('users')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'users'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Users className="w-4 h-4" />
            Users
          </button>
          <button
            onClick={() => setActiveTab('org')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'org'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Building2 className="w-4 h-4" />
            Organization
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
        )}

        {/* Users Tab */}
        {!isLoading && activeTab === 'users' && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Users ({users.length})</h2>
              <button
                onClick={() => {
                  setShowInviteModal(true);
                  setInviteEmail('');
                  setInviteName('');
                  setInviteRole('viewer');
                  setInviteResult(null);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <UserPlus className="w-4 h-4" />
                Invite User
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Login</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-gray-900">{u.name || u.email.split('@')[0]}</p>
                          <p className="text-sm text-gray-500">{u.email}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {editingUser === u.id ? (
                          <select
                            value={editRole}
                            onChange={(e) => setEditRole(e.target.value)}
                            className="border border-gray-200 rounded-lg px-2 py-1 text-sm"
                          >
                            <option value="viewer">Viewer</option>
                            <option value="reviewer">Reviewer</option>
                            <option value="transformer">Transformer</option>
                            <option value="org_admin">Org Admin</option>
                            {hasRole(['super_admin']) && <option value="super_admin">Super Admin</option>}
                          </select>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded-lg text-sm">
                            <Shield className="w-3 h-3" />
                            {ROLE_LABELS[u.role] || u.role}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {editingUser === u.id ? (
                          <select
                            value={editStatus}
                            onChange={(e) => setEditStatus(e.target.value)}
                            className="border border-gray-200 rounded-lg px-2 py-1 text-sm"
                          >
                            <option value="active">Active</option>
                            <option value="pending">Pending</option>
                            <option value="disabled">Disabled</option>
                          </select>
                        ) : (
                          <span className={`px-2 py-1 rounded-lg text-sm ${STATUS_LABELS[u.status]?.color || 'bg-gray-100'}`}>
                            {STATUS_LABELS[u.status]?.label || u.status}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {u.last_login_at
                          ? new Date(u.last_login_at).toLocaleDateString('en-US', {
                              day: 'numeric',
                              month: 'short',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : 'Never logged in'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {u.id !== user?.id && (
                          <div className="flex items-center justify-end gap-2">
                            {editingUser === u.id ? (
                              <>
                                <button
                                  onClick={() => handleUpdateUser(u.id)}
                                  className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                                >
                                  <Check className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => setEditingUser(null)}
                                  className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={() => {
                                    setEditingUser(u.id);
                                    setEditRole(u.role);
                                    setEditStatus(u.status);
                                  }}
                                  className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                                >
                                  <Edit2 className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleDeleteUser(u.id, u.email)}
                                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Organization Tab */}
        {!isLoading && activeTab === 'org' && org && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Organization Settings</h2>
            
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Organization Name</label>
                <p className="text-lg text-gray-900">{org.name}</p>
              </div>

              <div className="border-t pt-6">
                <h3 className="text-md font-medium text-gray-900 mb-4">Security Settings</h3>
                
                <div className="space-y-4">
                  <label className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                    <div>
                      <p className="font-medium text-gray-900">Export Permission</p>
                      <p className="text-sm text-gray-500">Allow users to export data</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={org.settings?.export_allowed !== false}
                      onChange={(e) => handleUpdateOrgSettings('export_allowed', e.target.checked)}
                      className="w-5 h-5 text-blue-600 rounded"
                    />
                  </label>

                  <label className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                    <div>
                      <p className="font-medium text-gray-900">Reviewer Export Permission</p>
                      <p className="text-sm text-gray-500">Allow reviewers to export data</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={org.settings?.reviewer_can_export === true}
                      onChange={(e) => handleUpdateOrgSettings('reviewer_can_export', e.target.checked)}
                      className="w-5 h-5 text-blue-600 rounded"
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Invite Modal */}
        {showInviteModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Invite User</h3>
              
              {inviteResult ? (
                <div className={`p-4 rounded-xl mb-4 ${inviteResult.success ? 'bg-green-50' : 'bg-red-50'}`}>
                  <p className={inviteResult.success ? 'text-green-700' : 'text-red-700'}>
                    {inviteResult.message}
                  </p>
                  {inviteResult.link && (
                    <div className="mt-3 p-3 bg-amber-50 rounded-lg">
                      <p className="text-xs text-amber-700 mb-2">🔧 Dev Mode - Invite Link:</p>
                      <code className="text-xs break-all">{inviteResult.link}</code>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                    <input
                      type="email"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="user@company.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name (optional)</label>
                    <input
                      type="text"
                      value={inviteName}
                      onChange={(e) => setInviteName(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder="John Doe"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                    <select
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="viewer">Viewer</option>
                      <option value="reviewer">Reviewer</option>
                      <option value="transformer">Transformer</option>
                      <option value="org_admin">Org Admin</option>
                    </select>
                  </div>
                </div>
              )}

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowInviteModal(false)}
                  className="flex-1 py-2 px-4 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  {inviteResult ? 'Close' : 'Cancel'}
                </button>
                {!inviteResult && (
                  <button
                    onClick={handleInvite}
                    disabled={isInviting || !inviteEmail.trim()}
                    className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {isInviting ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                    Send Invite
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPage;

