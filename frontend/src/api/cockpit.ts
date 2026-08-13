import api from './index'

export interface CockpitKPI {
  id: number
  name: string
  icon: string
  value: string
  unit: string
  trend_text: string
  trend_class: string
  desc: string
  progress: number
  progress_color: string
}

export interface CockpitTrend {
  date_label: string
  session_count: number
  ai_resolve_rate: number
}

export interface CockpitQuestion {
  rank: number
  question: string
  count: number
  progress: number
  color: string
}

export interface CockpitAttribution {
  name: string
  event_type: string
  event_amount: string
  attrib_window: string
  confidence: string
  increment_value: string
  group: string
}

export interface CockpitCsatRow {
  label: string
  value: number
}

export interface CockpitHourly {
  hour: string
  count: number
  percent: number
}

export interface CockpitValueComparison {
  ai_total: number
  human_total: number
  ai_conv: number
  ai_retain: number
  human_conv: number
  human_retain: number
}

export interface CockpitConversionValue {
  total: number
  session_count: number
  avg_per_session: number
  top_sessions: {
    session_id: string
    name: string
    amount: number
    gmvs: number
  }[]
}

export interface CockpitSummary {
  kpis: CockpitKPI[]
  trends: CockpitTrend[]
  top_questions: CockpitQuestion[]
  attributions: CockpitAttribution[]
  csat: CockpitCsatRow[]
  hourly: CockpitHourly[]
  value_comparison: CockpitValueComparison
  conversion_value: CockpitConversionValue
}

export const cockpitAPI = {
  getSummary(period: string = '30d') {
    return api.get('/cockpit/summary', { params: { period } }) as Promise<CockpitSummary>
  },
}