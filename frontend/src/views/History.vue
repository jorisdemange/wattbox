<template>
  <div class="container mx-auto p-6">
    <h1 class="text-3xl font-bold mb-6">Reading History</h1>

    <!-- Filters -->
    <Card class="mb-6">
      <CardHeader>
        <CardTitle>Filters</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid gap-4 md:grid-cols-3">
          <FormItem>
            <FormLabel>Device</FormLabel>
            <Select v-model="filters.deviceId">
              <SelectTrigger>
                <SelectValue placeholder="All Devices" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Devices</SelectItem>
                <SelectItem v-for="device in devices" :key="device.id" :value="device.id">
                  {{ device.name || device.id }}
                </SelectItem>
              </SelectContent>
            </Select>
          </FormItem>
          
          <FormItem>
            <FormLabel>Start Date</FormLabel>
            <FormControl>
              <Input
                v-model="filters.startDate"
                type="date"
              />
            </FormControl>
          </FormItem>
          
          <FormItem>
            <FormLabel>End Date</FormLabel>
            <FormControl>
              <Input
                v-model="filters.endDate"
                type="date"
              />
            </FormControl>
          </FormItem>
        </div>
        
        <div class="mt-4 flex gap-2">
          <Button @click="applyFilters">Apply Filters</Button>
          <Button variant="outline" @click="resetFilters">Reset</Button>
        </div>
      </CardContent>
    </Card>

    <!-- Readings Table -->
    <Card>
      <CardHeader>
        <CardTitle>Readings</CardTitle>
        <CardDescription>Total: {{ totalReadings }} readings</CardDescription>
      </CardHeader>
      <CardContent>
        <div v-if="isLoading" class="space-y-3">
          <Skeleton class="h-12 w-full" />
          <Skeleton class="h-12 w-full" />
          <Skeleton class="h-12 w-full" />
          <Skeleton class="h-12 w-full" />
        </div>
        
        <div v-else-if="readings.length === 0" class="text-center py-8 text-gray-500">
          No readings found
        </div>
        
        <div v-else>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Reading</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Device</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead class="text-right">Cost</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="reading in readings"
                :key="reading.id"
                class="cursor-pointer"
                @click="selectReading(reading)"
              >
                <TableCell class="font-medium">{{ reading.reading_kwh }} kWh</TableCell>
                <TableCell>{{ formatDateTime(reading.timestamp) }}</TableCell>
                <TableCell>
                  <Badge variant="outline">{{ reading.source }}</Badge>
                </TableCell>
                <TableCell>{{ reading.device_id || '-' }}</TableCell>
                <TableCell>
                  <Badge v-if="reading.ocr_confidence" :variant="getConfidenceVariant(reading.ocr_confidence)">
                    {{ reading.ocr_confidence.toFixed(1) }}%
                  </Badge>
                  <span v-else>-</span>
                </TableCell>
                <TableCell class="text-right">
                  <div>
                    <p class="font-medium">€{{ reading.cost.toFixed(2) }}</p>
                    <p class="text-xs text-muted-foreground">€{{ reading.price_per_kwh }}/kWh</p>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        
        <!-- Pagination -->
        <div v-if="totalPages > 1" class="mt-6 flex justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            :disabled="currentPage === 1"
            @click="changePage(currentPage - 1)"
          >
            Previous
          </Button>
          
          <span class="flex items-center px-4 text-sm">
            Page {{ currentPage }} of {{ totalPages }}
          </span>
          
          <Button
            variant="outline"
            size="sm"
            :disabled="currentPage === totalPages"
            @click="changePage(currentPage + 1)"
          >
            Next
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- Reading Detail Modal -->
    <div v-if="selectedReading" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" @click.self="selectedReading = null">
      <Card class="w-full max-w-2xl max-h-[90vh] overflow-auto">
        <CardHeader>
          <CardTitle>Reading Details</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            class="absolute right-4 top-4"
            @click="selectedReading = null"
          >
            ✕
          </Button>
        </CardHeader>
        <CardContent>
          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <p class="text-sm font-medium">Reading</p>
                <p class="text-2xl font-bold">{{ selectedReading.reading_kwh }} kWh</p>
              </div>
              <div>
                <p class="text-sm font-medium">Cost</p>
                <p class="text-2xl font-bold">€{{ selectedReading.cost.toFixed(2) }}</p>
              </div>
            </div>
            
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p class="font-medium">Timestamp</p>
                <p>{{ formatDateTime(selectedReading.timestamp) }}</p>
              </div>
              <div>
                <p class="font-medium">Source</p>
                <p>{{ selectedReading.source }}</p>
              </div>
              <div v-if="selectedReading.device_id">
                <p class="font-medium">Device ID</p>
                <p>{{ selectedReading.device_id }}</p>
              </div>
              <div v-if="selectedReading.ocr_confidence">
                <p class="font-medium">OCR Confidence</p>
                <p>{{ selectedReading.ocr_confidence.toFixed(1) }}%</p>
              </div>
              <div>
                <p class="font-medium">Price per kWh</p>
                <p>€{{ selectedReading.price_per_kwh }}</p>
              </div>
              <div v-if="selectedReading.battery_percent">
                <p class="font-medium">Battery Level</p>
                <p>{{ selectedReading.battery_percent }}%</p>
              </div>
            </div>
            
            <div v-if="selectedReading.photo_path" class="space-y-2">
              <p class="text-sm font-medium">Original Photo</p>
              <img
                :src="`${apiBaseUrl}/images/${selectedReading.photo_path}`"
                alt="Meter reading"
                class="max-w-full rounded-lg"
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { format } from 'date-fns'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { FormControl, FormItem, FormLabel } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'

interface Reading {
  id: number
  timestamp: string
  reading_kwh: number
  photo_path: string
  source: string
  device_id?: string
  battery_percent?: number
  ocr_confidence?: number
  price_per_kwh: number
  cost: number
}

interface Device {
  id: string
  name?: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const readings = ref<Reading[]>([])
const devices = ref<Device[]>([])
const selectedReading = ref<Reading | null>(null)
const isLoading = ref(false)
const totalReadings = ref(0)
const currentPage = ref(1)
const pageSize = 20

const filters = ref({
  deviceId: '',
  startDate: '',
  endDate: ''
})

const totalPages = computed(() => Math.ceil(totalReadings.value / pageSize))

const formatDateTime = (dateString: string) => {
  return format(new Date(dateString), 'MMM dd, yyyy HH:mm')
}

const getConfidenceVariant = (confidence: number) => {
  if (confidence >= 90) return 'default'
  if (confidence >= 70) return 'secondary'
  return 'outline'
}

const fetchReadings = async () => {
  isLoading.value = true
  try {
    const params: any = {
      skip: (currentPage.value - 1) * pageSize,
      limit: pageSize
    }
    
    if (filters.value.deviceId) {
      params.device_id = filters.value.deviceId
    }
    if (filters.value.startDate) {
      params.start_date = new Date(filters.value.startDate).toISOString()
    }
    if (filters.value.endDate) {
      params.end_date = new Date(filters.value.endDate).toISOString()
    }
    
    const response = await api.get('/readings', { params })
    readings.value = response.data.readings
    totalReadings.value = response.data.total
  } catch (error) {
    console.error('Error fetching readings:', error)
  } finally {
    isLoading.value = false
  }
}

const fetchDevices = async () => {
  try {
    const response = await api.get('/devices')
    devices.value = response.data.devices
  } catch (error) {
    console.error('Error fetching devices:', error)
  }
}

const applyFilters = () => {
  currentPage.value = 1
  fetchReadings()
}

const resetFilters = () => {
  filters.value = {
    deviceId: '',
    startDate: '',
    endDate: ''
  }
  currentPage.value = 1
  fetchReadings()
}

const changePage = (page: number) => {
  currentPage.value = page
  fetchReadings()
}

const selectReading = (reading: Reading) => {
  selectedReading.value = reading
}

onMounted(() => {
  fetchReadings()
  fetchDevices()
})
</script>