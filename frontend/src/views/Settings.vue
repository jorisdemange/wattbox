<template>
  <div class="container mx-auto p-6">
    <h1 class="text-3xl font-bold mb-6">Settings</h1>

    <!-- Price per kWh Setting -->
    <Card class="mb-6">
      <CardHeader>
        <CardTitle>Electricity Price</CardTitle>
        <CardDescription>Configure your electricity cost per kilowatt-hour</CardDescription>
      </CardHeader>
      <CardContent>
        <div class="space-y-4 max-w-md">
          <div class="space-y-2">
            <Label for="price-kwh">Price per kWh (€)</Label>
            <Input
              id="price-kwh"
              v-model="pricePerKwh"
              type="number"
              step="0.001"
              min="0"
              placeholder="0.42"
              @blur="savePrice"
            />
            <p class="text-sm text-muted-foreground">
              The price you pay for each kilowatt-hour of electricity. This is used to calculate cost estimates.
            </p>
          </div>

          <Button @click="savePrice" :disabled="isSaving">
            <span v-if="isSaving">Saving...</span>
            <span v-else>Save Price</span>
          </Button>

          <Alert v-if="saveMessage" class="mt-4">
            <AlertDescription>{{ saveMessage }}</AlertDescription>
          </Alert>
        </div>
      </CardContent>
    </Card>

    <!-- Devices Section -->
    <h2 class="text-2xl font-bold mb-4">Devices</h2>

    <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <Card v-for="device in devices" :key="device.id">
        <CardHeader>
          <CardTitle class="flex items-center justify-between">
            <span>{{ device.name || device.id }}</span>
            <Badge :variant="getStatusVariant(device.status)">
              {{ getStatusLabel(device.status) }}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div v-if="isLoadingDevices" class="space-y-3">
            <Skeleton class="h-4 w-full" />
            <Skeleton class="h-4 w-full" />
            <Skeleton class="h-4 w-full" />
          </div>
          <div v-else class="space-y-2">
            <div class="flex justify-between text-sm">
              <span class="text-muted-foreground">Device ID</span>
              <span class="font-mono">{{ device.id }}</span>
            </div>

            <div class="flex justify-between text-sm">
              <span class="text-muted-foreground">Last Ping</span>
              <span>{{ device.last_ping ? formatDateTime(device.last_ping) : 'Never' }}</span>
            </div>

            <div v-if="device.battery_percent !== null" class="flex justify-between text-sm">
              <span class="text-muted-foreground">Battery</span>
              <Badge :variant="getBatteryVariant(device.battery_percent)" class="font-mono">
                {{ device.battery_percent }}%
              </Badge>
            </div>

            <div class="flex justify-between text-sm">
              <span class="text-muted-foreground">Created</span>
              <span>{{ formatDate(device.created_at) }}</span>
            </div>
          </div>

          <Separator class="my-4" />

          <Button
            variant="outline"
            size="sm"
            class="w-full"
            @click="viewDeviceHealth(device.id)"
          >
            View Health Report
          </Button>
        </CardContent>
      </Card>

      <!-- Add Device Card -->
      <Card class="border-dashed">
        <CardContent class="flex items-center justify-center h-full min-h-[200px]">
          <Button variant="ghost" @click="showAddDevice = true">
            <span class="text-2xl mr-2">+</span>
            Add Device
          </Button>
        </CardContent>
      </Card>
    </div>

    <!-- Device Health Modal -->
    <div v-if="selectedDeviceHealth" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" @click.self="selectedDeviceHealth = null">
      <Card class="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Device Health Report</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            class="absolute right-4 top-4"
            @click="selectedDeviceHealth = null"
          >
            ✕
          </Button>
        </CardHeader>
        <CardContent>
          <div class="space-y-4">
            <div class="text-center">
              <div class="flex items-center justify-center gap-2">
                <p class="text-4xl font-bold">{{ selectedDeviceHealth.health_score }}%</p>
                <Badge :variant="getHealthScoreVariant(selectedDeviceHealth.health_score)">
                  {{ getHealthScoreLabel(selectedDeviceHealth.health_score) }}
                </Badge>
              </div>
              <p class="text-sm text-gray-500">Health Score</p>
            </div>

            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p class="font-medium">Status</p>
                <Badge :variant="getStatusVariant(selectedDeviceHealth.status)">
                  {{ getStatusLabel(selectedDeviceHealth.status) }}
                </Badge>
              </div>
              <div>
                <p class="font-medium">Uptime (7d)</p>
                <p>{{ selectedDeviceHealth.uptime_percentage_7d }}%</p>
              </div>
              <div>
                <p class="font-medium">Readings (7d)</p>
                <p>{{ selectedDeviceHealth.readings_last_7d }}</p>
              </div>
              <div v-if="selectedDeviceHealth.battery_percent !== null">
                <p class="font-medium">Battery Level</p>
                <Badge :variant="getBatteryVariant(selectedDeviceHealth.battery_percent)">
                  {{ selectedDeviceHealth.battery_percent }}%
                </Badge>
              </div>
            </div>

            <div v-if="selectedDeviceHealth.last_reading" class="pt-4 border-t">
              <p class="font-medium mb-2">Last Reading</p>
              <div class="text-sm space-y-1">
                <p>{{ selectedDeviceHealth.last_reading.kwh }} kWh</p>
                <p class="text-gray-500">{{ formatDateTime(selectedDeviceHealth.last_reading.timestamp) }}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Add Device Modal -->
    <div v-if="showAddDevice" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" @click.self="showAddDevice = false">
      <Card class="w-full max-w-md">
        <CardHeader>
          <CardTitle>Add New Device</CardTitle>
        </CardHeader>
        <CardContent>
          <form @submit.prevent="addDevice" class="space-y-4">
            <div class="space-y-2">
              <Label for="device-id">Device ID</Label>
              <Input
                id="device-id"
                v-model="newDevice.id"
                type="text"
                required
                placeholder="esp1"
              />
              <p class="text-sm text-muted-foreground">
                Unique identifier for the device
              </p>
            </div>

            <div class="space-y-2">
              <Label for="device-name">Device Name (optional)</Label>
              <Input
                id="device-name"
                v-model="newDevice.name"
                type="text"
                placeholder="Living Room Meter"
              />
              <p class="text-sm text-muted-foreground">
                A friendly name for the device
              </p>
            </div>

            <div class="flex gap-2">
              <Button type="submit" :disabled="!newDevice.id || isAddingDevice">
                <span v-if="isAddingDevice">Adding...</span>
                <span v-else>Add Device</span>
              </Button>
              <Button type="button" variant="outline" @click="showAddDevice = false">Cancel</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { format } from 'date-fns'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { api } from '@/lib/api'

interface Device {
  id: string
  name?: string
  is_active: boolean
  last_ping?: string
  battery_percent?: number
  created_at: string
  updated_at?: string
  status: string
}

interface DeviceHealth {
  device_id: string
  status: string
  health_score: number
  battery_percent?: number
  last_ping?: string
  last_reading?: {
    timestamp: string
    kwh: number
  }
  uptime_percentage_7d: number
  readings_last_7d: number
}

const pricePerKwh = ref<string>('0.42')
const isSaving = ref(false)
const saveMessage = ref<string>('')
const devices = ref<Device[]>([])
const selectedDeviceHealth = ref<DeviceHealth | null>(null)
const showAddDevice = ref(false)
const isLoadingDevices = ref(false)
const isAddingDevice = ref(false)
const newDevice = ref({
  id: '',
  name: ''
})

const formatDate = (dateString: string) => {
  return format(new Date(dateString), 'MMM dd, yyyy')
}

const formatDateTime = (dateString: string) => {
  return format(new Date(dateString), 'MMM dd, yyyy HH:mm')
}

const getStatusVariant = (status: string) => {
  const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
    online: 'default',
    offline: 'destructive',
    low_battery: 'secondary',
    critical_battery: 'destructive',
    delayed: 'secondary',
    healthy: 'default',
    never_connected: 'outline'
  }
  return variants[status] || 'outline'
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    online: 'Online',
    offline: 'Offline',
    low_battery: 'Low Battery',
    critical_battery: 'Critical Battery',
    delayed: 'Delayed',
    healthy: 'Healthy',
    never_connected: 'Never Connected'
  }
  return labels[status] || status
}

const getBatteryVariant = (battery: number) => {
  if (battery < 10) return 'destructive'
  if (battery < 20) return 'destructive'
  if (battery < 50) return 'secondary'
  return 'default'
}

const getHealthScoreVariant = (score: number) => {
  if (score < 25) return 'destructive'
  if (score < 50) return 'destructive'
  if (score < 75) return 'secondary'
  return 'default'
}

const getHealthScoreLabel = (score: number) => {
  if (score < 25) return 'Critical'
  if (score < 50) return 'Poor'
  if (score < 75) return 'Fair'
  return 'Good'
}

const savePrice = async () => {
  try {
    isSaving.value = true
    saveMessage.value = ''

    // Save to localStorage for now
    localStorage.setItem('price_per_kwh', pricePerKwh.value)

    saveMessage.value = 'Price saved successfully!'
    setTimeout(() => {
      saveMessage.value = ''
    }, 3000)
  } catch (error) {
    console.error('Error saving price:', error)
    saveMessage.value = 'Failed to save price'
  } finally {
    isSaving.value = false
  }
}

const fetchDevices = async () => {
  try {
    isLoadingDevices.value = true
    const response = await api.get('/devices')
    devices.value = response.data.devices
  } catch (error) {
    console.error('Error fetching devices:', error)
  } finally {
    isLoadingDevices.value = false
  }
}

const viewDeviceHealth = async (deviceId: string) => {
  try {
    const response = await api.get(`/devices/${deviceId}/health`)
    selectedDeviceHealth.value = response.data
  } catch (error) {
    console.error('Error fetching device health:', error)
  }
}

const addDevice = async () => {
  try {
    isAddingDevice.value = true
    await api.post('/devices', {
      id: newDevice.value.id,
      name: newDevice.value.name || null
    })

    // Reset form
    newDevice.value = { id: '', name: '' }
    showAddDevice.value = false

    // Refresh devices list
    fetchDevices()
  } catch (error: any) {
    alert(error.response?.data?.detail || 'Failed to add device')
  } finally {
    isAddingDevice.value = false
  }
}

onMounted(() => {
  // Load price from localStorage
  const savedPrice = localStorage.getItem('price_per_kwh')
  if (savedPrice) {
    pricePerKwh.value = savedPrice
  }

  // Fetch devices
  fetchDevices()
})
</script>
