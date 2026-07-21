import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area
} from 'recharts';
import { Users, Eye, MousePointer, TrendingUp, Calendar, Globe, RefreshCw, Radio, UserPlus, Clock } from 'lucide-react';
import { api, GA4FullReport, Project } from '../services/api';

const COLORS = ['#18CFE3', '#073B5C', '#0E7490', '#8EEAF3', '#061A33'];
const ORB_STREAM_ID = '15285875409';
const ORB_MEASUREMENT_ID = 'G-5BR1CYDQGS';

const GA4Dashboard: React.FC = () => {
  const { propertyId: routePropertyId } = useParams();
  const [dateRange, setDateRange] = useState('30');
  const [ga4Data, setGa4Data] = useState<GA4FullReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [orbProject, setOrbProject] = useState<Project | null>(null);
  const [propertyInput, setPropertyInput] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const propertyId = routePropertyId || orbProject?.ga4_property_id || '';

  useEffect(() => {
    if (routePropertyId) return;

    api.listProjects()
      .then((projects) => {
        const project = projects.find((item) => item.domain.replace(/^https?:\/\//, '').replace(/\/$/, '') === 'orbweaver.spruked.com') || projects[0] || null;
        setOrbProject(project);
        setPropertyInput(project?.ga4_property_id || '');
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load GA4 configuration'))
      .finally(() => setIsLoading(false));
  }, [routePropertyId]);

  useEffect(() => {
    const timer = window.setInterval(() => setRefreshKey((key) => key + 1), 5 * 60 * 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!propertyId) {
      setGa4Data(null);
      return;
    }

    const load = async () => {
      setIsLoading(true);
      setError('');
      try {
        setGa4Data(await api.getGA4Overview(propertyId, dateRange));
        setLastUpdated(new Date());
      } catch (err) {
        setGa4Data(null);
        setError(err instanceof Error ? err.message : 'Failed to load GA4 data');
      } finally {
        setIsLoading(false);
      }
    };

    load();
  }, [propertyId, dateRange, refreshKey]);

  const saveConnection = async () => {
    if (!orbProject) {
      setError('Create the Orb Weaver project before connecting GA4.');
      return;
    }
    if (!/^\d+$/.test(propertyInput.trim())) {
      setError('Enter the numeric GA4 Property ID from Admin → Property details. The Stream ID is not the Property ID.');
      return;
    }

    setIsSaving(true);
    setError('');
    try {
      const updated = await api.updateProjectGA4Config(orbProject.id, {
        ga4_property_id: propertyInput.trim(),
        ga4_measurement_id: ORB_MEASUREMENT_ID,
      });
      setOrbProject(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save GA4 configuration');
    } finally {
      setIsSaving(false);
    }
  };

  const totals = ga4Data?.traffic_overview?.totals || {};
  const trafficRows = ga4Data?.traffic_overview?.data || [];
  const rowSummary = trafficRows.reduce<{
    sessions: number;
    newUsers: number;
    bounceWeight: number;
    durationWeight: number;
  }>(
    (summary, row) => {
      const rowSessions = Number(row.sessions || 0);
      summary.sessions += rowSessions;
      summary.newUsers += Number(row.new_users || row.newUsers || 0);
      summary.bounceWeight += Number(row.bounce_rate || row.bounceRate || 0) * rowSessions;
      summary.durationWeight += Number(row.avg_session_duration || row.averageSessionDuration || 0) * rowSessions;
      return summary;
    },
    { sessions: 0, newUsers: 0, bounceWeight: 0, durationWeight: 0 }
  );
  const sessions = Number(totals.sessions || 0);
  const users = Number(totals.users || 0);
  const pageviews = Number(totals.pageviews || totals.screenPageViews || 0);
  const newUsers = Number(totals.new_users || totals.newUsers || rowSummary.newUsers || 0);
  const engagementRate = Number(
    totals.engagementRate || totals.engagement_rate ||
    (rowSummary.sessions ? 1 - (rowSummary.bounceWeight / rowSummary.sessions) : 0)
  );
  const avgSessionDuration = Number(
    totals.averageSessionDuration || totals.avg_session_duration ||
    (rowSummary.sessions ? rowSummary.durationWeight / rowSummary.sessions : 0)
  );
  const deviceData = useMemo(
    () =>
      (ga4Data?.device_breakdown || []).map((device, index) => {
        const deviceSessions = Number(device.sessions || 0);
        return {
          name: String(device.device || device.deviceCategory || device.name || 'Unknown'),
          value: sessions > 0 ? Number(((deviceSessions / sessions) * 100).toFixed(2)) : 0,
          sessions: deviceSessions,
          color: COLORS[index % COLORS.length]
        };
      }),
    [ga4Data, sessions]
  );
  const trafficData = useMemo(() => {
    const byDate = new Map<string, { date: string; sessions: number; users: number; pageviews: number }>();
    (ga4Data?.traffic_overview?.data || []).forEach((row) => {
      const rawDate = String(row.date || '');
      const label = /^\d{8}$/.test(rawDate)
        ? `${rawDate.slice(4, 6)}/${rawDate.slice(6, 8)}`
        : rawDate;
      const current = byDate.get(rawDate) || { date: label, sessions: 0, users: 0, pageviews: 0 };
      current.sessions += Number(row.sessions || 0);
      current.users += Number(row.users || 0);
      current.pageviews += Number(row.pageviews || row.screenPageViews || 0);
      byDate.set(rawDate, current);
    });
    return Array.from(byDate.entries()).sort(([a], [b]) => a.localeCompare(b)).map(([, value]) => value);
  }, [ga4Data]);
  const channelData = useMemo(() => {
    const byChannel = new Map<string, { channel: string; sessions: number; users: number; pageviews: number }>();
    (ga4Data?.traffic_overview?.data || []).forEach((row) => {
      const channel = String(row.channel || 'Unassigned');
      const current = byChannel.get(channel) || { channel, sessions: 0, users: 0, pageviews: 0 };
      current.sessions += Number(row.sessions || 0);
      current.users += Number(row.users || 0);
      current.pageviews += Number(row.pageviews || row.screenPageViews || 0);
      byChannel.set(channel, current);
    });
    return Array.from(byChannel.values()).sort((a, b) => b.sessions - a.sessions);
  }, [ga4Data]);
  const topPages = ga4Data?.top_pages || [];
  const searchQueries = ga4Data?.search_queries || [];
  const countryData = ga4Data?.country_breakdown || [];
  const conversionEvents = ga4Data?.conversion_events || [];

  const getBounceRateColor = (rate: number) => {
    if (rate < 0.35) return 'text-green-600';
    if (rate < 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Google Analytics 4</h1>
          <p className="text-gray-500 mt-1">Live visitor, acquisition, engagement, and content performance</p>
        </div>
        <div className="flex items-center gap-3">
          <Calendar className="w-5 h-5 text-gray-400" />
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-brand-orange"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
          <button
            type="button"
            onClick={() => setRefreshKey((key) => key + 1)}
            disabled={!propertyId || isLoading}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="card grid gap-4 border-l-4 border-brand-orange md:grid-cols-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Stream</p>
          <p className="mt-1 font-bold text-gray-900">O.R.B.S.</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Stream ID</p>
          <p className="mt-1 font-mono text-sm text-gray-900">{ORB_STREAM_ID}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Measurement ID</p>
          <p className="mt-1 font-mono text-sm text-gray-900">{ORB_MEASUREMENT_ID}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Collection</p>
          <p className="mt-1 flex items-center gap-2 font-semibold text-green-700"><Radio className="h-4 w-4" /> Tag firing</p>
          {lastUpdated && <p className="mt-1 text-xs text-gray-500">Data refreshed {lastUpdated.toLocaleTimeString()}</p>}
        </div>
      </div>

      {!propertyId && !isLoading ? (
        <div className="card max-w-2xl">
          <h2 className="text-lg font-bold text-gray-900">Connect reporting data</h2>
          <p className="mt-2 text-sm leading-6 text-gray-600">
            Visitor collection is active. To populate this reporting page, enter the numeric GA4 Property ID found under
            Admin → Property details. Google API read access must also be granted to Orb Weaver's service account.
          </p>
          {error && <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
          <label className="mt-5 block text-sm font-semibold text-gray-700" htmlFor="ga4-property-id">GA4 Property ID</label>
          <input
            id="ga4-property-id"
            value={propertyInput}
            onChange={(event) => setPropertyInput(event.target.value.replace(/\D/g, ''))}
            placeholder="Example: 123456789"
            inputMode="numeric"
            className="mt-2 w-full rounded-lg border border-gray-300 px-4 py-3 font-mono focus:border-brand-orange focus:outline-none"
          />
          <button
            type="button"
            onClick={saveConnection}
            disabled={isSaving || !propertyInput}
            className="mt-4 rounded-lg bg-brand-orange px-5 py-3 font-semibold text-brand-dark hover:bg-brand-accent hover:text-white disabled:opacity-50"
          >
            {isSaving ? 'Connecting…' : 'Connect GA4 reporting'}
          </button>
        </div>
      ) : isLoading ? (
        <div className="card text-gray-500">Loading GA4 data...</div>
      ) : error ? (
        <div className="card text-red-600">{error}</div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">Sessions</h3>
                <Users className="w-5 h-5 text-blue-500" />
              </div>
              <p className="text-3xl font-bold text-gray-900">{sessions.toLocaleString()}</p>
            </div>
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">Users</h3>
                <Users className="w-5 h-5 text-brand-orange" />
              </div>
              <p className="text-3xl font-bold text-gray-900">{users.toLocaleString()}</p>
            </div>
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">New Users</h3>
                <UserPlus className="w-5 h-5 text-cyan-600" />
              </div>
              <p className="text-3xl font-bold text-gray-900">{newUsers.toLocaleString()}</p>
            </div>
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">Pageviews</h3>
                <Eye className="w-5 h-5 text-purple-500" />
              </div>
              <p className="text-3xl font-bold text-gray-900">{pageviews.toLocaleString()}</p>
            </div>
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">Engagement Rate</h3>
                <MousePointer className="w-5 h-5 text-green-500" />
              </div>
              <p className="text-3xl font-bold text-gray-900">{engagementRate ? `${(engagementRate * 100).toFixed(1)}%` : '-'}</p>
              <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
                <TrendingUp className="w-4 h-4" />
                Current period
              </p>
            </div>
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-700">Avg. Session</h3>
                <Clock className="w-5 h-5 text-indigo-500" />
              </div>
              <p className="text-3xl font-bold text-gray-900">{avgSessionDuration ? `${Math.round(avgSessionDuration)}s` : '-'}</p>
            </div>
          </div>

          <div className="card">
            <h3 className="font-bold text-gray-900 mb-4">Traffic Overview</h3>
            {trafficData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={trafficData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="sessions" stroke="#18CFE3" fill="#18CFE3" fillOpacity={0.1} />
                  <Area type="monotone" dataKey="users" stroke="#073B5C" fill="#073B5C" fillOpacity={0.1} />
                  <Area type="monotone" dataKey="pageviews" stroke="#10B981" fill="#10B981" fillOpacity={0.1} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500">No traffic data returned for this period.</p>
            )}
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="card">
              <h3 className="mb-4 font-bold text-gray-900">Acquisition Channels</h3>
              {channelData.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="border-b text-left text-xs uppercase tracking-wide text-gray-500">
                      <tr><th className="pb-3">Channel</th><th className="pb-3 text-right">Sessions</th><th className="pb-3 text-right">Users</th><th className="pb-3 text-right">Views</th></tr>
                    </thead>
                    <tbody>
                      {channelData.map((row) => (
                        <tr key={row.channel} className="border-b border-gray-100 last:border-0">
                          <td className="py-3 font-medium text-gray-900">{row.channel}</td>
                          <td className="py-3 text-right">{row.sessions.toLocaleString()}</td>
                          <td className="py-3 text-right">{row.users.toLocaleString()}</td>
                          <td className="py-3 text-right">{row.pageviews.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : <p className="text-gray-500">No acquisition data returned.</p>}
            </div>

            <div className="card">
              <h3 className="mb-4 font-bold text-gray-900">Conversion Events</h3>
              {conversionEvents.length ? (
                <div className="space-y-3">
                  {conversionEvents.map((event, index) => (
                    <div key={`${String(event.event_name)}-${index}`} className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
                      <span className="font-medium text-gray-900">{String(event.event_name || 'Event')}</span>
                      <div className="text-right">
                        <p className="font-semibold text-gray-900">{Number(event.count || 0).toLocaleString()}</p>
                        <p className="text-xs text-gray-500">conversions</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : <p className="text-gray-500">No conversion events returned for this period.</p>}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-bold text-gray-900 mb-4">Device Breakdown</h3>
              {deviceData.length > 0 ? (
                <div className="flex items-center gap-8">
                  <ResponsiveContainer width={200} height={200}>
                    <PieChart>
                      <Pie data={deviceData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                        {deviceData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-3">
                    {deviceData.map((device) => (
                      <div key={device.name} className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: device.color }} />
                        <div>
                          <p className="font-medium text-gray-900">{device.name}</p>
                          <p className="text-sm text-gray-500">
                            {device.value}% · {device.sessions.toLocaleString()} sessions
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">No device data returned.</p>
              )}
            </div>

            <div className="card">
              <h3 className="font-bold text-gray-900 mb-4">Top Pages</h3>
              <div className="space-y-3">
                {topPages.length > 0 ? (
                  topPages.map((page, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900 text-sm">{String(page.title || page.path || page.pagePath || '-')}</p>
                        <p className="text-xs text-gray-500">{String(page.path || page.pagePath || '')}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-gray-900">{Number(page.pageviews || page.screenPageViews || 0).toLocaleString()}</p>
                        <p className="text-xs text-gray-500">views</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-500">No top page data returned.</p>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-bold text-gray-900 mb-4">Top Search Queries</h3>
              <div className="space-y-3">
                {searchQueries.length > 0 ? (
                  searchQueries.map((query, idx) => {
                    const bounceRate = Number(query.bounce_rate || query.bounceRate || 0);
                    return (
                      <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div>
                          <p className="font-medium text-gray-900">{String(query.query || '-')}</p>
                          <p className="text-xs text-gray-500">{Number(query.sessions || 0).toLocaleString()} sessions</p>
                        </div>
                        <div className="text-right">
                          <p className={`text-sm font-semibold ${getBounceRateColor(bounceRate)}`}>
                            {(bounceRate * 100).toFixed(1)}% bounce
                          </p>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-gray-500">No query data returned.</p>
                )}
              </div>
            </div>

            <div className="card">
              <h3 className="font-bold text-gray-900 mb-4">Top Countries</h3>
              <div className="space-y-3">
                {countryData.length > 0 ? (
                  countryData.map((country, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <Globe className="w-5 h-5 text-gray-400" />
                        <p className="font-medium text-gray-900">{String(country.country || '-')}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-gray-900">{Number(country.sessions || 0).toLocaleString()}</p>
                        <p className="text-xs text-gray-500">sessions</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-500">No country data returned.</p>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default GA4Dashboard;
