// src/components/VerifyOTP.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const VerifyOTP = ({ email, onSuccess, onBack }) => {
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const navigate = useNavigate();

  const handleVerify = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await api.post('/auth/verify-otp', { email, otp_code: otp });
      if (response.data.success) {
        // Store token and user data
        localStorage.setItem('token', response.data.token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        onSuccess();
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    setError('');
    try {
      await api.post('/auth/resend-otp', { email });
      alert('OTP resent successfully!');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to resend OTP');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="verify-container">
      <div className="verify-card">
        <h2 className="verify-title">Verify Your Email</h2>
        <p className="verify-text">
          We've sent a 6-digit verification code to:<br />
          <strong>{email}</strong>
        </p>
        
        {error && <div className="verify-error">{error}</div>}
        
        <form onSubmit={handleVerify}>
          <div className="form-group">
            <label className="form-label">Enter OTP Code</label>
            <input
              type="text"
              maxLength="6"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              className="form-input otp-input"
              placeholder="000000"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={loading || otp.length !== 6}
            className="verify-button"
          >
            {loading ? 'Verifying...' : 'Verify Email'}
          </button>
        </form>
        
        <div className="verify-footer">
          <button
            onClick={handleResend}
            disabled={resending}
            className="resend-link"
          >
            {resending ? 'Sending...' : 'Resend OTP'}
          </button>
          <button onClick={onBack} className="back-link">
            Back to Login
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerifyOTP;