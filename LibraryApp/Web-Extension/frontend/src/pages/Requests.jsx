import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader2, AlertCircle, XCircle } from 'lucide-react';
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
        <div className="bg-white dark:bg-dark-card rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-800">
                  <th className="p-4 font-semibold text-gray-600 dark:text-gray-300">Type</th>
                  <th className="p-4 font-semibold text-gray-600 dark:text-gray-300">Details</th>
                  <th className="p-4 font-semibold text-gray-600 dark:text-gray-300">Date</th>
                  <th className="p-4 font-semibold text-gray-600 dark:text-gray-300">Status</th>
                  <th className="p-4 font-semibold text-gray-600 dark:text-gray-300 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {requests.map((req) => (
                  <tr key={req.req_id || req.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/20 transition-colors">
                    <td className="p-4 font-medium text-gray-900 dark:text-white capitalize">
                      {req.request_type.replace('_', ' ')}
                    </td>
                    <td className="p-4 text-gray-600 dark:text-gray-400 max-w-xs truncate" title={formatDetails(req.details, req.request_type)}>
                      {formatDetails(req.details, req.request_type)}
                    </td>
                    <td className="p-4 text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      {new Date(req.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4">
                      {getStatusBadge(req.status)}
                    </td>
                    <td className="p-4 text-right">
                      {req.status === 'pending' && (
                        <button
                          onClick={() => cancelRequest(req.req_id || req.id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                          title="Cancel Request"
                        >
                          <XCircle size={16} />
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Requests;
