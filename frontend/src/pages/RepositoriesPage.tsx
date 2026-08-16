import React, { useState, useEffect } from 'react';
import { Search } from 'lucide-react';
import Navbar from '@/components/layout/Navbar';
import RepositoryList from '@/components/repository/RepositoryList';
import { fetchRepositories, RepositorySummary } from '@/lib/api';

export default function RepositoriesPage() {
  const [repositories, setRepositories] = useState<RepositorySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRepositories() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchRepositories(1, 50, search);
        setRepositories(data.items || []);
      } catch (err: any) {
        console.error('Failed to fetch repositories:', err);
        setError(err.message || 'Failed to load repositories.');
      } finally {
        setLoading(false);
      }
    }
    loadRepositories();
  }, [search]);

  return (
    <>
      <Navbar title="Repositories" />

      <div className="px-6 py-6 pb-12 space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Tracked Repositories</h1>
            <p className="text-xs text-zinc-400 mt-1">
              Monitor code health scores, review volume, and vulnerability metrics across repositories.
            </p>
          </div>

          {/* Search */}
          <div className="relative w-full md:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              placeholder="Search repositories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-zinc-900/80 border border-zinc-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-blue-500/50"
            />
          </div>
        </div>

        {/* Loading / Error / Content */}
        {loading ? (
          <div className="p-12 text-center text-xs text-zinc-500 font-mono">
            Loading repositories from MongoDB backend...
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-mono">
            Notice: Connection error ({error}). Make sure backend API server is active.
          </div>
        ) : (
          <RepositoryList repositories={repositories} />
        )}
      </div>
    </>
  );
}
