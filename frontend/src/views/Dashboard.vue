<template>
  <div class="container mx-auto p-6">
    <h1 class="text-3xl font-bold mb-6">Electricity Dashboard</h1>
    
    <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      <!-- Current Reading Card -->
      <Card>
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">Current Reading</CardTitle>
          <Badge v-if="latestReading" variant="outline">Live</Badge>
        </CardHeader>
        <CardContent>
          <div v-if="isLoading" class="space-y-2">
            <Skeleton class="h-8 w-24" />
            <Skeleton class="h-4 w-32" />
          </div>
          <div v-else>
            <div class="text-2xl font-bold">{{ formatNumber(latestReading?.reading_kwh || 0) }} kWh</div>
            <p class="text-xs text-muted-foreground">
              {{ latestReading ? formatDate(latestReading.timestamp) : 'No data' }}
            </p>
          </div>
        </CardContent>
      </Card>

      <!-- Daily Usage Card -->
      <Card>
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">Daily Average</CardTitle>
        </CardHeader>
        <CardContent>
          <div v-if="isLoading" class="space-y-2">
            <Skeleton class="h-8 w-24" />
            <Skeleton class="h-4 w-32" />
          </div>
          <div v-else>
            <div class="text-2xl font-bold">{{ formatNumber(dailyStats?.daily_average_kwh || 0) }} kWh</div>
            <p class="text-xs text-muted-foreground">
              € {{ formatNumber(dailyStats?.daily_average_cost || 0) }} per day
            </p>
          </div>
        </CardContent>
      </Card>

      <!-- Monthly Estimate Card -->
      <Card>
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">Monthly Estimate</CardTitle>
        </CardHeader>
        <CardContent>
          <div v-if="isLoading" class="space-y-2">
            <Skeleton class="h-8 w-24" />
            <Skeleton class="h-4 w-32" />
          </div>
          <div v-else>
            <div class="text-2xl font-bold">€ {{ formatNumber(monthlyEstimate?.estimated_monthly_cost || 0) }}</div>
            <p class="text-xs text-muted-foreground">
              {{ formatNumber(monthlyEstimate?.estimated_monthly_kwh || 0) }} kWh
            </p>
          </div>
        </CardContent>
      </Card>

      <!-- Device Status Card -->
      <Card>
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">Device Status</CardTitle>
          <Badge :variant="activeDevices > 0 ? 'default' : 'destructive'">
            {{ activeDevices > 0 ? 'Active' : 'Inactive' }}
          </Badge>
        </CardHeader>
        <CardContent>
          <div v-if="isLoading" class="space-y-2">
            <Skeleton class="h-8 w-20" />
            <Skeleton class="h-4 w-24" />
          </div>
          <div v-else>
            <div class="text-2xl font-bold">{{ activeDevices }} / {{ totalDevices }}</div>
            <p class="text-xs text-muted-foreground">Active devices</p>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Usage Chart -->
    <Card class="mt-6">
      <CardHeader>
        <CardTitle>Usage Over Time</CardTitle>
        <CardDescription>Electricity consumption for the last 7 days</CardDescription>
      </CardHeader>
      <CardContent>
        <div v-if="isLoading" class="h-[300px] flex items-center justify-center">
          <div class="space-y-2 w-full">
            <Skeleton class="h-4 w-full" />
            <Skeleton class="h-4 w-full" />
            <Skeleton class="h-[250px] w-full" />
          </div>
        </div>
        <div v-else class="h-[300px]">
          <Line v-if="chartData" :data="chartData" :options="chartOptions" />
          <div v-else class="h-full flex items-center justify-center text-muted-foreground">
            No data available
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { format } from 'date-fns'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface Reading {
  id: number
  timestamp: string
  reading_kwh: number
  cost: number
}

interface DailyStats {
  daily_average_kwh: number
  daily_average_cost: number
  total_kwh: number
  total_cost: number
}

interface MonthlyEstimate {
  estimated_monthly_kwh: number
  estimated_monthly_cost: number
}

interface Device {
  id: string
  status: string
}

const latestReading = ref<Reading | null>(null)
const dailyStats = ref<DailyStats | null>(null)
const monthlyEstimate = ref<MonthlyEstimate | null>(null)
const devices = ref<Device[]>([])
const readings = ref<Reading[]>([])
const isLoading = ref(true)

const activeDevices = computed(() => devices.value.filter(d => d.status === 'online').length)
const totalDevices = computed(() => devices.value.length)

const chartData = computed(() => {
  if (!readings.value.length) return null
  
  return {
    labels: readings.value.map(r => format(new Date(r.timestamp), 'MMM dd')),
    datasets: [
      {
        label: 'kWh',
        data: readings.value.map(r => r.reading_kwh),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.1
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      mode: 'index' as const,
      intersect: false
    }
  },
  scales: {
    y: {
      beginAtZero: false
    }
  }
}

const formatNumber = (num: number) => {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(num)
}

const formatDate = (dateString: string) => {
  return format(new Date(dateString), 'MMM dd, HH:mm')
}

const fetchData = async () => {
  try {
    isLoading.value = true
    
    // Fetch latest reading
    try {
      const latestResponse = await api.get('/readings/last')
      latestReading.value = latestResponse.data
    } catch (error) {
      console.log('No latest reading found')
    }

    // Fetch daily stats
    try {
      const dailyResponse = await api.get('/readings/daily')
      dailyStats.value = dailyResponse.data
    } catch (error) {
      console.log('No daily stats found')
    }

    // Fetch monthly estimate
    try {
      const monthlyResponse = await api.get('/readings/monthly-estimate')
      monthlyEstimate.value = monthlyResponse.data
    } catch (error) {
      console.log('No monthly estimate found')
    }

    // Fetch devices
    try {
      const devicesResponse = await api.get('/devices')
      devices.value = devicesResponse.data.devices
    } catch (error) {
      console.log('No devices found')
    }

    // Fetch readings for chart
    try {
      const readingsResponse = await api.get('/readings', {
        params: { limit: 100 }
      })
      readings.value = readingsResponse.data.readings.reverse()
    } catch (error) {
      console.log('No readings found')
    }
  } catch (error) {
    console.error('Error fetching dashboard data:', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  console.log('Dashboard component mounted')
  fetchData()
  // Refresh data every 5 minutes
  const interval = setInterval(fetchData, 5 * 60 * 1000)
  
  return () => clearInterval(interval)
})
</script>