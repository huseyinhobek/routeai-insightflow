import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Mail, Lock, Loader2, ArrowRight, CheckCircle, AlertCircle, BarChart2, KeyRound, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [otpCode, setOtpCode] = useState(['', '', '', '', '', '']);
  const [step, setStep] = useState<'credentials' | 'otp'>('credentials');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [devOtpCode, setDevOtpCode] = useState<string | null>(null);

  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);
  const { login, verify, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email.trim()) {
      setError('Please enter your email address');
      return;
    }

    if (!password) {
      setError('Please enter your password');
      return;
    }

    setIsLoading(true);
    setError(null);

    const result = await login(email.trim(), password);

    setIsLoading(false);

    if (result.success) {
      // Check if OTP is required (demo accounts skip OTP)
      if (result.requiresOtp === false && result.user) {
        // Direct login success - redirect to home
        const from = (location.state as any)?.from?.pathname || '/';
        navigate(from, { replace: true });
      } else {
        // OTP required
        setStep('otp');
        if (result.otpCode) {
          setDevOtpCode(result.otpCode);
        }
      }
    } else {
      setError(result.message);
    }
  };

  const handleOtpChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return; // Only allow digits

    const newOtp = [...otpCode];
    newOtp[index] = value.slice(-1); // Only take last digit
    setOtpCode(newOtp);

    // Auto-focus next input
    if (value && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otpCode[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
  };

  const handleOtpPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    const newOtp = [...otpCode];
    for (let i = 0; i < pastedData.length; i++) {
      newOtp[i] = pastedData[i];
    }
    setOtpCode(newOtp);
    if (pastedData.length === 6) {
      otpRefs.current[5]?.focus();
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const code = otpCode.join('');
    if (code.length !== 6) {
      setError('Please enter the 6-digit verification code');
      return;
    }

    setIsLoading(true);
    setError(null);

    const result = await verify(email, code);

    setIsLoading(false);

    if (result.success) {
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } else {
      setError(result.message);
    }
  };

  const handleDevAutoFill = () => {
    if (devOtpCode) {
      const digits = devOtpCode.split('');
      setOtpCode(digits);
      // UX: son haneye focus (akış bozmadan)
      otpRefs.current[5]?.focus();
    }
  };

  return (
    <div className="relative isolate min-h-screen overflow-hidden bg-slate-950 flex items-center justify-center p-6">
      {/* Ambient background layers */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-48 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute -bottom-56 right-[-120px] h-[560px] w-[560px] rounded-full bg-indigo-500/20 blur-3xl" />
        <div className="absolute inset-0 bg-[radial-gradient(1000px_500px_at_50%_0%,rgba(59,130,246,0.20),transparent_60%),radial-gradient(800px_400px_at_80%_60%,rgba(99,102,241,0.18),transparent_55%)]" />
        <div className="absolute inset-0 opacity-[0.06] [background-image:linear-gradient(to_right,white_1px,transparent_1px),linear-gradient(to_bottom,white_1px,transparent_1px)] [background-size:56px_56px]" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center mb-6">
            <div className="rounded-2xl bg-white/10 backdrop-blur-xl border border-white/15 shadow-xl px-5 py-4">
              <img src="/aletheia-logo.png" alt="Aletheia" className="h-12 w-auto" />
            </div>
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-white">
            {step === 'credentials' ? 'Welcome back' : 'Two-factor verification'}
          </h1>
          <p className="mt-2 text-sm text-blue-100/80">
            {step === 'credentials' ? 'Sign in to your account' : 'Enter the code sent to your email'}
          </p>
        </div>

        {/* Card */}
        <div className="bg-white/95 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl p-8 ring-1 ring-black/5">
          {step === 'credentials' ? (
            <form onSubmit={handleCredentialsSubmit} className="space-y-5">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-2">
                  Email Address
                </label>

                <div className="group relative">
                  <div className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-blue-600">
                    <Mail className="w-5 h-5" />
                  </div>

                  <input
                    type="email"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="ornek@sirket.com"
                    className="w-full pl-11 pr-4 py-3.5 rounded-2xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 shadow-sm
                               focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition disabled:opacity-60"
                    disabled={isLoading}
                    autoComplete="email"
                    autoFocus
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-2">
                  Password
                </label>

                <div className="group relative">
                  <div className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-blue-600">
                    <Lock className="w-5 h-5" />
                  </div>

                  <input
                    type={showPassword ? 'text' : 'password'}
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-11 pr-12 py-3.5 rounded-2xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 shadow-sm
                               focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition disabled:opacity-60"
                    disabled={isLoading}
                    autoComplete="current-password"
                  />

                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 rounded-xl p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition disabled:opacity-60"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    disabled={isLoading}
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {error && (
                <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-2xl">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full inline-flex items-center justify-center gap-2 py-3.5 px-4 rounded-2xl font-semibold text-white
                           bg-gradient-to-r from-blue-600 to-indigo-600 shadow-lg shadow-blue-600/20
                           hover:from-blue-700 hover:to-indigo-700
                           focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:ring-offset-2 focus:ring-offset-white
                           transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Kontrol ediliyor...
                  </>
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>

              <div className="pt-1">
                <p className="text-xs text-slate-500 text-center">
                  By continuing, you agree to the security verification on every sign in.
                </p>
              </div>
            </form>
          ) : (
            <form onSubmit={handleOtpSubmit} className="space-y-6">
              <div className="text-center">
                <div className="mx-auto mb-3 w-12 h-12 rounded-2xl bg-blue-600/10 border border-blue-600/15 flex items-center justify-center">
                  <KeyRound className="w-6 h-6 text-blue-700" />
                </div>

                <p className="text-sm text-slate-600">
                  We sent a 6-digit verification code to{' '}
                  <span className="font-semibold text-slate-900 break-all">{email}</span>.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-3 text-center">
                  Verification Code
                </label>

                <div className="flex gap-2 justify-center" onPaste={handleOtpPaste}>
                  {otpCode.map((digit, index) => (
                    <input
                      key={index}
                      ref={(el) => (otpRefs.current[index] = el)}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      onChange={(e) => handleOtpChange(index, e.target.value)}
                      onKeyDown={(e) => handleOtpKeyDown(index, e)}
                      className="w-12 h-14 text-center text-2xl font-bold rounded-2xl
                                 border border-slate-200 bg-white text-slate-900 shadow-sm
                                 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400
                                 transition disabled:opacity-60"
                      disabled={isLoading}
                      autoFocus={index === 0}
                      aria-label={`OTP digit ${index + 1}`}
                    />
                  ))}
                </div>

                <p className="mt-2 text-xs text-slate-500 text-center">
                  Tip: You can paste the full 6-digit code.
                </p>
              </div>

              {error && (
                <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-2xl">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              {/* Dev mode OTP */}
              {devOtpCode && (
                <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl">
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <p className="text-sm text-amber-900 font-semibold">Geliştirici Modu</p>
                    <span className="text-[11px] px-2 py-1 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                      Email disabled
                    </span>
                  </div>

                  <p className="text-xs text-amber-800 mb-2">Verification code:</p>

                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-lg font-mono font-bold text-amber-900 bg-amber-100 px-3 py-2 rounded-xl text-center tracking-widest border border-amber-200">
                      {devOtpCode}
                    </code>

                    <button
                      type="button"
                      onClick={handleDevAutoFill}
                      className="px-3 py-2 rounded-xl bg-amber-700 text-white text-sm font-semibold
                                 hover:bg-amber-800 transition disabled:opacity-60"
                      disabled={isLoading}
                    >
                      Doldur
                    </button>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading || otpCode.join('').length !== 6}
                className="w-full inline-flex items-center justify-center gap-2 py-3.5 px-4 rounded-2xl font-semibold text-white
                           bg-gradient-to-r from-blue-600 to-indigo-600 shadow-lg shadow-blue-600/20
                           hover:from-blue-700 hover:to-indigo-700
                           focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:ring-offset-2 focus:ring-offset-white
                           transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    Sign In
                  </>
                )}
              </button>

              <div className="text-center">
                <button
                  type="button"
                  onClick={() => {
                    setStep('credentials');
                    setOtpCode(['', '', '', '', '', '']);
                    setError(null);
                    setDevOtpCode(null);
                  }}
                  className="inline-flex items-center justify-center rounded-xl px-3 py-2 text-sm font-semibold text-blue-700
                             hover:bg-blue-50 transition"
                  disabled={isLoading}
                >
                  ← Go back
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-blue-100/80 text-sm mt-8">
          For your security, we send a verification code to your email on every sign in.
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
