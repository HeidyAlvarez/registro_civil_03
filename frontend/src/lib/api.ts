export type ApiError = {
  error?: string
  message?: string
  detail?: string
}

function getCookie(name: string) {
  const value = document.cookie
    .split('; ')
    .find((item) => item.startsWith(`${name}=`))
    ?.split('=')
    .slice(1)
    .join('=')
  return value ? decodeURIComponent(value) : ''
}

export async function api<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const csrf = getCookie('csrftoken')
  if (csrf) headers.set('X-CSRFToken', csrf)

  const response = await fetch(url, {
    credentials: 'same-origin',
    ...options,
    headers,
  })
  const payload = (await response.json().catch(() => ({}))) as T & ApiError
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('session-expired'))
    throw new Error(payload.error || payload.message || payload.detail || 'No fue posible completar la solicitud.')
  }
  return payload
}

export function postJson<T>(url: string, data: unknown) {
  return api<T>(url, { method: 'POST', body: JSON.stringify(data) })
}
