import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader2, AlertCircle, XCircle, Book, RefreshCw, User, Info, RotateCcw } from 'lucide-react';
import { useToast } from '../context/ToastContext';

const Requests = ({ user }) => {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { addToast } = useToast();

  useEffect(() => {
    fetchRequests();
  }, []);

  const fetchRequests = async () => {
    try {
      const { data } = await axios.get('/api/requests');
      setRequests(data.requests);
      setError(null);
    } catch (err) {
      setError('Failed to load requests');
    } finally {
      setLoading(false);
    }
  };

  const cancelRequest = async (reqId) => {
    if (!window.confirm('Are you sure you want to cancel this request?')) return;
    try {
      await axios.post(`/api/request/${reqId}/cancel`);
      addToast('Request cancelled successfully', 'success');
      fetchRequests();
    } catch (err) {
      addToast(err.response?.data?.error || 'Failed to cancel request', 'error');
    }
  };

  const reRequest = async (req) => {
    try {
      let parsed = req.details;
      if (typeof parsed === 'string') parsed = JSON.parse(parsed);
      if (typeof parsed === 'string') parsed = JSON.parse(parsed);
      
      const payload = {
        type: req.request_type,
        details: JSON.stringify(parsed)
      };
      await axios.post('/api/request', payload);
      addToast('Request resubmitted successfully', 'success');
      fetchRequests();
    } catch (err) {
      addToast(err.response?.data?.error || 'Failed to re-request', 'error');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-amber-100 text-amber-800 border border-amber-200',
      approved: 'bg-emerald-100 text-emerald-800 border border-emerald-200',
      rejected: 'bg-red-100 text-red-800 border border-red-200',
      cancelled: 'bg-gray-100 text-gray-800 border border-gray-200'
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium uppercase tracking-wider ${styles[status] || styles.pending}`}>
        {status}
      </span>
    );
  };

  const formatDetails = (details, type) => {
    try {
      let parsed = details;
      if (typeof details === 'string') {
        parsed = JSON.parse(details);
      }
      if (typeof parsed === 'string') {
          parsed = JSON.parse(parsed);
      }

      if (type === 'renewal') {
        return `Renewal for: ${parsed.title || parsed.book_id || 'Book'}`;
      } else if (type === 'book_request') {
        return `Reservation for: ${parsed.title || parsed.book_id || 'Book'}`;
      } else if (type === 'profile_update') {
        return `Profile Update: ${Object.keys(parsed).join(', ')}`;
      }
      return typeof parsed === 'object' ? JSON.stringify(parsed) : parsed;
    } catch (e) {
      return String(details);
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-primary" size={32} />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8 animate-fade-in relative z-10 w-full overflow-hidden">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">
          My Requests
        </h1>
      </div>

      {error ? (
        <div className="bg-red-50 text-red-600 p-4 rounded-xl flex items-center gap-3 border border-red-100">
          <AlertCircle />
          <span>{error}</span>
        </div>
      ) : requests.length === 0 ? (
        <div className="bg-white dark:bg-dark-card rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 p-12 text-center">
          <p className="text-gray-500 dark:text-gray-400">You have no requests history.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map((req) => {
            const Icon = req.request_type === 'renewal' ? RefreshCw : req.request_type === 'profile_update' ? User : req.request_type === 'book_request' ? Book : Info;
            
            return (
              <div key={req.req_id || req.id} className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col sm:flex-row gap-5">
                {/* Icon */}
                <div className="flex-shrink-0">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center ${req.status === 'rejected' ? 'bg-red-50 text-red-500' : req.status === 'approved' ? 'bg-emerald-50 text-emerald-500' : 'bg-amber-50 text-amber-500'}`}>
                    <Icon size={24} />
                  </div>
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-2">
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                      {formatDetails(req.details, req.request_type)}
                    </h3>
                    <div className="flex items-center gap-3 shrink-0">
                      {getStatusBadge(req.status)}
                      <span className="text-xs text-slate-500 font-medium whitespace-nowrap">
                        {new Date(req.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  
                  {req.status === 'rejected' && (req.remark || req.admin_remark) && (
                    <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-100 dark:border-red-900/30">
                      <p className="text-sm text-red-800 dark:text-red-300 font-medium">
                        <span className="font-bold">Reason: </span> {req.remark || req.admin_remark}
                      </p>
                    </div>
                  )}
                </div>
                
                {/* Actions */}
                <div className="flex flex-row sm:flex-col justify-end gap-2 border-t sm:border-t-0 sm:border-l border-slate-100 dark:border-slate-800 pt-4 sm:pt-0 sm:pl-4 mt-2 sm:mt-0 sm:min-w-[120px]">
                  {req.status === 'pending' && (
                    <button
                      onClick={() => cancelRequest(req.req_id || req.id)}
                      className="w-full inline-flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm font-bold text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 rounded-xl transition-colors"
                    >
                      <XCircle size={16} /> Cancel
                    </button>
                  )}
                  {req.status === 'rejected' && req.request_type !== 'profile_update' && (
                    <button
                      onClick={() => reRequest(req)}
                      className="w-full inline-flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm font-bold text-blue-600 hover:text-white border border-blue-200 hover:bg-blue-600 rounded-xl transition-colors"
                    >
                      <RotateCcw size={16} /> Re-request
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Requests;
