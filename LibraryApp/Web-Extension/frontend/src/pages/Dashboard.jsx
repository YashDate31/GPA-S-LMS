import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Book, AlertCircle, Clock, CheckCircle2, Megaphone, TrendingUp, RefreshCw, IndianRupee } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Skeleton from '../components/ui/Skeleton';
import ErrorMessage from '../components/ui/ErrorMessage';
import EmptyState from '../components/ui/EmptyState';
import BookLoanCard from '../components/BookLoanCard';

export default function Dashboard({ user }) {
  const navigate = useNavigate();
  const [data, setData] = useState({ 
    borrows: [], 
    history: [], 
    notices: [], 
    notifications: [],
    recent_requests: [],
    analytics: { badges: [], stats: {} }
  });
  const [loading, setLoading] = useState(true);
  const [profilePhoto, setProfilePhoto] = useState(null);
  const [renewingBookId, setRenewingBookId] = useState(null);

  // Load profile photo from localStorage (user-specific)
  useEffect(() => {
    if (user?.enrollment_no) {
      const savedPhoto = localStorage.getItem(`profilePhoto_${user.enrollment_no}`);
      if (savedPhoto) {
        setProfilePhoto(savedPhoto);
      }
    }
  }, [user]);

  // Use actual user data from session
  // Normalize year for display
  let displayYear = "N/A";
  if (user?.year) {
    const y = String(user.year).trim().toLowerCase();
    if (["pass out", "passout", "passed out", "alumni", "graduate"].includes(y)) {
      displayYear = "Pass Out";
    } else {
      displayYear = user.year;
    }
  }
  const displayUser = {
    name: user?.name || "Student",
    year: displayYear,
    department: user?.department || "Computer Department",
    avatar: profilePhoto || `https://ui-avatars.com/api/?name=${encodeURIComponent((user?.name || 'Student').split(' ').map(n=>n[0]).join('').substring(0,2))}&background=3b82f6&color=fff&size=128&bold=true`
  };

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const { data } = await axios.get('/api/dashboard');
      setData(data);
    } catch (e) {
      console.error("Failed to fetch dashboard, using fallback state if needed", e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <DashboardSkeleton />;
  if (!data && !loading) return (
    <div className="p-6">
      <ErrorMessage message="Failed to load your dashboard." onRetry={fetchData} />
    </div>
  );

  const overdueBooks = (data.borrows || []).filter(b => b.status === 'overdue');
  const activeBorrows = data.borrows || [];

  const handleRenew = async (book) => {
    setRenewingBookId(book.accession_no || book.book_id);
    try {
      await axios.post('/api/request', {
        type: 'renewal',
        details: JSON.stringify({ book_id: book.book_id, accession_no: book.accession_no || book.book_id, title: book.title })
      });
      alert('Renewal request sent to librarian for approval.');
      fetchData();
    } catch (e) {
      const msg = e.response?.data?.error || e.response?.data?.message || 'Failed to submit renewal request';
      alert(msg);
    } finally {
      setRenewingBookId(null);
    }
  };

  const getLoanStatus = (book) => {
    if (book.status === 'overdue') return 'overdue';
    // Parser for "5 days left" logic
    const days = parseInt(book.days_msg?.replace(/\D/g, '') || '10', 10);
    if (days <= 3) return 'due_soon';
    return 'normal';
  };

  // Helper to safely format relative dates from "YYYY-MM-DD HH:MM:SS"
  const formatRelativeDate = (dateStr) => {
    if (!dateStr) return 'Recently';
    try {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const due = new Date(dateStr.replace(' ', 'T'));
        due.setHours(0, 0, 0, 0);
        const diffDays = Math.ceil((due - today) / (1000 * 60 * 60 * 24));
        const formatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' });
        const mappedDate = formatter.format(due);
        
        if (diffDays === 0) return `Due today — ${mappedDate}`;
        if (diffDays === 1) return `Due tmrw — ${mappedDate}`;
        if (diffDays > 1) return `Due in ${diffDays} days — ${mappedDate}`;
        if (diffDays === -1) return `Overdue by 1 day — ${mappedDate}`;
        if (diffDays < -1) return `Overdue by ${Math.abs(diffDays)} days — ${mappedDate}`;
        return mappedDate;
    } catch (e) {
        return dateStr;
    }
  };
  
  const formatDate = (dateStr) => {
    if (!dateStr) return 'Recently';
    try {
        const isoStr = dateStr.replace(' ', 'T');
        return new Date(isoStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch (e) { return dateStr; }
  };

  return (
    <div className="min-h-screen bg-slate-50/50 dark:bg-slate-950 pb-24 md:pb-10 transition-colors">
      <div className="px-4 py-6 space-y-8 max-w-5xl mx-auto">
        
        {/* Z-Pattern: 1. Header & Most Urgent Action */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
             {/* Profile Minimal Card */}
             <Card className="relative h-full bg-gradient-to-br from-blue-600 to-indigo-700 text-white border-none shadow-xl overflow-hidden flex flex-col justify-center p-6">
                <div className="absolute top-0 right-0 p-4 opacity-10">
                    <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                </div>
                <div className="flex items-center gap-5 relative z-10 w-full mb-6">
                    <div className="shrink-0 relative">
                        <img src={displayUser.avatar} alt="Profile" className="w-16 h-16 rounded-full border-2 border-white/50 object-cover shadow-lg" />
                    </div>
                    <div>
                        <p className="text-blue-100 text-xs font-medium tracking-wider uppercase mb-1">Student Portal</p>
                        <h2 className="text-2xl font-heading font-bold">{displayUser.name}</h2>
                    </div>
                </div>
                <div className="flex items-center justify-between mt-auto bg-white/10 backdrop-blur-sm p-3 rounded-lg border border-white/10 w-full">
                     <div className="flex gap-4">
                         <div>
                             <span className="text-xs text-blue-200 block">ID No.</span>
                             <span className="font-mono font-medium">{user?.enrollment_no || '---'}</span>
                         </div>
                         <div>
                             <span className="text-xs text-blue-200 block">Branch</span>
                             <span className="font-medium truncate max-w-[120px] inline-block">{displayUser.department}</span>
                         </div>
                     </div>
                     <Button variant="secondary" size="sm" className="bg-white/10 hover:bg-white/20 text-white border-transparent" onClick={() => navigate('/profile')}>
                        Profile
                     </Button>
                </div>
            </Card>
            
            {/* Active Loans */}
            <div className="h-full flex flex-col">
              <h3 className="text-lg font-heading font-bold text-slate-800 dark:text-white mb-3 px-1 flex items-center justify-between">
                <span>Active Loans</span>
                <button className="text-sm text-blue-600 hover:underline font-semibold" onClick={() => navigate('/my-books')}>View History ➜</button>
              </h3>
              {activeBorrows.length === 0 ? (
                 <Card className="flex-1 flex flex-col items-center justify-center p-6 text-center border-dashed border-2 bg-slate-50 dark:bg-slate-900/50 shadow-none">
                    <Book className="w-8 h-8 text-slate-300 dark:text-slate-600 mb-2" />
                    <p className="text-slate-600 dark:text-slate-400 font-medium text-sm">No books borrowed</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500 mb-3 mt-1">Your reading list is empty.</p>
                    <Button variant="primary" size="sm" onClick={() => navigate('/books')}>Find Books</Button>
                 </Card>
              ) : (
                 <div className="flex overflow-x-auto pb-2 -mx-2 px-2 gap-4 snap-x hide-scrollbar h-[180px]">
                    {activeBorrows.slice(0, 3).map((book, i) => (
                      <div key={i} className="snap-center shrink-0 w-[240px] h-[160px]">
                        <BookLoanCard 
                          title={book.title}
                          author={book.author || "Unknown Author"}
                          dueDate={formatRelativeDate(book.due_date)}
                          status={getLoanStatus(book)}
                          fine={book.status === 'overdue' && book.fine ? `₹${book.fine}` : undefined}
                          onRenew={() => handleRenew(book)}
                          onViewDetails={() => navigate(`/books/${book.book_id}`)}
                        />
                      </div>
                    ))}
                 </div>
              )}
            </div>
        </div>

        {/* 2. Secondary: Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <Card className="p-4 flex items-center justify-between hover:shadow-md transition-shadow">
                  <div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wide">Borrowed</p>
                      <p className="text-xl font-black text-slate-800 dark:text-white mt-0.5">{data.summary?.borrowed_count ?? activeBorrows.length}</p>
                      <p className="text-[10px] text-slate-400 mt-1">{activeBorrows.length === 0 ? 'No current loans' : `Active library loans`}</p>
                  </div>
                  <div className="w-10 h-10 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center"><Book size={18} /></div>
              </Card>
              <Card className="p-4 flex items-center justify-between hover:shadow-md transition-shadow">
                  <div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wide">Returned</p>
                      <p className="text-xl font-black text-emerald-600 dark:text-emerald-400 mt-0.5">{data.summary?.returned_count ?? data.history?.length ?? 0}</p>
                      <p className="text-[10px] text-slate-400 mt-1">Total books returned</p>
                  </div>
                  <div className="w-10 h-10 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-full flex items-center justify-center"><CheckCircle2 size={18} /></div>
              </Card>
               <Card className="p-4 flex items-center justify-between hover:shadow-md transition-shadow">
                  <div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wide">Overdue</p>
                      <p className={`text-xl font-black mt-0.5 ${overdueBooks.length > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-400 dark:text-slate-600'}`}>
                          {data.summary?.overdue_count ?? overdueBooks.length}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-1">{overdueBooks.length === 0 ? 'No overdue fines 🎉' : 'Action required immediately'}</p>
                  </div>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${overdueBooks.length > 0 ? 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500'}`}><AlertCircle size={18} /></div>
              </Card>
              <Card className="p-4 flex items-center justify-between hover:shadow-md transition-shadow">
                  <div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wide">Active Fine</p>
                      <p className={`text-xl font-black mt-0.5 ${(data.summary?.active_fine || 0) > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-400 dark:text-slate-600'}`}>
                          ₹{data.summary?.active_fine ?? 0}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-1">{(data.summary?.active_fine || 0) > 0 ? 'Fine pending clearance' : 'No outstanding fines'}</p>
                  </div>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${(data.summary?.active_fine || 0) > 0 ? 'bg-red-50 dark:bg-red-900/30 text-red-500 dark:text-red-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'}`}>
                      <IndianRupee size={18} />
                  </div>
              </Card>
        </div>

        {/* 3. Bottom Row: Broadcast Notices & Recent Requests */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Broadcast Notices */}
            {data.notices && data.notices.length > 0 && (
               <div className="space-y-4">
                 <h3 className="text-lg font-heading font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    <Megaphone className="w-5 h-5 text-amber-500" />
                    Announcements
                 </h3>
                 <div className="grid gap-3">
                   {data.notices.slice(0,2).map((notice) => (
                     <div key={notice.id} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm border-l-4 border-l-amber-400">
                         <h4 className="font-bold text-slate-800 dark:text-white text-sm mb-1">{notice.title}</h4>
                         <p className="text-slate-600 dark:text-slate-400 text-xs leading-relaxed mb-2 line-clamp-2">{notice.content}</p>
                         <div className="text-[10px] text-slate-400 font-medium">Posted on {formatDate(notice.date)}</div>
                     </div>
                   ))}
                 </div>
               </div>
            )}

            {/* Recent Requests */}
            <div className="space-y-4">
               <h3 className="text-lg font-heading font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 text-indigo-500" />
                  Recent Requests
               </h3>
               {(!data.recent_requests || data.recent_requests.length === 0) ? (
                 <Card className="p-6 text-center text-slate-500 shadow-none border-dashed bg-transparent border-slate-200">
                   No recent requests.
                 </Card>
               ) : (
                 <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden divide-y divide-slate-100 dark:divide-slate-800">
                     {data.recent_requests.slice(0, 3).map((req) => (
                       <div key={req.req_id || req.id} className="p-3.5 flex items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                         <div className="min-w-0">
                           <p className="font-semibold text-slate-800 dark:text-white text-sm capitalize truncate">{req.request_type.replace('_', ' ')}</p>
                           <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                             {(() => {
                               try {
                                 let parsed = req.details;
                                 if (typeof parsed === 'string') parsed = JSON.parse(parsed);
                                 if (typeof parsed === 'string') parsed = JSON.parse(parsed);
                                 if (typeof parsed === 'object' && parsed !== null) {
                                   if (req.request_type === 'renewal') return `Renewal for: ${parsed.title || parsed.book_id || 'Book'}`;
                                   return parsed.title || parsed.book_id || JSON.stringify(parsed);
                                 }
                                 return String(parsed);
                               } catch { return String(req.details); }
                             })()}
                           </p>
                         </div>
                         <div className="flex flex-col items-end gap-1 shrink-0">
                           <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider ${
                             req.status === 'approved' ? 'bg-emerald-100 text-emerald-700' :
                             req.status === 'rejected' ? 'bg-red-100 text-red-700' :
                             req.status === 'cancelled' ? 'bg-slate-100 text-slate-700' :
                             'bg-amber-100 text-amber-700'
                           }`}>
                             {req.status === 'pending' ? 'Reviewing' : req.status}
                           </span>
                           <span className="text-[10px] text-slate-400">{new Date(req.created_at).toLocaleDateString()}</span>
                         </div>
                       </div>
                     ))}
                 </div>
               )}
            </div>
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="p-4 space-y-6 max-w-5xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
         <Skeleton className="h-48 w-full rounded-2xl" />
         <div className="flex gap-4">
             <Skeleton className="h-48 w-1/2 rounded-2xl" />
             <Skeleton className="h-48 w-1/2 rounded-2xl" />
         </div>
      </div>
      <div className="grid grid-cols-3 gap-4">
         <Skeleton className="h-20 w-full rounded-xl" />
         <Skeleton className="h-20 w-full rounded-xl" />
         <Skeleton className="h-20 w-full rounded-xl" />
      </div>
    </div>
  );
}
