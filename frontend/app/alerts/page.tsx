"use client"

import { useState, useEffect } from 'react'
import { Bell, AlertTriangle, Clock, ShieldAlert, CheckCircle, Loader2, RefreshCw, Trash2, Shield } from 'lucide-react'

interface Alert {
    id: number
    title: string
    message: string
    pollutant: string
    measured_value: number
    threshold_value: number
    threshold_standard: string
    severity: string
    status: string
    is_anomaly_based: boolean
    triggered_at: string
}

const severityConfig: Record<string, { bg: string; text: string; border: string; icon: any }> = {
    'low': { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30', icon: Bell },
    'medium': { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30', icon: AlertTriangle },
    'high': { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/30', icon: ShieldAlert },
    'critical': { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', icon: AlertTriangle },
}

export default function AlertsPage() {
    const [alerts, setAlerts] = useState<Alert[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [activeCount, setActiveCount] = useState(0)

    useEffect(() => {
        fetchAlerts()
    }, [])

    const fetchAlerts = async () => {
        try {
            setLoading(true)
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/alerts/?hours=48`
            )
            if (!response.ok) throw new Error('Failed to fetch alerts')
            const data = await response.json()
            setAlerts(data.alerts)
            setActiveCount(data.active_count)
            setError(null)
        } catch (err) {
            setError('Failed to load alerts')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const acknowledgeAlert = async (id: number) => {
        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/alerts/${id}/acknowledge`,
                { method: 'PATCH' }
            )
            if (response.ok) {
                setAlerts(alerts.map(a => a.id === id ? { ...a, status: 'acknowledged' } : a))
                setActiveCount(prev => Math.max(0, prev - 1))
            }
        } catch (err) {
            console.error('Failed to acknowledge alert:', err)
        }
    }

    const formatTime = (timestamp: string) => {
        return new Date(timestamp).toLocaleString('en-IN', {
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    if (loading && alerts.length === 0) {
        return (
            <div className="flex items-center justify-center h-full">
                <Loader2 className="w-8 h-8 animate-spin text-green-500" />
            </div>
        )
    }

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Bell className="w-6 h-6 text-green-400" />
                        Active Alerts
                    </h1>
                    <p className="text-gray-400 text-sm mt-1">
                        Real-time notifications for boundary exceedances and anomalies
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    <div className="glass-card px-4 py-2 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                        <span className="text-sm font-medium text-gray-200">{activeCount} Active</span>
                    </div>
                    <button
                        onClick={fetchAlerts}
                        className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300 transition-colors"
                    >
                        <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {error ? (
                <div className="glass-card p-12 text-center text-red-400 border-red-500/20">
                    <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>{error}</p>
                    <button onClick={fetchAlerts} className="mt-4 text-sm text-green-400 hover:underline">Try Again</button>
                </div>
            ) : alerts.length === 0 ? (
                <div className="glass-card p-12 text-center text-gray-400 border-gray-800">
                    <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-500/50" />
                    <p className="text-lg text-gray-300">No active alerts found</p>
                    <p className="text-sm">All environmental parameters are within safe limits.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4">
                    {alerts.map((alert) => {
                        const config = severityConfig[alert.severity.toLowerCase()] || severityConfig.low
                        const Icon = config.icon
                        const isAcknowledged = alert.status.toLowerCase() === 'acknowledged'

                        return (
                            <div
                                key={alert.id}
                                className={`glass-card p-5 border-l-4 transition-all ${config.border} ${isAcknowledged ? 'opacity-60' : ''}`}
                                style={{ borderLeftColor: config.text.split('-')[1] }}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex gap-4">
                                        <div className={`p-3 rounded-xl ${config.bg} ${config.text}`}>
                                            <Icon className="w-6 h-6" />
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-3">
                                                <h3 className="text-lg font-semibold text-white">{alert.title}</h3>
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${config.bg} ${config.text}`}>
                                                    {alert.severity}
                                                </span>
                                                {alert.is_anomaly_based && (
                                                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-purple-500/10 text-purple-400 border border-purple-500/20">
                                                        AI Detected
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-gray-400 mt-1">{alert.message}</p>

                                            <div className="flex items-center gap-6 mt-4">
                                                <div className="flex items-center gap-2 text-xs text-gray-500">
                                                    <Clock className="w-3.5 h-3.5" />
                                                    {formatTime(alert.triggered_at)}
                                                </div>
                                                <div className="flex items-center gap-2 text-xs">
                                                    <span className="text-gray-500">Pollutant:</span>
                                                    <span className="text-green-400 font-medium">{alert.pollutant.toUpperCase()}</span>
                                                </div>
                                                <div className="flex items-center gap-2 text-xs">
                                                    <span className="text-gray-500">Value:</span>
                                                    <span className="text-red-400 font-medium">{alert.measured_value.toFixed(1)}</span>
                                                    <span className="text-gray-500">vs Limit {alert.threshold_value} ({alert.threshold_standard})</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {!isAcknowledged && (
                                        <button
                                            onClick={() => acknowledgeAlert(alert.id)}
                                            className="px-4 py-2 bg-white/5 hover:bg-white/10 text-xs font-medium text-gray-300 rounded-lg border border-white/10 transition-colors flex items-center gap-2"
                                        >
                                            <CheckCircle className="w-3.5 h-3.5" />
                                            Acknowledge
                                        </button>
                                    )}
                                    {isAcknowledged && (
                                        <div className="text-xs text-green-500 flex items-center gap-2 font-medium bg-green-500/5 px-3 py-1.5 rounded-lg border border-green-500/20">
                                            <CheckCircle className="w-3.5 h-3.5" />
                                            Acknowledged
                                        </div>
                                    )}
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Footer Info */}
            <div className="glass-card p-6 bg-gradient-to-r from-green-500/5 to-transparent border border-green-500/10">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-green-500/10 rounded-full">
                        <Shield className="w-6 h-6 text-green-400" />
                    </div>
                    <div>
                        <h4 className="text-sm font-semibold text-white">Advanced Alert Engine</h4>
                        <p className="text-xs text-gray-500 mt-0.5">
                            The engine evaluates sensor data every 60 seconds against WHO and CPCB standards. AI-based
                            anomaly detection also triggers alerts for unexpected pattern changes.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
