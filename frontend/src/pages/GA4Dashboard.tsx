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
import { Users, Eye, MousePointer, TrendingUp, Calendar, Globe } from 'lucide-react';
import { api, GA4FullReport } from '../services/api';

const COLORS = ['#18CFE3', '#073B5C', '#0E7490', '#8EEAF3', '#061A33'];

const GA4Dashboard: React.FC = () => {
  const { propertyId } = useParams();
  const [dateRange, setDateRange] = useState('30');
  const [ga4Data, setGa4Data] = useState<GA4FullReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!propertyId) return;

    const load = async () => {
      setIsLoading(true);
      setError('');
      try {
        setGa4Data(await api.getGA4Overview(propertyId, dateRange));
      } catch (err) {
        setGa4Data(null);
        setError(err instanceof Error ? err.message : 'Failed to load GA4 data');
      } finally {
        setIsLoading(false);
      }
    };

    load();
  }, [propertyId, dateRange]);

  const totals = ga4Data?.traffic_overview?.totals || {};
  const sessions = Number(totals.sessions || 0);
  const users = Number(totals.users || 0);
  const pageviews = Number(totals.pageviews || totals.screenPageViews || 0);
  const engagementRate = Number(totals.engagementRate || totals.engagement_rate || 0);
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
  const trafficData = sessions || users || pageviews ? [{ date: `Last ${dateRange} days`, sessions, users, pageviews }] : [];
  const topPages = ga4Data?.top_pages || [];
  const searchQueries = ga4Data?.search_queries || [];
  const countryData = ga4Data?.country_breakdown || [];

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
          <p className="text-gray-500 mt-1">Property: {propertyId}</p>
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
        </div>
      </div>

      {isLoading ? (
        <div className="card text-gray-500">Loading GA4 data...</div>
      ) : error ? (
        <div className="card text-red-600">{error}</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
