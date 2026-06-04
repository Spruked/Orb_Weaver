import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Globe, Trash2, ExternalLink, BarChart3, FolderPlus, FileText, RotateCw } from 'lucide-react';
import { api, Project } from '../services/api';

const Projects: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newProject, setNewProject] = useState({ client_name: '', domain: '', ga4_property_id: '' });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const loadProjects = async () => {
    setIsLoading(true);
    setError('');
    try {
      setProjects(await api.listProjects());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleAddProject = async () => {
    if (!newProject.client_name.trim() || !newProject.domain.trim()) return;

    setError('');
    try {
      await api.createProject({
        name: newProject.client_name.trim(),
        domain: newProject.domain.trim().replace(/^https?:\/\//, '').replace(/\/$/, ''),
        ga4_property_id: newProject.ga4_property_id.trim() || null
      });
      setShowAddModal(false);
      setNewProject({ client_name: '', domain: '', ga4_property_id: '' });
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add project');
    }
  };

  const handleDelete = async (id: string) => {
    setError('');
    try {
      await api.deleteProject(id);
      await loadProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
    }
  };

  const handleCrawl = async (projectId: string) => {
    setError('');
    try {
      const crawl = await api.startCrawl(projectId, {
        max_pages: 100,
        delay: 1,
        max_depth: 5
      });
      navigate(`/crawl/${crawl.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start crawl');
    }
  };

  const handleRecrawl = async (projectId: string) => {
    setError('');
    try {
      const crawl = await api.recrawlProject(projectId, {
        max_pages: 100,
        delay: 1,
        max_depth: 5
      });
      navigate(`/crawl/${crawl.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restart crawl');
    }
  };

  const handleReaudit = async (projectId: string) => {
    setError('');
    try {
      const audit = await api.reauditProject(projectId);
      navigate(`/audit/${audit.audit_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rerun audit');
    }
  };

  const renderStatusBadge = (status?: string) => {
    if (!status || status === 'never_crawled') {
      return <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-600">Never Crawled</span>;
    }
    if (status === 'completed') {
      return <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-700">Audit Ready</span>;
    }
    if (status === 'running' || status === 'pending') {
      return <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700">Crawl Running</span>;
    }
    return <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-700">Crawl Failed</span>;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Client Folders</h1>
          <p className="text-gray-500 mt-1">Create folders by client name and manage crawls</p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn-primary flex items-center gap-2">
          <FolderPlus className="w-5 h-5" />
          Create New Folder
        </button>
      </div>

      {error && <div className="card text-red-600">{error}</div>}

      {isLoading ? (
        <div className="card text-gray-500">Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="card text-gray-500">No projects have been created yet.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div key={project.id} className="card hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-brand-orange/10 rounded-xl flex items-center justify-center">
                    <Globe className="w-6 h-6 text-brand-orange" />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900">{project.name}</h3>
                    <p className="text-sm text-gray-500">{project.domain}</p>
                    <div className="mt-1">{renderStatusBadge(project.latest_crawl_status)}</div>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(project.id)}
                  className="p-2 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-600 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <p className={`text-2xl font-bold ${project.latest_audit_score == null ? 'text-gray-400' : 'text-gray-900'}`}>
                    {project.latest_audit_score == null ? '-' : Math.round(project.latest_audit_score)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Score</p>
                </div>
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <p className={`text-2xl font-bold ${project.latest_pages_crawled == null ? 'text-gray-400' : 'text-gray-900'}`}>
                    {project.latest_pages_crawled ?? '-'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Pages</p>
                </div>
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm font-bold text-gray-900">
                    {project.created_at ? new Date(project.created_at).toLocaleDateString() : '-'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Created</p>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() =>
                    project.latest_crawl_id ? handleRecrawl(project.id) : handleCrawl(project.id)
                  }
                  className="flex-1 py-2 bg-brand-orange/10 text-brand-orange rounded-lg font-medium hover:bg-brand-orange/20 transition-colors flex items-center justify-center gap-2"
                >
                  {project.latest_crawl_id ? <RotateCw className="w-4 h-4" /> : <ExternalLink className="w-4 h-4" />}
                  {project.latest_crawl_id ? 'Re-Crawl' : 'Crawl'}
                </button>
                {project.latest_crawl_status === 'completed' && (
                  <button
                    onClick={() => handleReaudit(project.id)}
                    className="flex-1 py-2 bg-purple-50 text-purple-700 rounded-lg font-medium hover:bg-purple-100 transition-colors"
                  >
                    Re-Audit
                  </button>
                )}
                {project.ga4_property_id && (
                  <button
                    onClick={() => navigate(`/ga4/${project.ga4_property_id}`)}
                    className="flex-1 py-2 bg-blue-50 text-blue-600 rounded-lg font-medium hover:bg-blue-100 transition-colors flex items-center justify-center gap-2"
                  >
                    <BarChart3 className="w-4 h-4" />
                    GA4
                  </button>
                )}
                <button
                  onClick={() => navigate(`/reports/${project.id}`)}
                  className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors flex items-center justify-center gap-2"
                >
                  <FileText className="w-4 h-4" />
                  Reports
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Create New Folder</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Client Name</label>
                <input
                  type="text"
                  value={newProject.client_name}
                  onChange={(e) => setNewProject({ ...newProject, client_name: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
                  placeholder="Client name (used as folder title)"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Domain</label>
                <input
                  type="text"
                  value={newProject.domain}
                  onChange={(e) => setNewProject({ ...newProject, domain: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
                  placeholder="domain.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">GA4 Property ID</label>
                <input
                  type="text"
                  value={newProject.ga4_property_id}
                  onChange={(e) => setNewProject({ ...newProject, ga4_property_id: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
                  placeholder="Optional"
                />
              </div>
            </div>

            <div className="flex gap-4 mt-8">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 py-3 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddProject}
                className="flex-1 py-3 bg-brand-orange text-white rounded-lg font-medium hover:bg-orange-600 transition-colors"
              >
                Create Folder
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Projects;
