"use client"

import { useState, useEffect } from 'react'
import { CheckCircle2, AlertCircle, ShieldCheck, Scale, Info, Loader2, RefreshCw, Landmark, ExternalLink, Globe } from 'lucide-react'

interface ComplianceReport {
  location_id: number
  assessed_at: string
  period_hours: number
  risk_level: string
  overall_compliance: boolean
  standards: Record<string, {
    pollutants: Record<string, {
      value: number
      limit: number
      unit: string
      compliant: boolean
      exceedance_pct: number
    }>
    score: number
    passed: boolean
  }>
  recommendations: string[]
}

const riskColors: Record<string, string> = {
  'Low': 'text-green-400 bg-green-500/10 border-green-500/20',
  'Moderate': 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  'High': 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  'Critical': 'text-red-400 bg-red-500/10 border-red-500/20',
}

export default function CompliancePage() {
  const [report, setReport] = useState<ComplianceReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [period, setPeriod] = useState(24)

  useEffect(() => {
    fetchCompliance()
  }, [period])

  const fetchCompliance = async () => {
    try {
      setLoading(true)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/compliance/assess?period_hours=${period}`
      )
      if (!response.ok) throw new Error('Failed to fetch compliance assessment')
      const data = await response.json()
      setReport(data)
      setError(null)
    } catch (err) {
      setError('Could not establish connection to the compliance audit engine.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  if (loading && !report) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh]">
        <div className="relative">
          <Loader2 className="w-12 h-12 animate-spin text-emerald-500" />
          <Landmark className="absolute inset-0 m-auto w-5 h-5 text-emerald-500/50" />
        </div>
        <p className="mt-6 text-gray-500 font-black tracking-widest text-[10px] uppercase animate-pulse">Running Regulatory Audit...</p>
      </div>
    )
  }

  return (
    <div className="max-w-[1400px] mx-auto space-y-8 pb-12 animate-fade-slide">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck className="w-5 h-5 text-emerald-500" />
            <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest leading-none">Governance / Compliance Audit</span>
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight">Regulatory Assessment</h1>
          <p className="text-sm text-gray-500 font-medium mt-2 max-w-xl">
            Real-time audit against international and national environmental benchmarks (WHO, CPCB, NAAQS).
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-white/5 p-1.5 rounded-2xl border border-white/5">
            {[24, 168].map(h => (
              <button
                key={h}
                onClick={() => setPeriod(h)}
                className={`px-5 py-2 rounded-xl text-[10px] font-black transition-all ${period === h ? 'bg-emerald-500 text-white' : 'text-gray-500 hover:text-white'}`}
              >
                {h === 24 ? '24H WINDOW' : '7D AUDIT'}
              </button>
            ))}
          </div>
          <button onClick={fetchCompliance} className="p-3 bg-white/5 hover:bg-white/10 text-gray-400 rounded-2xl border border-white/5 transition-all">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error ? (
        <div className="glass-card p-16 text-center border-red-500/20 max-w-2xl mx-auto">
          <AlertCircle className="w-12 h-12 text-red-500/40 mx-auto mb-6" />
          <h3 className="text-white font-black text-lg">Audit Engine Offline</h3>
          <p className="text-gray-500 text-sm mt-2">{error}</p>
          <button onClick={fetchCompliance} className="mt-8 px-8 py-3 bg-white text-black text-xs font-black rounded-xl tracking-widest uppercase">Reconnect</button>
        </div>
      ) : report && (
        <div className="space-y-8">

          {/* Executive Summary Card */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
            <div className="xl:col-span-4 glass-card p-8 bg-gradient-to-br from-white/[0.02] to-transparent relative overflow-hidden">
              <div className="absolute -top-12 -right-12 w-48 h-48 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
              <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-8">Executive Status</h3>

              <div className="flex flex-col items-center text-center py-4">
                <div className={`w-24 h-24 rounded-full border-2 flex items-center justify-center mb-6 ${report.overall_compliance ? 'border-green-500 shadow-[0_0_30px_rgba(34,197,94,0.2)]' : 'border-red-500 shadow-[0_0_30px_rgba(239,68,68,0.2)]'}`}>
                  {report.overall_compliance ? <CheckCircle2 className="w-12 h-12 text-green-500" /> : <AlertCircle className="w-12 h-12 text-red-500" />}
                </div>
                <div className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border ${riskColors[report.risk_level] || ''}`}>
                  {report.risk_level} Risk Level
                </div>
                <h2 className="text-2xl font-black text-white mt-6 leading-tight">
                  Station is <span className={report.overall_compliance ? 'text-green-500' : 'text-red-500'}>
                    {report.overall_compliance ? 'Fully Compliant' : 'Non-Compliant'}
                  </span>
                </h2>
                <p className="text-xs text-gray-500 font-medium mt-2">Audit generated at {new Date(report.assessed_at).toLocaleTimeString()}</p>
              </div>
            </div>

            <div className="xl:col-span-8 glass-card p-8">
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Standard breakdown</h3>
                <div className="flex gap-4">
                  {report.standards && Object.keys(report.standards).map(s => (
                    <div key={s} className="flex items-center gap-1.5">
                      <div className={`w-1.5 h-1.5 rounded-full ${report.standards[s].passed ? 'bg-green-500' : 'bg-red-500'}`} />
                      <span className="text-[10px] font-black text-white">{s}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-8">
                {report && report.standards && Object.entries(report.standards).map(([stdName, stdData]) => (
                  <div key={stdName} className="relative group">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-4">
                        <Landmark className={`w-5 h-5 ${stdData.passed ? 'text-green-500' : 'text-red-500'}`} />
                        <div>
                          <h4 className="text-sm font-black text-white">{stdName} Guidelines</h4>
                          <p className="text-[10px] text-gray-500 font-medium">Compliance Score: {stdData.score}%</p>
                        </div>
                      </div>
                      <div className={`text-[10px] font-black uppercase px-2 py-0.5 rounded ${stdData.passed ? 'text-green-500 bg-green-500/10' : 'text-red-500 bg-red-500/10'}`}>
                        {stdData.passed ? 'PASS' : 'FAIL'}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                      {Object.entries(stdData.pollutants).map(([poll, details]) => (
                        <div key={poll} className={`p-4 rounded-2xl border transition-all ${details.compliant ? 'bg-green-500/[0.02] border-white/5' : 'bg-red-500/[0.04] border-red-500/20'}`}>
                          <p className="text-[10px] font-black text-gray-500 uppercase mb-2">{poll}</p>
                          <p className={`text-lg font-black font-metric ${details.compliant ? 'text-white' : 'text-red-400'}`}>{details.value.toFixed(1)}</p>
                          <p className="text-[10px] font-medium text-gray-600">Limit: {details.limit}</p>
                          {!details.compliant && (
                            <div className="mt-3 text-[9px] font-black text-red-500 uppercase">+{details.exceedance_pct.toFixed(0)}% EXC</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recommendations Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 glass-card p-8 bg-gradient-to-br from-indigo-500/[0.03] to-transparent">
              <div className="flex items-center gap-2 mb-8">
                <Info className="w-4 h-4 text-indigo-400" />
                <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-widest leading-none">Mitigation Protocols</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {report && report.recommendations && report.recommendations.map((rec, i) => (
                  <div key={i} className="flex gap-4 p-4 rounded-2xl bg-white/[0.02] border border-white/5 items-start">
                    <div className="mt-1 w-5 h-5 rounded bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
                      <span className="text-[10px] font-black text-indigo-400">{i + 1}</span>
                    </div>
                    <p className="text-xs font-medium text-gray-300 leading-relaxed">{rec}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-card p-8 flex flex-col justify-center">
              <Globe className="w-10 h-10 text-emerald-500/20 mb-6" />
              <h3 className="text-sm font-black text-white tracking-widest uppercase mb-4 leading-tight">Global Alignment</h3>
              <p className="text-xs text-gray-500 font-medium leading-relaxed mb-6">
                GreenPulse AI uses ISO-certified calculation methods. Our data is cross-referenced with the World Air Quality Index (WAQI) for high-fidelity verification.
              </p>
              <button className="w-full py-3 bg-white/5 hover:bg-white/10 text-white text-[10px] font-black rounded-xl transition-all border border-white/5 flex items-center justify-center gap-2 tracking-widest uppercase">
                Verify Proof of Service <ExternalLink className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
