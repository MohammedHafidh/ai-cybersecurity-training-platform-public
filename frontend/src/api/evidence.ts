export const scenarioNames = {
  benign: 'Benign',
  brute_force: 'Brute force',
  sql_injection: 'SQL injection',
  reconnaissance: 'Network reconnaissance',
}

export function evidenceObject(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

export function evidenceList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter(item => typeof item === 'string') : []
}

export function maliciousProbability(value: unknown): string | undefined {
  if (typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1) {
    return new Intl.NumberFormat('en', { style: 'percent', maximumFractionDigits: 2 }).format(value)
  }
}

export function featureName(key: string): string {
  const names: Record<string, string> = {
    suspicious_token_count: 'SQL-like token matches',
    failed_login_count: 'Failed SSH password events',
    unique_destination_port_count: 'Distinct observed destination ports',
    max_request_length: 'Maximum decoded input length',
  }
  return Object.hasOwn(names, key) ? names[key] : key.replaceAll('_', ' ')
}
