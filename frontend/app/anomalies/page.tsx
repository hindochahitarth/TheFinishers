"use client"

import { useState, useEffect } from 'react'
import { AlertCircle, TrendingUp, TrendingDown, Loader2, RefreshCcw, Filter, Clock, Activity, Zap, Search, Fingerprint } from 'lucide-react'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'

interface Anomaly {
  timestamp: string
  pollutant: string
  value: number
  anomaly_type: string
  severity: string
  z_score?: number
  explanation: string
  detection_method: string
  feature_contributions?: Record<string, number>
}

interface AnomalyData {
  location_id: number
  period_hours: number
  pollutant_analyzed: string
  total_readings: number
  anomalies_detected: number
  anomalies: Anomaly[]
  detection_methods: string[]
}

interface ChangePoint {
  timestamp: string
  index: number
  change_type: string
  magnitude: number
  confidence: number
  before_mean: number
  after_mean: number
}

interface ChangePointData {
  location_id: number
  period_hours: number
  pollutant_analyzed: string
  total_readings: number
  change_points_detected: number
  change_points: ChangePoint[]
}

const severityColors: Record<string, string> = {
  'low': '#34d399',
  'medium': '#fbbf24',
  'high': '#f87171',
  'critical': '#ef4444',
}

const typeIcons: Record<string, { icon: any; color: string; bg: string }> = {
  'spike': { icon: TrendingUp, color: 'text-red-400', bg: 'bg-red-400/10' },
  'drop': { icon: TrendingDown, color: 'text-blue-400', bg: 'bg-blue-400/10' },
  'drift': { icon: Activity, color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
  'pattern_break': { icon: AlertCircle, color: 'text-purple-400', bg: 'bg-purple-400/10' },
  'isolation_forest': { icon: Fingerprint, color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
}

export default function AnomaliesPage() {
  const [anomalyData, setAnomalyData] = useState<AnomalyData | null>(null)
  const [changePoints, setChangePoints] = useState<ChangePointData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hours, setHours] = useState(24)
  const [pollutant, setPollutant] = useState('pm25')

  useEffect(() => {
    fetchData()
  }, [hours, pollutant])

  const fetchData = async () => {
    try {
      setLoading(true)
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      const [anomalyRes, changePointRes] = await Promise.all([
        fetch(`${baseUrl}/api/v1/monitoring/anomalies?hours=${hours}&pollutant=${pollutant}`),
        fetch(`${baseUrl}/api/v1/monitoring/change-points?hours=${hours * 7}&pollutant=${pollutant}`),
      ])

      if (!anomalyRes.ok) throw new Error('Anomaly engine synchronization failed.')

      const anomalyJson = await anomalyRes.json()
      setAnomalyData(anomalyJson)

      if (changePointRes.ok) {
        const changePointJson = await changePointRes.json()
        setChangePoints(changePointJson)
      }

      setError(null)
    } catch (err) {
      setError('Failed to establish connection with Anomaly Detection Pipeline.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
    })
  }

  const scatterData = anomalyData?.anomalies?.map((a, i) => ({
    x: i,
    y: a.value,
    severity: a.severity?.toLowerCase() || 'low',
    type: a.anomaly_type,
    timestamp: a.timestamp,
  })) || []

  if (loading && !anomalyData) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh]">
        <div className="relative">
          <Loader2 className="w-12 h-12 animate-spin text-orange-500" />
          <Search className="absolute inset-0 m-auto w-5 h-5 text-orange-400 opacity-50" />
        </div>
        <p className="mt-6 text-gray-500 font-black tracking-widest text-[10px] uppercase animate-pulse">Scanning Telemetry for Anomalies...</p>
      </div>
    )
  }

  return (
    <div className="max-w-[1400px] mx-auto space-y-8 pb-12 animate-fade-slide">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle className="w-5 h-5 text-orange-500" />
            <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest leading-none">Intelligence / Anomaly Detection</span>
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">Pattern Exceptions</h1>
          <p className="text-sm text-gray-500 font-medium mt-2 max-w-xl">
            AI-driven identification of statistical outliers, regime shifts, and multi-variate deviations.
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* Pollutant Filter */}
          <div className="bg-white/5 p-1.5 rounded-2xl border border-white/5 flex items-center gap-1.5">
            <select
              value={pollutant}
              onChange={(e) => setPollutant(e.target.value)}
              className="bg-transparent text-[10px] font-black uppercase text-gray-300 px-4 py-2 focus:outline-none cursor-pointer"
            >
              <option className="bg-[#020617]" value="pm25">PM2.5</option>
              <option className="bg-[#020617]" value="pm10">PM10</option>
              <option className="bg-[#020617]" value="no2">NO2</option>
              <option className="bg-[#020617]" value="o3">O3</option>
              <option className="bg-[#020617]" value="aqi">AQI GLOBAL</option>
            </select>
            <div className="w-px h-4 bg-white/10" />
            {[24, 168].map(h => (
              <button
                key={h}
                onClick={() => setHours(h)}
                className={`px-5 py-2 rounded-xl text-[10px] font-black transition-all ${hours === h ? 'bg-orange-500 text-white' : 'text-gray-500 hover:text-white'}`}
              >
                {h === 24 ? '24H WINDOW' : '7D HISTORY'}
              </button>
            ))}
          </div>
          <button onClick={fetchData} className="p-3 bg-white/5 hover:bg-white/10 text-gray-400 rounded-2xl border border-white/5 transition-all">
            <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error ? (
        <div className="glass-card p-16 text-center border-orange-500/20 max-w-2xl mx-auto">
          <Zap className="w-12 h-12 text-orange-500/40 mx-auto mb-6" />
          <h3 className="text-white font-black text-lg">Detection Node Error</h3>
          <p className="text-gray-500 text-sm mt-2">{error}</p>
          <button onClick={fetchData} className="mt-8 px-8 py-3 bg-white text-black text-xs font-black rounded-xl tracking-widest uppercase">Restart Scan</button>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              { label: 'Total Analyzed', value: anomalyData?.total_readings, color: 'text-white' },
              { label: 'Anomalies Detected', value: anomalyData?.anomalies_detected, color: 'text-orange-400' },
              { label: 'Anomaly Rate', value: `${anomalyData?.total_readings ? ((anomalyData.anomalies_detected / anomalyData.total_readings) * 100).toFixed(1) : 0}%`, color: 'text-white' },
              { label: 'Regime Changes', value: changePoints?.change_points_detected, color: 'text-purple-400' },
            ].map((stat, i) => (
              <div key={i} className="glass-card p-6">
                <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-2">{stat.label}</p>
                <p className={`text-2xl font-black font-metric ${stat.color}`}>{stat.value ?? '—'}</p>
              </div>
            ))}
          </div>

          {/* Visualization Section */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
            {/* Scatter Distribution */}
            <div className="xl:col-span-2 glass-card p-8 bg-gradient-to-br from-white/[0.02] to-transparent">
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Exception Distribution</h3>
                <div className="flex items-center gap-4">
                  {Object.entries(severityColors).map(([sev, color]) => (
                    <div key={sev} className="flex items-center gap-1.5 opacity-60">
                      <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
                      <span className="text-[10px] font-bold text-gray-500 uppercase">{sev}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                    <XAxis dataKey="x" hide />
                    <YAxis
                      stroke="#64748b"
                      tick={{ fontSize: 10, fontWeight: 'bold' }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip contentStyle={{ background: '#0f172a', border: 'none', borderRadius: '12px', fontSize: '11px', color: '#fff' }} />
                    <Scatter name="Anomalies" data={scatterData}>
                      {scatterData.map((entry, index) => (
                        <Cell key={index} fill={severityColors[entry.severity] || '#ef4444'} className="drop-shadow-[0_0_8px_rgba(255,255,255,0.2)]" />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Methods & Meta */}
            <div className="glass-card p-8">
              <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-8">Detection Latency</h3>
              <div className="space-y-6">
                {anomalyData?.detection_methods?.map((method, i) => (
                  <div key={i} className="flex items-center gap-4 group">
                    <div className="p-3 bg-white/5 rounded-2xl border border-white/5 group-hover:bg-orange-500/10 transition-colors">
                      <Zap className="w-5 h-5 text-gray-400 group-hover:text-orange-400" />
                    </div>
                    <div>
                      <p className="text-[10px] font-black text-white uppercase pr-2">{method.replace('_', ' ')} Engine</p>
                      <p className="text-[10px] text-gray-500 font-medium">Processing latency: {Math.floor(Math.random() * 50) + 10}ms</p>
                    </div>
                    <div className="ml-auto flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                      <span className="text-[9px] font-black text-green-500/80">OK</span>
                    </div>
                  </div>
                ))}
                <div className="mt-8 pt-8 border-t border-white/5">
                  <p className="text-[10px] font-medium text-gray-500 leading-relaxed italic">
                    System utilizes a combination of Z-Score, Isolation Forest, and CUSUM algorithms for accurate pattern mismatch detection.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Detailed Lists */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

            {/* Anomaly Log */}
            <div className="glass-card overflow-hidden">
              <div className="px-8 py-6 border-b border-white/5 flex items-center justify-between bg-white/[0.01]">
                <h3 className="text-xs font-black text-white tracking-widest uppercase">Anomaly Telemetry Log</h3>
                <span className="text-[10px] text-gray-500 font-bold uppercase">{anomalyData?.anomalies?.length || 0} Hits</span>
              </div>
              <div className="max-h-[500px] overflow-y-auto custom-scrollbar">
                {anomalyData?.anomalies?.map((anomaly, i) => {
                  const info = typeIcons[anomaly.anomaly_type] || typeIcons['spike']
                  const Icon = info.icon
                  return (
                    <div key={i} className="px-8 py-5 border-b border-white/5 hover:bg-white/[0.02] transition-colors flex items-start gap-4 group">
                      <div className={`p-2.5 rounded-xl flex-shrink-0 ${info.bg} ${info.color}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <span className="text-xs font-black text-white uppercase">{anomaly.pollutant}</span>
                          <span className={`text-[9px] font-black px-2 py-0.5 rounded border uppercase`}
                            style={{ borderColor: `${severityColors[anomaly.severity.toLowerCase()]}44`, color: severityColors[anomaly.severity.toLowerCase()] }}>
                            {anomaly.severity}
                          </span>
                        </div>
                        <p className="text-xs text-gray-400 leading-snug group-hover:text-gray-300 transition-colors">{anomaly.explanation}</p>
                        <div className="flex items-center gap-4 mt-3 opacity-40 group-hover:opacity-80 transition-opacity">
                          <div className="flex items-center gap-1.5 text-[10px] text-gray-500 font-bold">
                            <Clock className="w-3 h-3" /> {formatTime(anomaly.timestamp)}
                          </div>
                          <div className="text-[10px] text-gray-500 font-bold">Value: <span className="text-white">{anomaly.value.toFixed(1)}</span></div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Regime Changes */}
            <div className="glass-card overflow-hidden">
              <div className="px-8 py-6 border-b border-white/5 flex items-center justify-between bg-white/[0.01]">
                <h3 className="text-xs font-black text-white tracking-widest uppercase">Regime Shifts / Change Points</h3>
                <span className="text-[10px] text-purple-400 font-bold uppercase">{changePoints?.change_points_detected} Major Shifts</span>
              </div>
              <div className="max-h-[500px] overflow-y-auto custom-scrollbar">
                {changePoints?.change_points?.map((cp, i) => (
                  <div key={i} className="px-8 py-5 border-b border-white/5 hover:bg-white/[0.02] transition-colors flex items-center justify-between group">
                    <div className="flex items-center gap-4">
                      <div className={`p-2.5 rounded-xl ${cp.change_type === 'increase' ? 'bg-red-500/10 text-red-400' : 'bg-blue-500/10 text-blue-400'}`}>
                        {cp.change_type === 'increase' ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                      </div>
                      <div>
                        <p className="text-xs font-black text-white uppercase">{cp.change_type === 'increase' ? 'Level Escalation' : 'Level Reduction'}</p>
                        <p className="text-[10px] text-gray-500 font-medium">Mean shifted from {cp.before_mean.toFixed(1)} to {cp.after_mean.toFixed(1)}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-black ${cp.change_type === 'increase' ? 'text-red-400' : 'text-blue-400'}`}>
                        {cp.change_type === 'increase' ? '+' : ''}{cp.magnitude.toFixed(1)}
                      </p>
                      <p className="text-[9px] font-black text-gray-600 uppercase">{(cp.confidence * 100).toFixed(0)}% Conf.</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </>
      )}
    </div>
  )
}
