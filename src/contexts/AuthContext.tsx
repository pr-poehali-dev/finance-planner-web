import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface User {
  id: number
  email: string
  first_name: string
  last_name: string
}

interface AuthContextType {
  user: User | null
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  register: (email: string, password: string, firstName: string, lastName: string) => Promise<{ success: boolean; error?: string }>
  logout: () => Promise<void>
  resetPassword: (email: string) => Promise<{ success: boolean; error?: string }>
  confirmReset: (token: string, password: string) => Promise<{ success: boolean; error?: string }>
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

const AUTH_API_URL = 'https://functions.poehali.dev/37469ea0-8998-49ee-ba66-8f43d0682a4a'

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Проверяем авторизацию через cookie
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const response = await fetch(AUTH_API_URL, {
        method: 'GET',
        credentials: 'include', // Включаем cookies
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        if (data.valid && data.user) {
          setUser(data.user)
        } else {
          setUser(null)
        }
      } else {
        setUser(null)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(AUTH_API_URL, {
        method: 'POST',
        credentials: 'include', // Включаем cookies
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'login',
          email,
          password
        })
      })

      const data = await response.json()

      if (response.ok && data.user) {
        setUser(data.user)
        return { success: true }
      } else {
        return { success: false, error: data.error || 'Ошибка авторизации' }
      }
    } catch (error) {
      return { success: false, error: 'Ошибка соединения с сервером' }
    }
  }

  const register = async (
    email: string, 
    password: string, 
    firstName: string, 
    lastName: string
  ): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(AUTH_API_URL, {
        method: 'POST',
        credentials: 'include', // Включаем cookies
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'register',
          email,
          password,
          first_name: firstName,
          last_name: lastName || ''
        })
      })

      const data = await response.json()

      if (response.ok && data.user) {
        setUser(data.user)
        return { success: true }
      } else {
        return { success: false, error: data.error || 'Ошибка регистрации' }
      }
    } catch (error) {
      return { success: false, error: 'Ошибка соединения с сервером' }
    }
  }

  const logout = async (): Promise<void> => {
    try {
      // Отправляем запрос на очистку cookie
      await fetch(AUTH_API_URL, {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })
    } catch (error) {
      console.error('Logout request failed:', error)
    }
    
    setUser(null)
  }

  const resetPassword = async (email: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(AUTH_API_URL, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'reset_password',
          email
        })
      })

      const data = await response.json()

      if (response.ok) {
        return { success: true }
      } else {
        return { success: false, error: data.error || 'Ошибка отправки письма' }
      }
    } catch (error) {
      return { success: false, error: 'Ошибка соединения с сервером' }
    }
  }

  const confirmReset = async (token: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await fetch(AUTH_API_URL, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'confirm_reset',
          token,
          password
        })
      })

      const data = await response.json()

      if (response.ok) {
        return { success: true }
      } else {
        return { success: false, error: data.error || 'Ошибка сброса пароля' }
      }
    } catch (error) {
      return { success: false, error: 'Ошибка соединения с сервером' }
    }
  }

  const value: AuthContextType = {
    user,
    login,
    register,
    logout,
    resetPassword,
    confirmReset,
    loading
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}