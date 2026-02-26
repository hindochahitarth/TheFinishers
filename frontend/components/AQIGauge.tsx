'use client'

interface AQIGaugeProps {
    aqi: number
    category: string
    size?: 'sm' | 'md' | 'lg'
}

const CATEGORY_COLORS: Record<string, { stroke: string; glow: string; text: string }> = {
    Good: { stroke: '#22c55e', glow: 'rgba(34,197,94,0.4)', text: 'text-green-400' },
    Satisfactory: { stroke: '#84cc16', glow: 'rgba(132,204,22,0.4)', text: 'text-lime-400' },
    Moderate: { stroke: '#eab308', glow: 'rgba(234,179,8,0.4)', text: 'text-yellow-400' },
    Poor: { stroke: '#f97316', glow: 'rgba(249,115,22,0.4)', text: 'text-orange-400' },
    'Very Poor': { stroke: '#ef4444', glow: 'rgba(239,68,68,0.4)', text: 'text-red-400' },
    Severe: { stroke: '#dc2626', glow: 'rgba(220,38,38,0.5)', text: 'text-red-600' },
    Unknown: { stroke: '#6b7280', glow: 'rgba(107,114,128,0.3)', text: 'text-gray-400' },
}

export default function AQIGauge({ aqi, category, size = 'lg' }: AQIGaugeProps) {
    const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS['Unknown']
    const clampedAqi = Math.min(Math.max(aqi || 0, 0), 500)

    // SVG arc parameters
    const radius = size === 'lg' ? 80 : size === 'md' ? 60 : 45
    const cx = size === 'lg' ? 100 : size === 'md' ? 80 : 60
    const strokeWidth = size === 'lg' ? 14 : size === 'md' ? 11 : 9
    const svgSize = cx * 2

    // Arc from 150° to 390° (240° sweep)
    const startAngle = 150
    const endAngle = 390
    const sweep = endAngle - startAngle

    const toRad = (d: number) => (d * Math.PI) / 180
    const arcPath = (start: number, end: number) => {
        const x1 = cx + radius * Math.cos(toRad(start))
        const y1 = cx + radius * Math.sin(toRad(start))
        const x2 = cx + radius * Math.cos(toRad(end))
        const y2 = cx + radius * Math.sin(toRad(end))
        const large = end - start > 180 ? 1 : 0
        return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`
    }

    const fillAngle = startAngle + (clampedAqi / 500) * sweep
    const fontSize = size === 'lg' ? '2rem' : size === 'md' ? '1.5rem' : '1.1rem'
    const labelSize = size === 'lg' ? '0.7rem' : '0.6rem'

    return (
        <div className="flex flex-col items-center">
            <svg
                width={svgSize}
                height={svgSize * 0.72}
                viewBox={`0 0 ${svgSize} ${svgSize * 0.72}`}
                style={{ overflow: 'visible' }}>
                <defs>
                    <filter id="gauge-glow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                        <feMerge>
                            <feMergeNode in="coloredBlur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                </defs>
                {/* Background track */}
                <path d={arcPath(startAngle, endAngle)}
                    fill="none" stroke="rgba(34,197,94,0.08)" strokeWidth={strokeWidth}
                    strokeLinecap="round" />
                {/* Value arc */}
                {clampedAqi > 0 && (
                    <path d={arcPath(startAngle, fillAngle)}
                        fill="none" stroke={colors.stroke} strokeWidth={strokeWidth}
                        strokeLinecap="round" filter="url(#gauge-glow)"
                        style={{
                            transition: 'stroke-dasharray 1s ease',
                            filter: `drop-shadow(0 0 8px ${colors.glow})`,
                        }} />
                )}
                {/* Center AQI value */}
                <text x={cx} y={cx - 4} textAnchor="middle" dominantBaseline="middle"
                    fill={colors.stroke} fontSize={fontSize} fontWeight="700"
                    fontFamily="Inter, system-ui"
                    style={{ filter: `drop-shadow(0 0 10px ${colors.glow})` }}>
                    {Math.round(aqi || 0)}
                </text>
                <text x={cx} y={cx + (size === 'lg' ? 22 : 18)} textAnchor="middle"
                    fill="rgba(156,163,175,0.8)" fontSize={labelSize} fontWeight="500">
                    AQI
                </text>
            </svg>
            <div className={`text-center -mt-2 ${colors.text}`}>
                <span className="font-semibold text-sm tracking-wide">{category || 'Unknown'}</span>
            </div>
        </div>
    )
}
