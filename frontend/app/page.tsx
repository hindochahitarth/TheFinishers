import Link from 'next/link'
import { useEffect, useState, useCallback } from 'react'
import { RefreshCw, Wind, Thermometer, Droplets, Car, AlertTriangle, CheckCircle2, MapPin, Calendar, Clock, Activity, Fingerprint, Leaf, Zap, Bot, ShieldCheck, Gauge, Cloud } from 'lucide-react'
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart, ReferenceLine
} from 'recharts'
import AQIGauge from '@/components/AQIGauge'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const cat2color = (cat: string) => ({
    Good: '#2ecc71', Satisfactory: '#27ae60', Moderate: '#f1c40f',
    Poor: '#e67e22', 'Very Poor': '#e74c3c', Severe: '#c0392b',
}[cat] || '#94a3b8')

function StatCard({ label, value, unit, icon: Icon, color = '#22c55e', trend }: any) {
    return (
        <div className="glass-card p-5 animate-fade-slide group overflow-visible">
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-white/5 group-hover:bg-white/10 transition-colors">
                        <Icon className="w-4 h-4" style={{ color }} />
                    </div>
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.1em]">{label}</span>
                </div>
                {trend && (
                    <span className={`text-[10px] font-bold ${trend > 0 ? 'text-red-400' : 'text-green-400'}`}>
                        {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
                    </span>
                )}
            </div>
            <div className="flex items-baseline gap-1">
                <span className="text-3xl font-extrabold font-metric tracking-tight text-white group-hover:text-glow-green transition-all">
                    {value ?? '—'}
                </span>
                <span className="text-xs font-semibold text-gray-500">{unit}</span>
            </div>
            {/* Subtle light effect on hover */}
            <div className="absolute inset-0 bg-gradient-to-br from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
        </div>
    )
}

function PollutantBar({ label, value, max, color }: any) {
    const pct = Math.min(100, ((value || 0) / max) * 100)
    return (
        <div className="mb-4 group">
            <div className="flex justify-between items-end mb-2">
                <div>
                    <span className="text-xs font-bold text-gray-400 group-hover:text-white transition-colors">{label}</span>
                </div>
                <div className="flex items-baseline gap-1">
                    <span className="text-sm font-bold font-metric text-white">{value?.toFixed(1) ?? '—'}</span>
                    <span className="text-[10px] text-gray-500 font-medium">µg/m³</span>
                </div>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden p-[1px] border border-white/5">
                <div className="h-full rounded-full transition-all duration-1000 cubic-bezier(0.4, 0, 0.2, 1)"
                    style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}22, ${color})`, boxShadow: `0 0 12px ${color}40` }} />
            </div>
        </div>
    )
}

export default function Dashboard() {
    const [data, setData] = useState<any>(null)
    const [history, setHistory] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [refreshing, setRefreshing] = useState(false)

    const fetchData = useCallback(async (refresh = false) => {
        if (refresh) setRefreshing(true)
        try {
            const [cur, hist] = await Promise.all([
                fetch(`${API}/api/v1/monitoring/current`).then(r => r.json()),
                fetch(`${API}/api/v1/monitoring/history?hours=24&location_id=1`).then(r => r.json()),
            ])
            setData(cur)
            const chartData = (hist.readings || []).slice(0, 48).reverse().map((r: any) => ({
                time: new Date(r.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }),
                aqi: r.aqi ? Math.round(r.aqi) : null,
                pm25: r.pollutants?.pm25?.toFixed(1),
                no2: r.pollutants?.no2?.toFixed(1),
            }))
            setHistory(chartData)
        } catch (e) {
            console.error('Data fetch error:', e)
        } finally {
            setLoading(false)
            setRefreshing(false)
        }
    }, [])

    useEffect(() => { fetchData() }, [fetchData])

    // WebSocket live updates
    useEffect(() => {
        const WS = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
        let ws: WebSocket
        const connect = () => {
            try {
                ws = new WebSocket(`${WS}/ws/live`)
                ws.onmessage = (e) => {
                    const msg = JSON.parse(e.data)
                    if (msg.type === 'update') fetchData()
                }
                ws.onclose = () => setTimeout(connect, 5000)
            } catch { }
        }
        connect()
        return () => ws?.close()
    }, [fetchData])

    if (loading) return (
        <div className="flex flex-col items-center justify-center h-[60vh]">
            <div className="relative">
                <div className="w-16 h-16 border-4 border-green-500/10 border-t-green-500 rounded-full animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                    <Leaf className="w-6 h-6 text-green-500 animate-pulse" />
                </div>
            </div>
            <p className="text-gray-500 font-medium mt-6 animate-pulse">Initializing Environmental Intelligence...</p>
        </div>
    )

    const reading = data?.reading
    const location = data?.location
    const p = reading?.pollutants || {}
    const w = reading?.weather || {}
    const t = reading?.traffic || {}
    const aqiValue = reading?.aqi || 0
    const aqiCat = reading?.aqi_category || 'Unknown'
    const aqiColor = cat2color(aqiCat)

    return (
        <div className="max-w-[1600px] mx-auto space-y-8 pb-12 animate-fade-slide">
            {/* Top Bar / Stats */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <MapPin className="w-4 h-4 text-green-500" />
                        <h1 className="text-2xl font-black text-white tracking-tight">
                            Environmental Intelligence <span className="text-green-500 opacity-50 font-medium">/</span> {location?.city || 'New Delhi'}
                        </h1>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-500 font-medium">
                        <div className="flex items-center gap-1.5 leading-none">
                            <Calendar className="w-3.5 h-3.5" />
                            {reading?.timestamp ? new Date(reading.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '—'}
                        </div>
                        <div className="w-px h-3 bg-white/10" />
                        <div className="flex items-center gap-1.5 leading-none">
                            <Clock className="w-3.5 h-3.5" />
                            {reading?.timestamp ? new Date(reading.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '—'}
                        </div>
                        <div className="w-px h-3 bg-white/10" />
                        <div className="flex items-center gap-2 text-green-500/80">
                            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                            Live Telemetry
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button onClick={() => fetchData(true)}
                        className="group flex items-center gap-2 px-5 py-2.5 bg-green-500/10 text-green-400 font-bold text-xs rounded-xl border border-green-500/20 hover:bg-green-500/20 hover:border-green-500/40 transition-all active:scale-95 shadow-lg shadow-green-900/10">
                        <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
                        SYSTEM REFRESH
                    </button>
                </div>
            </div>

            {/* Alert Banner / Status */}
            <div className={`glass-card p-1.5 border-l-4 ${data?.alert_count > 0 ? 'border-orange-500' : 'border-green-500'}`}>
                <div className={`px-4 py-3 rounded-[14px] flex items-center justify-between ${data?.alert_count > 0 ? 'bg-orange-500/5' : 'bg-green-500/5'}`}>
                    <div className="flex items-center gap-4">
                        {data?.alert_count > 0 ? (
                            <div className="w-10 h-10 rounded-full bg-orange-500/10 flex items-center justify-center">
                                <AlertTriangle className="w-5 h-5 text-orange-400" />
                            </div>
                        ) : (
                            <div className="w-10 h-10 rounded-full bg-green-500/10 flex items-center justify-center">
                                <CheckCircle2 className="w-5 h-5 text-green-400" />
                            </div>
                        )}
                        <div>
                            <p className="text-sm font-bold text-white leading-tight">
                                {data?.alert_count > 0
                                    ? `${data.alert_count} ACTIVE ENVIRONMENTAL ALERTS DETECTED`
                                    : 'OPTIMAL ENVIRONMENTAL CONDITIONS MAINTAINED'}
                            </p>
                            <p className="text-xs text-gray-500 font-medium mt-0.5">
                                Compliance Assessment: <span className={data?.alert_count > 0 ? 'text-orange-400' : 'text-green-400'}>{data?.compliance_status}</span>
                            </p>
                        </div>
                    </div>
                    {data?.alert_count > 0 && (
                        <Link href="/alerts">
                            <button className="px-4 py-1.5 bg-orange-500/20 hover:bg-orange-500/30 text-orange-400 text-[10px] font-black rounded-lg transition-colors border border-orange-500/20">
                                VIEW ALERTS
                            </button>
                        </Link>
                    )}
                </div>
            </div>

            {/* Main Grid: Data Visualization */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">

                {/* Left Side: Major Metrics */}
                <div className="xl:col-span-8 space-y-8">

                    {/* Hero Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="glass-card p-8 flex flex-col items-center justify-center md:col-span-1 relative">
                            <div className="absolute top-4 left-6 flex items-center gap-2">
                                <Activity className="w-3.5 h-3.5 text-gray-500" />
                                <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Core Index</span>
                            </div>
                            <div className="my-2">
                                <AQIGauge aqi={aqiValue} category={aqiCat} size="lg" />
                            </div>
                            <div className="w-full mt-4 pt-4 border-t border-white/5 flex items-center justify-between">
                                <div className="text-center">
                                    <p className="text-[9px] font-bold text-gray-600 uppercase">Dominant</p>
                                    <p className="text-xs font-black text-green-500 uppercase">{reading?.dominant_pollutant || '—'}</p>
                                </div>
                                <div className="text-center">
                                    <p className="text-[9px] font-bold text-gray-600 uppercase">Quality</p>
                                    <p className="text-xs font-black text-white uppercase">{aqiValue < 50 ? '98%' : aqiValue < 100 ? '82%' : '45%'}</p>
                                </div>
                                <div className="text-center">
                                    <p className="text-[9px] font-bold text-gray-600 uppercase">Trust</p>
                                    <p className="text-xs font-black text-white uppercase">Verified</p>
                                </div>
                            </div>
                        </div>

                        <div className="glass-card p-8 md:col-span-2">
                            <div className="flex items-center justify-between mb-8">
                                <div className="flex items-center gap-2">
                                    <Fingerprint className="w-4 h-4 text-green-500" />
                                    <h3 className="text-[10px] font-black text-gray-500 uppercase tracking-widest leading-none">Pollutant Fingerprint</h3>
                                </div>
                                <span className="text-[10px] text-gray-600 font-medium bg-white/5 px-2 py-0.5 rounded leading-none">µg/m³ units</span>
                            </div>
                            <div className="grid grid-cols-2 gap-x-12 gap-y-2">
                                <PollutantBar label="PM2.5 / Fine Dust" value={p.pm25} max={150} color="#ff4d4d" />
                                <PollutantBar label="PM10 / Coarse Dust" value={p.pm10} max={250} color="#ff8e3c" />
                                <PollutantBar label="NO₂ / Nitrogen Dioxide" value={p.no2} max={200} color="#ffbe0b" />
                                <PollutantBar label="O₃ / Ozone" value={p.o3} max={180} color="#2ecc71" />
                                <PollutantBar label="SO₂ / Sulfur Dioxide" value={p.so2} max={150} color="#a29bfe" />
                                <PollutantBar label="CO / Carbon Monoxide" value={p.co ? p.co * 10 : null} max={100} color="#0984e3" />
                            </div>
                        </div>
                    </div>

                    {/* Historical Chart */}
                    <div className="glass-card p-8">
                        <div className="flex items-center justify-between mb-8">
                            <div>
                                <h3 className="text-sm font-black text-white tracking-wide uppercase">Environmental Trend Analysis</h3>
                                <p className="text-xs text-gray-500 font-medium mt-1">Predictive patterns over last 24-hours sequence</p>
                            </div>
                            <div className="flex items-center gap-6">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
                                    <span className="text-[10px] font-black text-gray-500 uppercase">AQI Index</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded bg-red-400 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
                                    <span className="text-[10px] font-black text-gray-500 uppercase">PM2.5 Level</span>
                                </div>
                            </div>
                        </div>
                        <div className="h-[280px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={history} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                                    <defs>
                                        <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#22c55e" stopOpacity={0.2} />
                                            <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                                    <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#6b7280', fontWeight: 'bold' }} interval="preserveStartEnd" dy={10} />
                                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#6b7280', fontWeight: 'bold' }} />
                                    <Tooltip
                                        cursor={{ stroke: 'rgba(34,197,94,0.2)', strokeWidth: 2 }}
                                        contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.4)', fontSize: '12px', color: '#fff' }}
                                    />
                                    <ReferenceLine y={100} stroke="#eab308" strokeDasharray="5 5" strokeOpacity={0.3} label={{ position: 'right', value: 'Moderate', fill: '#eab308', fontSize: 10, fontWeight: 'bold' }} />
                                    <Area type="monotone" dataKey="aqi" stroke="#22c55e" strokeWidth={3} fill="url(#chartGrad)" dot={{ r: 4, fill: '#22c55e', strokeWidth: 2, stroke: '#020617' }} activeDot={{ r: 6, strokeWidth: 0 }} animationDuration={2000} />
                                    <Line type="monotone" dataKey="pm25" stroke="#ef4444" strokeWidth={2} dot={false} strokeDasharray="4 4" opacity={0.6} />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>

                {/* Right Side: Environment & Logistics */}
                <div className="xl:col-span-4 space-y-6">

                    <div className="grid grid-cols-2 gap-4">
                        <StatCard label="Air Temp" value={w.temperature?.toFixed(1)} unit="°C" icon={Thermometer} color="#f97316" trend={+2.4} />
                        <StatCard label="Rel. Humidity" value={w.humidity?.toFixed(0)} unit="%" icon={Droplets} color="#0ea5e9" trend={-1.2} />
                        <StatCard label="Avg Wind" value={w.wind_speed?.toFixed(1)} unit="m/s" icon={Wind} color="#10b981" />
                        <StatCard label="Traffic Load" value={t.traffic_density_index?.toFixed(1)} unit="/10" icon={Car}
                            color={t.traffic_density_index > 6 ? '#ef4444' : t.traffic_density_index > 4 ? '#f59e0b' : '#10b981'} trend={+4.1} />
                    </div>

                    <div className="glass-card p-6 bg-gradient-to-br from-green-500/[0.03] to-transparent">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xs font-black text-gray-500 uppercase tracking-widest">Environment Meta</h3>
                            <div className="px-2 py-0.5 rounded-full bg-green-500/10 text-green-400 text-[9px] font-black border border-green-500/20">STATION_ID: 01-DEL-IN</div>
                        </div>

                        <div className="space-y-6">
                            <div className="flex items-start gap-4">
                                <div className="p-2.5 rounded-lg bg-white/5">
                                    <Cloud className="w-5 h-5 text-gray-400" />
                                </div>
                                <div className="flex-1">
                                    <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">Atmospheric State</p>
                                    <p className="text-base font-bold text-white mt-0.5">{w.weather_condition || 'Partly Cloudy'}</p>
                                    <div className="flex gap-4 mt-1.5">
                                        <div className="text-[10px] text-gray-500"><span className="text-gray-400 font-bold">{w.pressure?.toFixed(0)}</span> hPa Press</div>
                                        <div className="text-[10px] text-gray-500"><span className="text-gray-400 font-bold">{w.visibility?.toFixed(1)}</span> km Visib</div>
                                    </div>
                                </div>
                            </div>

                            <div className="w-full h-px bg-white/5" />

                            <div className="flex items-start gap-4">
                                <div className="p-2.5 rounded-lg bg-green-500/10 shadow-[0_0_15px_rgba(34,197,94,0.1)]">
                                    <Zap className="w-5 h-5 text-green-500" />
                                </div>
                                <div>
                                    <p className="text-xs font-bold text-gray-500 uppercase tracking-wide leading-none mb-1.5">Intelligence Status</p>
                                    <div className="flex gap-1.5">
                                        {['TELEMETRY', 'COMPLIANCE', 'FORECAST'].map(tag => (
                                            <span key={tag} className="text-[9px] font-black bg-white/5 px-2 py-0.5 rounded text-gray-400 border border-white/5">{tag}</span>
                                        ))}
                                    </div>
                                    <p className="text-[10px] text-gray-500 mt-2.5 leading-relaxed">
                                        Multiple ingestion pipelines (OpenAQ, OWM, TomTom) are active. Model version <span className="text-green-500 font-bold">2.4.0-edge</span> is currently processing inference.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Quick Insight / Bot Preview Card */}
                    <div className="glass-card p-6 bg-gradient-to-br from-indigo-500/[0.03] to-transparent relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-8 transform translate-x-1/3 -translate-y-1/3 blur-3xl bg-indigo-500/10 rounded-full w-48 h-48" />
                        <div className="relative z-10">
                            <div className="flex items-center gap-2 mb-4">
                                <Bot className="w-4 h-4 text-indigo-400" />
                                <span className="text-[10px] font-black text-indigo-400/70 uppercase tracking-widest">Assistant Insight</span>
                            </div>
                            <p className="text-sm font-bold text-gray-200 leading-snug italic">
                                "The increase in traffic density index (4.1%) at 02:45 pm is likely causing the PM2.5 spike. Suggest higher mitigation if AQI exceeds 180."
                            </p>
                            <button className="mt-4 w-full py-2 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 text-[10px] font-black rounded-lg transition-all border border-indigo-500/20 tracking-widest">
                                ASK GREENPULSE AI
                            </button>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    )
}
