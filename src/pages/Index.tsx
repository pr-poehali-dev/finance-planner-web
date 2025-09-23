import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useAuth } from '@/contexts/AuthContext'
import { AuthModal } from '@/components/AuthModal'
import Icon from '@/components/ui/icon'

interface Transaction {
  id: string
  type: 'income' | 'expense'
  amount: number
  category: string
  description: string
  date: string
}

interface Goal {
  id: string
  title: string
  targetAmount: number
  currentAmount: number
  deadline: string
}

function Index() {
  const { user, logout, loading } = useAuth()
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('dashboard')
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [goals, setGoals] = useState<Goal[]>([])

  useEffect(() => {
    if (!loading && !user) {
      setAuthModalOpen(true)
    }
  }, [user, loading])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Icon name="Loader2" size={48} className="mx-auto mb-4 text-primary animate-spin" />
          <h3 className="text-xl font-medium text-gray-500">Загрузка...</h3>
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <>
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <Icon name="Wallet" size={64} className="mx-auto mb-4 text-primary" />
            <h1 className="text-4xl font-bold text-gray-900 mb-2">FinPlan</h1>
            <p className="text-xl text-gray-600 mb-8">Ваш личный финансовый планировщик</p>
            <Button size="lg" onClick={() => setAuthModalOpen(true)}>
              Войти или зарегистрироваться
            </Button>
          </div>
        </div>
        <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />
      </>
    )
  }

  const totalIncome = transactions.filter(t => t.type === 'income').reduce((sum, t) => sum + t.amount, 0)
  const totalExpenses = transactions.filter(t => t.type === 'expense').reduce((sum, t) => sum + t.amount, 0)
  const balance = totalIncome - totalExpenses

  const expensesByCategory = transactions
    .filter(t => t.type === 'expense')
    .reduce((acc, t) => {
      acc[t.category] = (acc[t.category] || 0) + t.amount
      return acc
    }, {} as Record<string, number>)

  const addTransaction = (transaction: Omit<Transaction, 'id'>) => {
    const newTransaction = {
      ...transaction,
      id: Date.now().toString()
    }
    setTransactions([newTransaction, ...transactions])
  }

  const addGoal = (goal: Omit<Goal, 'id'>) => {
    const newGoal = {
      ...goal,
      id: Date.now().toString()
    }
    setGoals([...goals, newGoal])
  }

  const NavigationButton = ({ tab, icon, label }: { tab: string, icon: string, label: string }) => (
    <Button
      variant={activeTab === tab ? "default" : "ghost"}
      className="w-full justify-start gap-3"
      onClick={() => setActiveTab(tab)}
    >
      <Icon name={icon} size={20} />
      {label}
    </Button>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="flex">
        {/* Sidebar */}
        <div className="w-64 bg-white border-r border-gray-200 p-6 hidden lg:block">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">FinPlan</h1>
            <p className="text-sm text-gray-500">
              {user.first_name ? `Привет, ${user.first_name}!` : user.email}
            </p>
          </div>
          
          <nav className="space-y-2">
            <NavigationButton tab="dashboard" icon="LayoutDashboard" label="Дашборд" />
            <NavigationButton tab="transactions" icon="Receipt" label="Транзакции" />
            <NavigationButton tab="statistics" icon="BarChart3" label="Статистика" />
            <NavigationButton tab="goals" icon="Target" label="Цели" />
            <NavigationButton tab="calendar" icon="Calendar" label="Календарь" />
            <NavigationButton tab="settings" icon="Settings" label="Настройки" />
            
            <div className="mt-8 pt-4 border-t border-gray-200">
              <Button variant="ghost" className="w-full justify-start gap-3 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={logout}>
                <Icon name="LogOut" size={20} />
                Выйти
              </Button>
            </div>
          </nav>
        </div>

        {/* Mobile Header */}
        <div className="lg:hidden fixed top-0 left-0 right-0 bg-white border-b border-gray-200 p-4 z-50">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-gray-900">FinPlan</h1>
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Icon name="Menu" size={24} />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-64">
                <SheetHeader>
                  <SheetTitle>Меню</SheetTitle>
                </SheetHeader>
                <nav className="space-y-2 mt-6">
                  <NavigationButton tab="dashboard" icon="LayoutDashboard" label="Дашборд" />
                  <NavigationButton tab="transactions" icon="Receipt" label="Транзакции" />
                  <NavigationButton tab="statistics" icon="BarChart3" label="Статистика" />
                  <NavigationButton tab="goals" icon="Target" label="Цели" />
                  <NavigationButton tab="calendar" icon="Calendar" label="Календарь" />
                  <NavigationButton tab="settings" icon="Settings" label="Настройки" />
                  
                  <div className="mt-8 pt-4 border-t border-gray-200">
                    <Button variant="ghost" className="w-full justify-start gap-3 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={logout}>
                      <Icon name="LogOut" size={20} />
                      Выйти
                    </Button>
                  </div>
                </nav>
              </SheetContent>
            </Sheet>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 lg:ml-0 mt-16 lg:mt-0">
          <div className="p-6">
            {/* Dashboard */}
            {activeTab === 'dashboard' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-3xl font-bold text-gray-900">Дашборд</h2>
                  <Sheet>
                    <SheetTrigger asChild>
                      <Button className="gap-2">
                        <Icon name="Plus" size={16} />
                        Добавить транзакцию
                      </Button>
                    </SheetTrigger>
                    <SheetContent>
                      <SheetHeader>
                        <SheetTitle>Новая транзакция</SheetTitle>
                      </SheetHeader>
                      <TransactionForm onSubmit={addTransaction} />
                    </SheetContent>
                  </Sheet>
                </div>

                {/* Balance Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">Общий баланс</CardTitle>
                      <Icon name="Wallet" className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        <span className={balance >= 0 ? 'text-finance-income' : 'text-finance-expense'}>
                          {balance.toLocaleString('ru-RU')} ₽
                        </span>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">Доходы</CardTitle>
                      <Icon name="TrendingUp" className="h-4 w-4 text-finance-income" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold text-finance-income">
                        +{totalIncome.toLocaleString('ru-RU')} ₽
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">Расходы</CardTitle>
                      <Icon name="TrendingDown" className="h-4 w-4 text-finance-expense" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold text-finance-expense">
                        -{totalExpenses.toLocaleString('ru-RU')} ₽
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Recent Transactions & Goals */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Последние транзакции</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {transactions.slice(0, 5).map((transaction) => (
                          <div key={transaction.id} className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                transaction.type === 'income' ? 'bg-green-100' : 'bg-red-100'
                              }`}>
                                <Icon 
                                  name={transaction.type === 'income' ? 'ArrowUpRight' : 'ArrowDownRight'} 
                                  size={16}
                                  className={transaction.type === 'income' ? 'text-finance-income' : 'text-finance-expense'}
                                />
                              </div>
                              <div>
                                <p className="font-medium">{transaction.description}</p>
                                <p className="text-sm text-gray-500">{transaction.category}</p>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className={`font-medium ${
                                transaction.type === 'income' ? 'text-finance-income' : 'text-finance-expense'
                              }`}>
                                {transaction.type === 'income' ? '+' : '-'}
                                {transaction.amount.toLocaleString('ru-RU')} ₽
                              </p>
                              <p className="text-sm text-gray-500">{transaction.date}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Финансовые цели</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-6">
                        {goals.map((goal) => {
                          const progress = (goal.currentAmount / goal.targetAmount) * 100
                          return (
                            <div key={goal.id} className="space-y-2">
                              <div className="flex items-center justify-between">
                                <h4 className="font-medium">{goal.title}</h4>
                                <Badge variant="outline">{Math.round(progress)}%</Badge>
                              </div>
                              <Progress value={progress} className="h-2" />
                              <div className="flex justify-between text-sm text-gray-500">
                                <span>{goal.currentAmount.toLocaleString('ru-RU')} ₽</span>
                                <span>{goal.targetAmount.toLocaleString('ru-RU')} ₽</span>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}

            {/* Transactions */}
            {activeTab === 'transactions' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-3xl font-bold text-gray-900">Транзакции</h2>
                  <Sheet>
                    <SheetTrigger asChild>
                      <Button className="gap-2">
                        <Icon name="Plus" size={16} />
                        Добавить транзакцию
                      </Button>
                    </SheetTrigger>
                    <SheetContent>
                      <SheetHeader>
                        <SheetTitle>Новая транзакция</SheetTitle>
                      </SheetHeader>
                      <TransactionForm onSubmit={addTransaction} />
                    </SheetContent>
                  </Sheet>
                </div>

                <Card>
                  <CardContent className="p-0">
                    <div className="space-y-0">
                      {transactions.map((transaction, index) => (
                        <div key={transaction.id}>
                          <div className="flex items-center justify-between p-6">
                            <div className="flex items-center gap-4">
                              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                                transaction.type === 'income' ? 'bg-green-100' : 'bg-red-100'
                              }`}>
                                <Icon 
                                  name={transaction.type === 'income' ? 'ArrowUpRight' : 'ArrowDownRight'} 
                                  size={20}
                                  className={transaction.type === 'income' ? 'text-finance-income' : 'text-finance-expense'}
                                />
                              </div>
                              <div>
                                <h4 className="font-medium">{transaction.description}</h4>
                                <p className="text-sm text-gray-500">{transaction.category}</p>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className={`text-lg font-medium ${
                                transaction.type === 'income' ? 'text-finance-income' : 'text-finance-expense'
                              }`}>
                                {transaction.type === 'income' ? '+' : '-'}
                                {transaction.amount.toLocaleString('ru-RU')} ₽
                              </p>
                              <p className="text-sm text-gray-500">{transaction.date}</p>
                            </div>
                          </div>
                          {index < transactions.length - 1 && <Separator />}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Statistics */}
            {activeTab === 'statistics' && (
              <div className="space-y-6">
                <h2 className="text-3xl font-bold text-gray-900">Статистика</h2>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Расходы по категориям</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {Object.entries(expensesByCategory).map(([category, amount]) => {
                          const percentage = (amount / totalExpenses) * 100
                          return (
                            <div key={category} className="space-y-2">
                              <div className="flex justify-between items-center">
                                <span className="font-medium">{category}</span>
                                <span className="text-sm text-gray-500">
                                  {amount.toLocaleString('ru-RU')} ₽ ({percentage.toFixed(1)}%)
                                </span>
                              </div>
                              <Progress value={percentage} className="h-2" />
                            </div>
                          )
                        })}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Месячная динамика</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <span>Доходы</span>
                          <span className="text-finance-income font-medium">
                            +{totalIncome.toLocaleString('ru-RU')} ₽
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>Расходы</span>
                          <span className="text-finance-expense font-medium">
                            -{totalExpenses.toLocaleString('ru-RU')} ₽
                          </span>
                        </div>
                        <Separator />
                        <div className="flex items-center justify-between font-bold">
                          <span>Итого</span>
                          <span className={balance >= 0 ? 'text-finance-income' : 'text-finance-expense'}>
                            {balance >= 0 ? '+' : ''}{balance.toLocaleString('ru-RU')} ₽
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}

            {/* Goals */}
            {activeTab === 'goals' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-3xl font-bold text-gray-900">Финансовые цели</h2>
                  <Sheet>
                    <SheetTrigger asChild>
                      <Button className="gap-2">
                        <Icon name="Plus" size={16} />
                        Добавить цель
                      </Button>
                    </SheetTrigger>
                    <SheetContent>
                      <SheetHeader>
                        <SheetTitle>Новая финансовая цель</SheetTitle>
                      </SheetHeader>
                      <GoalForm onSubmit={addGoal} />
                    </SheetContent>
                  </Sheet>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {goals.map((goal) => {
                    const progress = (goal.currentAmount / goal.targetAmount) * 100
                    const remaining = goal.targetAmount - goal.currentAmount
                    return (
                      <Card key={goal.id}>
                        <CardHeader>
                          <CardTitle className="flex items-center justify-between">
                            {goal.title}
                            <Badge variant="outline">{Math.round(progress)}%</Badge>
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          <Progress value={progress} className="h-3" />
                          <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span>Накоплено:</span>
                              <span className="font-medium">{goal.currentAmount.toLocaleString('ru-RU')} ₽</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span>Цель:</span>
                              <span className="font-medium">{goal.targetAmount.toLocaleString('ru-RU')} ₽</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span>Осталось:</span>
                              <span className="font-medium text-finance-expense">{remaining.toLocaleString('ru-RU')} ₽</span>
                            </div>
                            <div className="flex justify-between text-sm">
                              <span>Срок:</span>
                              <span className="font-medium">{goal.deadline}</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Other tabs placeholder */}
            {(activeTab === 'calendar' || activeTab === 'settings') && (
              <div className="text-center py-12">
                <Icon name="Construction" size={48} className="mx-auto mb-4 text-gray-400" />
                <h3 className="text-xl font-medium text-gray-500 mb-2">
                  Раздел "{activeTab === 'calendar' ? 'Календарь' : 'Настройки'}" в разработке
                </h3>
                <p className="text-gray-400">Этот функционал будет добавлен в следующих версиях</p>
              </div>
            )}
          </div>
        </div>
      </div>
      
      <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />
    </div>
  )
}

function GoalForm({ onSubmit }: { onSubmit: (goal: Omit<Goal, 'id'>) => void }) {
  const [formData, setFormData] = useState({
    title: '',
    targetAmount: '',
    currentAmount: '',
    deadline: ''
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.title && formData.targetAmount && formData.deadline) {
      onSubmit({
        ...formData,
        targetAmount: parseFloat(formData.targetAmount),
        currentAmount: parseFloat(formData.currentAmount) || 0
      })
      setFormData({
        title: '',
        targetAmount: '',
        currentAmount: '',
        deadline: ''
      })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 mt-6">
      <div className="space-y-2">
        <Label htmlFor="title">Название цели</Label>
        <Input
          id="title"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          placeholder="Например, Новый ноутбук"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="targetAmount">Целевая сумма (₽)</Label>
        <Input
          id="targetAmount"
          type="number"
          value={formData.targetAmount}
          onChange={(e) => setFormData({ ...formData, targetAmount: e.target.value })}
          placeholder="0"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="currentAmount">Текущая сумма (₽)</Label>
        <Input
          id="currentAmount"
          type="number"
          value={formData.currentAmount}
          onChange={(e) => setFormData({ ...formData, currentAmount: e.target.value })}
          placeholder="0"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="deadline">Срок достижения</Label>
        <Input
          id="deadline"
          type="date"
          value={formData.deadline}
          onChange={(e) => setFormData({ ...formData, deadline: e.target.value })}
          required
        />
      </div>

      <Button type="submit" className="w-full">
        Создать цель
      </Button>
    </form>
  )
}

function TransactionForm({ onSubmit }: { onSubmit: (transaction: Omit<Transaction, 'id'>) => void }) {
  const [formData, setFormData] = useState({
    type: 'expense' as 'income' | 'expense',
    amount: '',
    category: '',
    description: '',
    date: new Date().toISOString().split('T')[0]
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.amount && formData.category && formData.description) {
      onSubmit({
        ...formData,
        amount: parseFloat(formData.amount)
      })
      setFormData({
        type: 'expense',
        amount: '',
        category: '',
        description: '',
        date: new Date().toISOString().split('T')[0]
      })
    }
  }

  const categories = {
    income: ['Зарплата', 'Фриланс', 'Инвестиции', 'Подарки', 'Другое'],
    expense: ['Продукты', 'Транспорт', 'Жилье', 'Здоровье', 'Развлечения', 'Одежда', 'Образование', 'Другое']
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 mt-6">
      <div className="space-y-2">
        <Label>Тип транзакции</Label>
        <Select value={formData.type} onValueChange={(value: 'income' | 'expense') => setFormData({ ...formData, type: value })}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="income">Доход</SelectItem>
            <SelectItem value="expense">Расход</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="amount">Сумма (₽)</Label>
        <Input
          id="amount"
          type="number"
          value={formData.amount}
          onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
          placeholder="0"
          required
        />
      </div>

      <div className="space-y-2">
        <Label>Категория</Label>
        <Select value={formData.category} onValueChange={(value) => setFormData({ ...formData, category: value })}>
          <SelectTrigger>
            <SelectValue placeholder="Выберите категорию" />
          </SelectTrigger>
          <SelectContent>
            {categories[formData.type].map((category) => (
              <SelectItem key={category} value={category}>
                {category}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Описание</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="Введите описание транзакции"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="date">Дата</Label>
        <Input
          id="date"
          type="date"
          value={formData.date}
          onChange={(e) => setFormData({ ...formData, date: e.target.value })}
          required
        />
      </div>

      <Button type="submit" className="w-full">
        Добавить транзакцию
      </Button>
    </form>
  )
}

export default Index