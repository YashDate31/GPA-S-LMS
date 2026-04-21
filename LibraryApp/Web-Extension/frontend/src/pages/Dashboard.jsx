import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Book, AlertCircle, Clock, CheckCircle2, Megaphone, TrendingUp, RefreshCw, IndianRupee, Bookmark, History, PieChart } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Skeleton from '../components/ui/Skeleton';
import ErrorMessage from '../components/ui/ErrorMessage';
import EmptyState from '../components/ui/EmptyState';
import BookLoanCard from '../components/BookLoanCard';
import AlertBanner from '../components/AlertBanner';
import { useToast } from '../context/ToastContext';

export default function Dashboard({ user }) {
  const toast = useToast();
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

  // BUG 4 FIX: Don't unconditionally pre-set the backend URL (causes 404 flash
  // for users with no photo). Use a HEAD request to check photo existence first.
  useEffect(() => {
    if (user?.enrollment_no) {
      axios.head('/api/profile/photo')
        .then(() => setProfilePhoto(`/api/profile/photo?_t=${new Date().getTime()}`))
        .catch(() => setProfilePhoto(null)); // avatars fallback will handle it
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
      toast.success('Renewal request sent to librarian for approval.');
      fetchData();
    } catch (e) {
      const msg = e.response?.data?.error || e.response?.data?.message || 'Failed to submit renewal request';
      toast.error(msg);
    } finally {
      setRenewingBookId(null);
    }
  };

  const getLoanStatus = (book) => {
    // BUG 8 FIX: Check 'status' field directly first — overdue books have status='overdue'
    // The old logic parsed days_msg with /\D/g which strips ALL non-digits, so
    // "101 days late" -> "101" which is NOT <=3, so overdue showed as green "On Time".
    if (book.status === 'overdue') return 'overdue';
    // Only use days_msg to detect "due soon" for active (non-overdue) loans
    const match = book.days_msg?.match(/^(\d+)\s*days?\s*left/i);
    const days = match ? parseInt(match[1], 10) : 99;
    return days <= 3 ? 'due_soon' : 'normal';
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
        <AlertBanner />
        
        {/* Z-Pattern: 1. Header & Most Urgent Action */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
             {/* Profile Minimal Card */}
             <Card className="relative h-full bg-gradient-to-br from-primary to-indigo-900 text-white border-none shadow-xl overflow-hidden flex flex-col justify-center p-6">
                <div className="absolute top-0 right-0 p-4 opacity-10">
                    <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                </div>
                <div className="flex items-center gap-5 relative z-10 w-full mb-6">
                    <div className="shrink-0 relative">
                        <img 
                          src={displayUser.avatar} 
                          alt="Profile" 
                          className="w-16 h-16 rounded-full border-2 border-white/50 object-cover shadow-lg" 
                          onError={(e) => {
                              e.target.onerror = null;
                              e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent((user?.name || 'Student').split(' ').map(n=>n[0]).join('').substring(0,2))}&background=0F3460&color=fff&size=128&bold=true`;
                          }}
                        />
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
                <button className="text-sm text-primary hover:underline font-semibold" onClick={() => navigate('/my-books')}>View History ➜</button>
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
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <Card className="p-4 flex items-center justify-between hover:shadow-md transition-shadow">
                  <div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wide">Borrowed</p>
                      <p className="text-xl font-black text-slate-800 dark:text-white mt-0.5">{data.summary?.borrowed_count ?? activeBorrows.length}</p>
                      <p className="text-[10px] text-slate-400 mt-1">{activeBorrows.length === 0 ? 'No current loans' : `Active library loans`}</p>
                  </div>
                  <div className="w-10 h-10 bg-primary/10 dark:bg-primary/20 text-primary dark:text-blue-400 rounded-full flex items-center justify-center"><Book size={18} /></div>
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
              <Card className="p-4 flex items-center justify-between hover:shadow-md transition-shadow">
                  <div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wide">Wishlist</p>
                      <p className={`text-xl font-black mt-0.5 ${(data.summary?.wishlist_count || 0) > 0 ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-400 dark:text-slate-600'}`}>
                          {data.summary?.wishlist_count ?? 0}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-1">{(data.summary?.wishlist_count || 0) > 0 ? 'Books waiting' : 'Wishlist is empty'}</p>
                  </div>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${(data.summary?.wishlist_count || 0) > 0 ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-500 dark:text-indigo-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'}`}>
                      <Bookmark size={18} />
                  </div>
              </Card>
              <Card className="p-4 flex items-center justify-between hover:shadow-md transition-shadow">
                  <div>
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wide">Total Fines</p>
                      <p className={`text-xl font-black mt-0.5 ${(data.summary?.total_fine_ever || 0) > 0 ? 'text-slate-800 dark:text-white' : 'text-slate-400 dark:text-slate-600'}`}>
                          ₹{data.summary?.total_fine_ever ?? 0}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-1">Cumulative history</p>
                  </div>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center text-slate-500 bg-slate-100 dark:bg-slate-800 dark:text-slate-400`}>
                      <History size={18} />
                  </div>
              </Card>
        </div>

        {/* 3. Bottom Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Reading Habits */}
            <div className="space-y-4">
               <h3 className="text-lg font-heading font-bold text-slate-800 dark:text-white flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-purple-500" />
                  Reading Habits
               </h3>
               <Card className="p-5 flex flex-col justify-center h-[calc(100%-2rem)]">
                 {!data.analytics?.stats?.categories || Object.keys(data.analytics.stats.categories).length === 0 ? (
                    <div className="text-center text-slate-400 dark:text-slate-500 my-auto py-6">
                      <TrendingUp className="w-8 h-8 opacity-50 mx-auto mb-2" />
                      <p className="text-sm font-medium">No reading data yet.</p>
                    </div>
                 ) : (
                    <div className="space-y-4 w-full">
                      {Object.entries(data.analytics.stats.categories)
                        .sort(([,a], [,b]) => b - a)
                        .slice(0, 4)
                        .map(([category, count]) => {
                          const total = data.analytics.stats.total_books || Object.values(data.analytics.stats.categories).reduce((a,b)=>a+b, 0) || 1;
                          const pct = Math.round((count / total) * 100);
                          return (
                            <div key={category}>
                              <div className="flex justify-between text-xs mb-1 font-bold">
                                <span className="text-slate-700 dark:text-slate-300 truncate pr-2">{category}</span>
                                <span className="text-slate-500 dark:text-slate-400 shrink-0">{pct}% ({count})</span>
                              </div>
                              <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-purple-500 dark:bg-purple-400 rounded-full" 
                                  style={{ width: `${pct}%` }} 
                                />
                              </div>
                            </div>
                          );
                      })}
                    </div>
                 )}
               </Card>
            </div>

            {/* Broadcast Notices */}
            {data.notices && data.notices.length > 0 && (
               <div className="space-y-4 lg:col-span-1">
                 <h3 className="text-lg font-heading font-bold text-slate-800 dark:text-white flex items-center gap-2">
                    <Megaphone className="w-5 h-5 text-amber-500" />
                    Announcements
                 </h3>
                 <div className="grid gap-3">
                   {data.notices.slice(0,2).map((notice) => (
                     <div key={notice.id} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm border-l-4 border-l-amber-400 h-full flex flex-col">
                         <h4 className="font-bold text-slate-800 dark:text-white text-sm mb-1">{notice.title}</h4>
                         <p className="text-slate-600 dark:text-slate-400 text-xs leading-relaxed mb-2 line-clamp-2 flex-grow">{notice.content}</p>
                         <div className="text-[10px] text-slate-400 font-medium">Posted on {formatDate(notice.date)}</div>
                     </div>
                   ))}
                 </div>
               </div>
            )}

            {/* Recent Requests */}
            <div className="space-y-4 lg:col-span-1">
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
                             req.status === 'cancelled' ? 'bg-slate-100 text-slate-500' :
                             'bg-amber-100 text-amber-700'
                           }`}>
                             {req.status === 'pending' ? 'Pending' : req.status}
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
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-8 animate-pulse">
      {/* 1. Top Section: Welcome & Actions */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="space-y-2">
          <Skeleton className="h-4 w-32 rounded-lg" />
          <Skeleton className="h-8 w-64 rounded-xl" />
          <Skeleton className="h-4 w-48 rounded-lg" />
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-10 w-32 rounded-xl" />
          <Skeleton className="h-10 w-32 rounded-xl" />
        </div>
      </div>

      {/* 2. Top Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex items-center gap-3">
              <Skeleton className="w-10 h-10 rounded-full" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-5 w-12" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content Area (Currently Borrowed) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <Skeleton className="h-6 w-40 rounded-lg" />
            <Skeleton className="h-8 w-24 rounded-lg" />
          </div>
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden divide-y divide-slate-100 dark:divide-slate-800 shadow-sm">
            {[1, 2, 3].map((i) => (
              <div key={i} className="p-4 flex gap-4">
                <Skeleton className="w-16 h-24 rounded-lg flex-shrink-0" />
                <div className="flex flex-col justify-between py-1 flex-1">
                  <div className="space-y-2">
                    <Skeleton className="h-5 w-3/4 rounded" />
                    <Skeleton className="h-4 w-1/2 rounded" />
                  </div>
                  <div className="flex gap-2">
                    <Skeleton className="h-6 w-20 rounded-full" />
                    <Skeleton className="h-6 w-24 rounded-full" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Sidebar (Fines & History) */}
        <div className="space-y-8">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-6">
            <div className="flex justify-between items-center">
              <Skeleton className="h-6 w-32 rounded-lg" />
              <Skeleton className="w-10 h-10 rounded-full" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-10 w-24 rounded-xl" />
              <Skeleton className="h-4 w-40 rounded-lg" />
            </div>
            <Skeleton className="h-10 w-full rounded-xl" />
          </div>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm space-y-4">
            <Skeleton className="h-6 w-32 rounded-lg mb-2" />
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex justify-between items-center">
                <Skeleton className="h-4 w-3/4 rounded" />
                <Skeleton className="h-4 w-12 rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="space-y-4">
          <Skeleton className="h-6 w-40 rounded-lg" />
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl space-y-4">
             {[1,2,3].map(i => (
                <div key={i} className="space-y-2">
                   <div className="flex justify-between"><Skeleton className="h-3 w-20"/><Skeleton className="h-3 w-10"/></div>
                   <Skeleton className="h-2 w-full rounded-full" />
                </div>
             ))}
          </div>
        </div>
        <div className="space-y-4 lg:col-span-1">
          <Skeleton className="h-6 w-40 rounded-lg" />
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-xl shadow-sm border-l-4 border-l-slate-200 dark:border-l-slate-800 space-y-2 h-[100px]">
                <Skeleton className="h-4 w-1/2 rounded" />
                <Skeleton className="h-3 w-full rounded" />
                <Skeleton className="h-3 w-2/3 rounded" />
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-4 lg:col-span-1">
          <Skeleton className="h-6 w-40 rounded-lg" />
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden divide-y divide-slate-100 dark:divide-slate-800">
            {[1, 2, 3].map((i) => (
              <div key={i} className="p-3.5 flex items-center justify-between gap-3 h-[60px]">
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-4 w-24 rounded" />
                  <Skeleton className="h-3 w-32 rounded" />
                </div>
                <div className="space-y-2 flex flex-col items-end">
                  <Skeleton className="h-4 w-16 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
