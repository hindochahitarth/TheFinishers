"use client"

import { useState, useEffect } from 'react'
import { LineChart, Line, Area, AreaChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ComposedChart, Bar, ReferenceLine } from 'recharts'
import { Cloud, AlertTriangle, TrendingUp, Loader2, Calendar, Database, Zap, Sparkles, Clock, MapPin, RefreshCw } from 'lucide-react'

interface ForecastPoint {
  timestamp: string
  aqi_predicted: number
  aqi_lower: number
  aqi_upper: number
  aqi_category: string
  pm25_predicted: number
  no2_predicted: number
  confidence: number
}

interface ForecastData {
  location_id: number
  generated_at: string
  horizon_hours: number
  model_name: string
  model_version: string
  model_type: string
  forecast: ForecastPoint[]
  feature_importance: Record<string, number>
}

const categoryColors: Record<string, string> = {
  'Good': '#2ecc71',
  'Satisfactory': '#27ae60',
  'Moderate': '#f1c40f',
  'Poor': '#e67e22',
  'Very Poor': '#e74c3c',
  'Severe': '#c0392b',
}

export default function ForecastPage() {
  const [forecast, setForecast] = useState<ForecastData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [horizonHours, setHorizonHours] = useState(24)

  useEffect(() => {
    fetchForecast()
  }, [horizonHours])

  const fetchForecast = async () => {
    try {
      setLoading(true)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/forecast/aqi?hours=${horizonHours}`
      )
      if (!response.ok) throw new Error('Failed to fetch forecast')
      const data = await response.json()
      setForecast(data)
      setError(null)
    } catch (err) {
      setError('Failed to load forecast data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
  }

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
  }

  const chartData = forecast?.forecast.map((point) => ({
    time: formatTime(point.timestamp),
    date: formatDate(point.timestamp),
    aqi: Math.round(point.aqi_predicted),
    lower: Math.round(point.aqi_lower),
    upper: Math.round(point.aqi_upper),
    pm25: point.pm25_predicted,
    no2: point.no2_predicted,
    confidence: Math.round(point.confidence * 100),
    category: point.aqi_category,
    range: [Math.round(point.aqi_lower), Math.round(point.aqi_upper)],
  })) || []

  if (loading && !forecast) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh]">
        <Loader2 className="w-10 h-10 animate-spin text-green-500 mb-4" />
        <p className="text-gray-500 font-bold tracking-widest text-xs uppercase animate-pulse">Consulting Predictive Models...</p>
      </div>
    )
  }

  return (
    <div className="max-w-[1400px] mx-auto space-y-8 pb-12 animate-fade-slide">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-5 h-5 text-green-500" />
            <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest leading-none">Intelligence / Forecast</span>
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">Environmental Projections</h1>
          <div className="flex items-center gap-4 mt-2">
            <div className="flex items-center gap-1.5 text-xs text-gray-500 font-medium">
              <Database className="w-3.5 h-3.5" />
              Model: <span className="text-gray-300">{forecast?.model_name || 'Ensemble'} v{forecast?.model_version}</span>
            </div>
            <div className="w-px h-3 bg-white/10" />
            <div className="flex items-center gap-1.5 text-xs text-gray-500 font-medium">
              <Zap className="w-3.5 h-3.5 text-yellow-500" />
              Engine: <span className="text-yellow-500/80 uppercase font-black">{forecast?.model_type === 'ml_ensemble' ? 'Edge Inference' : 'Deep Mock'}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 bg-white/5 p-1.5 rounded-2xl border border-white/5">
          {[24, 48, 72].map((h) => (
            <button
              key={h}
              onClick={() => setHorizonHours(h)}
              className={`px-6 py-2 rounded-xl text-xs font-black transition-all ${horizonHours === h
                ? 'bg-green-500 text-white shadow-lg shadow-green-500/20'
                : 'text-gray-500 hover:text-gray-300'
                }`}
            >
              {h}H WINDOW
            </button>
          ))}
          <div className="w-px h-4 bg-white/10 mx-1" />
          <button
            onClick={fetchForecast}
            className="p-2 bg-white/5 hover:bg-white/10 rounded-xl text-gray-400 hover:text-white transition-all shadow-xl"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error ? (
        <div className="glass-card p-16 text-center border-red-500/20 max-w-2xl mx-auto">
          <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>
          <h2 className="text-xl font-black text-white mb-2">Inference Pipeline Offline</h2>
          <p className="text-gray-500 mb-8 leading-relaxed">The predictive synchronization for location <span className="text-gray-300">#001</span> encountered an interruption. Verify backend connectivity and telemetry stream status.</p>
          <button onClick={fetchForecast} className="px-8 py-3 bg-white text-black font-black text-xs rounded-xl hover:scale-105 active:scale-95 transition-all tracking-widest uppercase">
            RETRY PIPELINE
          </button>
        </div>
      ) : (
        <>
          {/* Hero Chart Row */}
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
            <div className="xl:col-span-3 glass-card p-8">
              <div className="flex items-center justify-between mb-8">
                <div>
                  <h3 className="text-sm font-black text-white tracking-widest uppercase mb-1">AQI Projection Matrix</h3>
                  <p className="text-xs text-gray-500 font-medium italic">Shaded region indicates ±15% confidence interval shift</p>
                </div>
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]" />
                    <span className="text-[10px] font-black text-gray-500 uppercase">Median Predict</span>
                  </div>
                  <div className="flex items-center gap-2 opacity-50">
                    <div className="w-2.5 h-2.5 rounded bg-blue-500/40" />
                    <span className="text-[10px] font-black text-gray-500 uppercase">Confidence Band</span>
                  </div>
                </div>
              </div>

              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData}>
                    <defs>
                      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#22c55e" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="confGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.08} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                    <XAxis
                      dataKey="time"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: '#64748b', fontSize: 10, fontWeight: 'bold' }}
                      dy={10}
                    />
                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: '#64748b', fontSize: 10, fontWeight: 'bold' }}
                      domain={[0, (dataMax: number) => Math.ceil((dataMax + 50) / 50) * 50]}
                    />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.4)', color: '#fff' }}
                      cursor={{ stroke: '#22c55e', strokeWidth: 1, strokeDasharray: '4 4' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="upper"
                      stroke="none"
                      fill="url(#confGrad)"
                      animationDuration={2000}
                    />
                    <Area
                      type="monotone"
                      dataKey="lower"
                      stroke="none"
                      fill="#020617"
                      animationDuration={2000}
                    />
                    <Area
                      type="monotone"
                      dataKey="aqi"
                      stroke="#22c55e"
                      strokeWidth={3}
                      fill="url(#areaGrad)"
                      animationDuration={2500}
                      dot={{ r: 3, fill: '#22c55e', strokeWidth: 0 }}
                      activeDot={{ r: 5, fill: '#fff' }}
                    />
                    <ReferenceLine y={100} stroke="#eab308" strokeOpacity={0.2} strokeDasharray="3 3" />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Model Insight Sidebar */}
            <div className="space-y-6">
              <div className="glass-card p-6 bg-gradient-to-br from-indigo-500/[0.04] to-transparent">
                <div className="flex items-center gap-2 mb-6">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">Prediction Summary</h3>
                </div>
                {chartData.length > 0 && (
                  <div className="space-y-5">
                    <div>
                      <p className="text-[10px] font-bold text-gray-500 uppercase leading-none mb-2">Max Projected AQI</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-black text-white">{chartData.length > 0 ? Math.max(...chartData.map(d => d.aqi)) : '—'}</span>
                        <span className="text-xs font-bold text-red-500/80 uppercase">Warning</span>
                      </div>
                    </div>
                    <div className="w-full h-px bg-white/5" />
                    <div>
                      <p className="text-[10px] font-bold text-gray-500 uppercase leading-none mb-2">Avg Confidence</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-black text-white">{chartData.length > 0 ? Math.round(chartData.reduce((acc, d) => acc + d.confidence, 0) / chartData.length) : 0}%</span>
                        <span className="text-xs font-bold text-green-500/80 uppercase">High</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Feature Importance List */}
              <div className="glass-card p-6">
                <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-6 leading-none">Causal Importance</h3>
                <div className="space-y-4">
                  {Object.entries(forecast?.feature_importance || {})
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 5)
                    .map(([name, val], i) => (
                      <div key={name} className="flex items-center gap-3">
                        <span className="text-[10px] font-black text-white/20 w-4">0{i + 1}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-[10px] font-bold text-gray-400 uppercase truncate pr-2" title={name}>{name.split('_').slice(0, 2).join(' ')}</span>
                            <span className="text-[10px] font-black text-white">{(val * 100).toFixed(0)}%</span>
                          </div>
                          <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-green-500" style={{ width: `${val * 100}%` }} />
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>

          {/* Pollutant Detail Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="glass-card p-8">
              <div className="flex items-center gap-2 mb-6">
                <div className="w-1.5 h-1.5 rounded-full bg-orange-400 shadow-[0_0_8px_rgba(251,146,60,0.5)]" />
                <h3 className="text-xs font-black text-white uppercase tracking-widest">Pollutant Variability (PM2.5 / Fine)</h3>
              </div>
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                    <XAxis dataKey="time" hide />
                    <YAxis hide domain={['auto', 'auto']} />
                    <Tooltip />
                    <Line type="monotone" dataKey="pm25" stroke="#f97316" strokeWidth={2} dot={false} animationDuration={3000} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="glass-card p-8">
              <div className="flex items-center gap-2 mb-6">
                <div className="w-1.5 h-1.5 rounded-full bg-purple-400 shadow-[0_0_8px_rgba(167,139,250,0.5)]" />
                <h3 className="text-xs font-black text-white uppercase tracking-widest">Pollutant Variability (NO2 / Nitrogen)</h3>
              </div>
              <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                    <XAxis dataKey="time" hide />
                    <YAxis hide domain={['auto', 'auto']} />
                    <Tooltip />
                    <Area type="monotone" dataKey="no2" stroke="#8b5cf6" fill="#8b5cf611" strokeWidth={2} animationDuration={3000} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Prediction Table */}
          <div className="glass-card overflow-hidden">
            <div className="px-8 py-6 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
              <h3 className="text-sm font-black text-white tracking-widest uppercase">Granular Prediction Log</h3>
              <span className="text-[10px] font-bold text-gray-500 uppercase">{forecast?.forecast.length} Data Points Available</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-white/[0.01]">
                    <th className="px-8 py-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Time Vector</th>
                    <th className="px-8 py-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">AQI Index</th>
                    <th className="px-8 py-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Confidence</th>
                    <th className="px-8 py-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">Status / Risk</th>
                    <th className="px-8 py-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">PM2.5 (µg)</th>
                    <th className="px-8 py-4 text-[10px] font-black text-gray-500 uppercase tracking-widest text-right">Metric Shift</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {chartData.slice(0, 12).map((row, i) => (
                    <tr key={i} className="group hover:bg-white/[0.02] transition-colors">
                      <td className="px-8 py-4">
                        <p className="text-xs font-bold text-white leading-none">{row.time}</p>
                        <p className="text-[10px] font-medium text-gray-500 mt-1">{row.date}</p>
                      </td>
                      <td className="px-8 py-4">
                        <span className="text-sm font-black text-white font-metric">{row.aqi}</span>
                      </td>
                      <td className="px-8 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-12 h-1.5 bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-blue-500" style={{ width: `${row.confidence}%` }} />
                          </div>
                          <span className="text-[10px] font-bold text-gray-400">{row.confidence}%</span>
                        </div>
                      </td>
                      <td className="px-8 py-4">
                        <span className="px-2 py-0.5 rounded text-[9px] font-black border uppercase"
                          style={{
                            color: categoryColors[row.category],
                            borderColor: `${categoryColors[row.category]}33`,
                            background: `${categoryColors[row.category]}11`
                          }}>
                          {row.category}
                        </span>
                      </td>
                      <td className="px-8 py-4">
                        <span className="text-xs font-bold text-orange-400/80 font-metric">{row.pm25.toFixed(1)}</span>
                      </td>
                      <td className="px-8 py-4 text-right">
                        <span className="text-[10px] font-black text-gray-500">{(row.upper - row.lower).toFixed(0)} ∆ Range</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
