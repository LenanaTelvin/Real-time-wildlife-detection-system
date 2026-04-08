// src/pages/Register.jsx
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { authService } from '../services/authService';
import VerifyOTP from '../components/VerifyOTP';

const Register = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showOTP, setShowOTP] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await authService.register(email, password, name);
      console.log('Registration response:', response);
      
      if (response.requires_verification) {
        setRegisteredEmail(email);
        setShowOTP(true);
      } else {
        // Direct login if no verification needed
        window.location.href = '/dashboard';
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleVerificationSuccess = () => {
    // Redirect handled in VerifyOTP component
  };

  if (showOTP) {
    return (
      <VerifyOTP 
        email={registeredEmail}
        onSuccess={handleVerificationSuccess}
        onBack={() => setShowOTP(false)}
      />
    );
  }

  return (
    <div className="register-container">
      <div className="register-card">
        <h1 className="register-title">Create Account</h1>
        
        {error && (
          <div className="register-error">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="form-input"
              placeholder="Wildlife Researcher"
              required
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="form-input"
              placeholder="researcher@wildlife.org"
              required
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="form-input"
              placeholder="••••••••"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="register-button"
          >
            {loading ? 'Creating account...' : 'Register'}
          </button>
        </form>
        
        <p className="login-link">
          Already have an account?{' '}
          <Link to="/login">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Register;