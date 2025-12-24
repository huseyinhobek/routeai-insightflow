import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, BarChart2 } from 'lucide-react';

/**
 * VerifyPage - Legacy page, redirects to login
 * OTP verification is now handled in LoginPage
 */
const VerifyPage: React.FC = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect to login page - OTP verification is now inline
    navigate('/login', { replace: true });
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center p-4 bg-white/10 backdrop-blur-sm rounded-2xl mb-6">
            <BarChart2 className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Native Insight Studio</h1>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <div className="text-center py-8">
            <Loader2 className="w-16 h-16 text-blue-600 animate-spin mx-auto mb-6" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">Redirecting...</h2>
            <p className="text-gray-600">You are being redirected to the login page.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VerifyPage;

