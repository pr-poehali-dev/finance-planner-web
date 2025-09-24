// API функции для работы с backend
const API_URLS = {
  auth: 'https://functions.poehali.dev/f0418e5f-ef38-47d7-96e8-fcc12cc2bf96',
  goals: 'https://functions.poehali.dev/61374f29-3f4a-4325-acc0-5ed4fbcbd77e',
  transactions: 'https://functions.poehali.dev/2fc3f1dd-8b8a-491e-9c11-3abdf16c1cb7',
  calendar: 'https://functions.poehali.dev/325cbca9-ff34-4fef-9d79-e5619ad8e62e'
}

// Общая функция для API запросов
async function apiRequest(url: string, options: RequestInit = {}) {
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    mode: 'cors',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers
    }
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`)
  }

  return response.json()
}

// Goals API
export const goalsAPI = {
  getAll: () => apiRequest(API_URLS.goals),
  create: (goal: any) => apiRequest(API_URLS.goals, {
    method: 'POST',
    body: JSON.stringify(goal)
  }),
  update: (goal: any) => apiRequest(API_URLS.goals, {
    method: 'PUT',
    body: JSON.stringify(goal)
  }),
  delete: (id: number) => apiRequest(`${API_URLS.goals}?id=${id}`, {
    method: 'DELETE'
  })
}

// Transactions API
export const transactionsAPI = {
  getAll: (params?: any) => {
    const query = params ? `?${new URLSearchParams(params)}` : ''
    return apiRequest(`${API_URLS.transactions}${query}`)
  },
  create: (transaction: any) => apiRequest(API_URLS.transactions, {
    method: 'POST',
    body: JSON.stringify({
      action: 'create_transaction',
      ...transaction
    })
  }),
  update: (transaction: any) => apiRequest(API_URLS.transactions, {
    method: 'PUT',
    body: JSON.stringify(transaction)
  }),
  delete: (id: number) => apiRequest(`${API_URLS.transactions}?id=${id}`, {
    method: 'DELETE'
  }),
  getTags: () => apiRequest(`${API_URLS.transactions}?action=tags`),
  createTag: (tag: any) => apiRequest(API_URLS.transactions, {
    method: 'POST',
    body: JSON.stringify({
      action: 'create_tag',
      ...tag
    })
  })
}

// Calendar API
export const calendarAPI = {
  getEvents: (params?: any) => {
    const query = params ? `?${new URLSearchParams(params)}` : ''
    return apiRequest(`${API_URLS.calendar}${query}`)
  },
  createEvent: (event: any) => apiRequest(API_URLS.calendar, {
    method: 'POST',
    body: JSON.stringify(event)
  }),
  updateEvent: (event: any) => apiRequest(API_URLS.calendar, {
    method: 'PUT', 
    body: JSON.stringify(event)
  }),
  deleteEvent: (id: number) => apiRequest(`${API_URLS.calendar}?id=${id}`, {
    method: 'DELETE'
  })
}