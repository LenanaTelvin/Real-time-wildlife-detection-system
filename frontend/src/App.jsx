// src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import Login from './pages/Login';
import Register from './pages/Register';

function App() {
  // Simple auth check
  const isAuthenticated = () => {
    return !!localStorage.getItem('token');
  };

  console.log('App rendering, auth status:', isAuthenticated());

  return (
    <Router>
      <Routes>
        {/* Public routes - no login required */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        {/* Protected routes - require login */}
        <Route 
          path="/dashboard" 
          element={isAuthenticated() ? <Dashboard /> : <Navigate to="/login" />}
        />
        <Route 
          path="/history" 
          element={isAuthenticated() ? <History /> : <Navigate to="/login" />}
        />
        
        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/dashboard" />} />
      </Routes>
    </Router>
  );
}

export default App;