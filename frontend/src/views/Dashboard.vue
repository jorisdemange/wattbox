<template>
  <div class="container mx-auto p-6 pb-24">
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
              {{ formatNumber(monthlyEstimate?.estimated_monthly_kwh || 0) }} kWh for {{ currentMonthName }}
            </p>
            <p class="text-xs text-muted-foreground mt-1">
              Base price: €{{ kwhPrice }}/kWh
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

    <!-- Filters -->
    <Card class="mt-6">
      <CardHeader>
        <CardTitle>Filters</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="space-y-4">
          <!-- Date Range Selector -->
          <div class="space-y-2">
            <Label>Date Range</Label>
            <Popover>
              <PopoverTrigger as-child>
                <Button
                  variant="outline"
                  :class="[
                    'w-full justify-start text-left font-normal',
                    !dateRange && 'text-muted-foreground'
                  ]"
                >
                  <CalendarIcon class="mr-2 h-4 w-4" />
                  <span v-if="dateRange && (dateRange.start || dateRange.end)">
                    <span v-if="dateRange.start">{{ formatDateOnly(`${dateRange.start.year}-${String(dateRange.start.month).padStart(2, '0')}-${String(dateRange.start.day).padStart(2, '0')}`) }}</span>
                    <span v-if="dateRange.start && dateRange.end"> - </span>
                    <span v-if="dateRange.end">{{ formatDateOnly(`${dateRange.end.year}-${String(dateRange.end.month).padStart(2, '0')}-${String(dateRange.end.day).padStart(2, '0')}`) }}</span>
                  </span>
                  <span v-else>Pick a date range</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-auto p-0" align="start">
                <RangeCalendar
                  v-model="dateRange"
                  :initial-focus="true"
                />
              </PopoverContent>
            </Popover>
          </div>

          <!-- Period Selection Buttons -->
          <div class="flex flex-wrap gap-2">
            <Button
              v-for="period in periodOptions"
              :key="period.value"
              :variant="selectedPeriod === period.value ? 'default' : 'outline'"
              size="sm"
              @click="selectPeriod(period.value)"
            >
              {{ period.label }}
            </Button>
            <Button
              variant="outline"
              size="sm"
              @click="selectPeriod('')"
            >
              Reset
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Usage Chart -->
    <Card class="mt-6">
      <CardHeader>
        <CardTitle>Usage Over Time</CardTitle>
        <CardDescription>Electricity consumption for the last {{ selectedPeriodLabel }}</CardDescription>
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

    <!-- Daily Cost & Consumption Chart -->
    <Card class="mt-6">
      <CardHeader>
        <CardTitle>Daily Cost & Consumption</CardTitle>
        <CardDescription>Average cost per day (hover to see kWh/day)</CardDescription>
      </CardHeader>
      <CardContent>
        <div v-if="isLoading" class="h-[300px] flex items-center justify-center">
          <div class="space-y-2 w-full">
            <Skeleton class="h-4 w-full" />
            <Skeleton class="h-[250px] w-full" />
          </div>
        </div>
        <div v-else class="h-[300px]">
          <Bar v-if="costChartData" :data="costChartData" :options="costChartOptions" />
          <div v-else class="h-full flex items-center justify-center text-muted-foreground">
            No data available
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Readings Table -->
    <Card class="mt-6">
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

        <div v-else-if="filteredReadings.length === 0" class="text-center py-8 text-gray-500">
          No readings found
        </div>

        <div v-else>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Reading</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead>Notes</TableHead>
                <TableHead class="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="reading in filteredReadings"
                :key="reading.id"
                class="hover:bg-muted/50"
              >
                <TableCell class="font-medium cursor-pointer" @click="selectReading(reading)">{{ reading.reading_kwh }} kWh</TableCell>
                <TableCell class="cursor-pointer" @click="selectReading(reading)">
                  <div>
                    <p>{{ formatDateTime(reading.timestamp) }}</p>
                    <p class="text-xs text-muted-foreground">€{{ reading.price_per_kwh }}/kWh</p>
                  </div>
                </TableCell>
                <TableCell class="cursor-pointer" @click="selectReading(reading)">
                  <Badge variant="outline">{{ reading.source }}</Badge>
                </TableCell>
                <TableCell class="cursor-pointer" @click="selectReading(reading)">
                  <Badge v-if="reading.ocr_confidence" :variant="getConfidenceVariant(reading.ocr_confidence)">
                    {{ reading.ocr_confidence.toFixed(1) }}%
                  </Badge>
                  <span v-else>-</span>
                </TableCell>
                <TableCell class="max-w-xs cursor-pointer" @click="selectReading(reading)">
                  <p v-if="reading.notes" class="text-sm text-muted-foreground truncate">{{ reading.notes }}</p>
                  <span v-else class="text-xs text-muted-foreground italic">No notes</span>
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="sm"
                    class="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                    @click.stop="confirmDeleteReading(reading)"
                  >
                    <Trash2Icon class="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>

    <!-- Delete Confirmation Modal -->
    <div v-if="readingToDelete" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" @click.self="readingToDelete = null" @keydown.enter="deleteReading" @keydown.escape="readingToDelete = null" tabindex="-1">
      <Card class="w-full max-w-md">
        <CardHeader>
          <CardTitle>Delete Reading</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            class="absolute right-4 top-4"
            @click="readingToDelete = null"
          >
            ✕
          </Button>
        </CardHeader>
        <CardContent>
          <div class="space-y-4">
            <p class="text-sm">
              Are you sure you want to delete this reading?
            </p>
            <div class="bg-muted p-3 rounded-md text-sm space-y-1">
              <p><strong>Reading:</strong> {{ readingToDelete.reading_kwh }} kWh</p>
              <p><strong>Timestamp:</strong> {{ formatDateTime(readingToDelete.timestamp) }}</p>
              <p v-if="readingToDelete.notes"><strong>Notes:</strong> {{ readingToDelete.notes }}</p>
            </div>
            <p class="text-xs text-muted-foreground">
              This action cannot be undone.
            </p>
            <div class="flex gap-2 justify-end">
              <Button variant="outline" @click="readingToDelete = null">
                Cancel
              </Button>
              <Button variant="destructive" @click="deleteReading">
                Delete
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

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
                <p class="text-2xl font-bold">€{{ (selectedReading.reading_kwh * selectedReading.price_per_kwh).toFixed(2) }}</p>
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

            <div v-if="selectedReading.notes" class="space-y-2 pt-4 border-t">
              <p class="text-sm font-medium">Notes</p>
              <p class="text-sm text-muted-foreground whitespace-pre-wrap">{{ selectedReading.notes }}</p>
            </div>

            <div v-if="selectedReading.photo_path" class="space-y-2 pt-4 border-t">
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

    <!-- Upload Sheet -->
    <Drawer>
      <DrawerTrigger as-child>
        <Button
          class="fixed bottom-6 right-6 h-16 w-16 rounded-full shadow-lg hover:shadow-xl transition-all md:h-auto md:w-auto md:rounded-md md:px-6 md:py-3"
          size="lg"
        >
          <PlusIcon class="h-6 w-6 md:mr-2" />
          <span class="hidden md:inline">Add Reading</span>
        </Button>
      </DrawerTrigger>
      <DrawerContent class="max-h-[96vh]">
        <DrawerHeader>
          <DrawerTitle>Add Reading</DrawerTitle>
          <DrawerDescription>
            Upload a photo of your meter or enter the reading manually
          </DrawerDescription>
        </DrawerHeader>
        <div class="px-4 pb-4 overflow-y-auto space-y-4">
          <!-- File Upload -->
          <div class="space-y-2">
            <Label>Meter Photo (optional)</Label>
            <div
              @drop="handleDrop"
              @dragover.prevent
              @dragenter.prevent
              :class="[
                'border-2 border-dashed rounded-lg text-center transition-all overflow-hidden',
                uploadIsUploading ? 'border-gray-200 bg-gray-50 dark:bg-gray-900 cursor-not-allowed' : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600 cursor-pointer'
              ]"
              @click="!uploadIsUploading && !uploadPreviewUrl && uploadFileInput?.click()"
            >
              <input
                ref="uploadFileInput"
                type="file"
                accept="image/*"
                @change="handleFileSelect"
                :disabled="uploadIsUploading"
                class="hidden"
              />

              <!-- Upload prompt when no file -->
              <div v-if="!uploadPreviewUrl" class="p-6 space-y-2">
                <Upload class="mx-auto h-12 w-12 text-gray-400" />
                <p class="text-sm text-gray-600 dark:text-gray-400">
                  Drag and drop or tap to choose
                </p>
              </div>

              <!-- Image Preview when file selected -->
              <div v-else class="space-y-0">
                <img
                  :src="uploadPreviewUrl"
                  alt="Preview"
                  class="w-full max-h-64 object-contain"
                />
                <div class="p-3 bg-muted/50">
                  <p class="text-sm font-medium">{{ uploadSelectedFile?.name }}</p>
                  <p class="text-xs text-muted-foreground">{{ formatFileSize(uploadSelectedFile?.size || 0) }}</p>
                </div>
              </div>
            </div>

            <!-- Remove button below preview -->
            <Button
              v-if="uploadPreviewUrl"
              type="button"
              variant="outline"
              size="sm"
              class="w-full"
              @click="removeFile"
              :disabled="uploadIsUploading"
            >
              Remove Photo
            </Button>
          </div>

          <!-- Manual Reading Input -->
          <div class="space-y-2">
            <Label for="manual-reading">Manual Reading (kWh)</Label>
            <Input
              id="manual-reading"
              v-model="uploadManualReading"
              type="number"
              step="0.01"
              placeholder="Enter meter reading"
              :disabled="uploadIsUploading"
            />

            <!-- OCR Status -->
            <div v-if="uploadPreviewUrl" class="flex items-center gap-2 text-sm">
              <template v-if="ocrPreview.isLoading">
                <Loader2 class="h-4 w-4 animate-spin text-muted-foreground" />
                <span class="text-muted-foreground">Reading meter...</span>
              </template>
              <template v-else-if="ocrPreview.reading">
                <CheckCircle2 class="h-4 w-4 text-green-600 dark:text-green-500" />
                <span class="text-green-600 dark:text-green-500">
                  OCR: {{ ocrPreview.reading }} kWh ({{ Math.round(ocrPreview.confidence || 0) }}% confidence)
                </span>
              </template>
              <template v-else-if="ocrPreview.error">
                <XCircle class="h-4 w-4 text-red-600 dark:text-red-500" />
                <span class="text-red-600 dark:text-red-500">{{ ocrPreview.error }}</span>
              </template>
            </div>
          </div>

          <!-- Date/Time Selection -->
          <div class="space-y-2">
            <Label>Reading Date & Time</Label>
            <Popover>
              <PopoverTrigger as-child>
                <Button
                  type="button"
                  variant="outline"
                  class="w-full justify-start text-left font-normal"
                  :disabled="uploadIsUploading"
                >
                  <CalendarIcon class="mr-2 h-4 w-4" />
                  <span v-if="uploadReadingDateTime">{{ formatUploadDateTime(uploadReadingDateTime) }}</span>
                  <span v-else>Pick a date and time</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-auto p-0" align="start">
                <Calendar
                  v-model="uploadSelectedDate"
                  mode="single"
                  :initial-focus="true"
                />
                <div class="p-3 border-t">
                  <Label class="text-xs text-muted-foreground">Time</Label>
                  <div class="flex gap-2 mt-2">
                    <Input
                      v-model="uploadSelectedHour"
                      type="number"
                      min="0"
                      max="23"
                      placeholder="HH"
                      class="w-16 text-center"
                    />
                    <span class="flex items-center">:</span>
                    <Input
                      v-model="uploadSelectedMinute"
                      type="number"
                      min="0"
                      max="59"
                      placeholder="MM"
                      class="w-16 text-center"
                    />
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>

          <!-- Device Selection -->
          <div class="space-y-2">
            <Label for="device-select">Device (optional)</Label>
            <Select v-model="uploadSelectedDevice" :disabled="uploadIsUploading">
              <SelectTrigger id="device-select">
                <SelectValue placeholder="Manual upload" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="manual">Manual upload</SelectItem>
                <SelectItem v-for="device in devices" :key="device.id" :value="device.id">
                  {{ device.name || device.id }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <!-- Notes Input -->
          <div class="space-y-2">
            <Label for="notes">Notes (optional)</Label>
            <Textarea
              id="notes"
              v-model="uploadNotes"
              placeholder="Add any observations..."
              :disabled="uploadIsUploading"
              class="min-h-[60px] resize-y"
            />
          </div>

          <!-- Submit Button -->
          <Button
            type="button"
            class="w-full"
            :disabled="(!uploadSelectedFile && !uploadManualReading) || uploadIsUploading"
            @click="handleUploadSubmit"
          >
            <Loader2 v-if="uploadIsUploading" class="mr-2 h-4 w-4 animate-spin" />
            <span v-if="uploadIsUploading">Uploading... {{ uploadProgress }}%</span>
            <span v-else>Submit Reading</span>
          </Button>

          <!-- Result Alert -->
          <Alert v-if="uploadResult" :variant="uploadResult.success ? 'default' : 'destructive'">
            <CheckCircle2 v-if="uploadResult.success" class="h-4 w-4" />
            <XCircle v-else class="h-4 w-4" />
            <AlertTitle>{{ uploadResult.success ? 'Success' : 'Error' }}</AlertTitle>
            <AlertDescription>
              <div v-if="uploadResult.success" class="space-y-1 mt-2 text-sm">
                <p><strong>Reading:</strong> {{ uploadResult.reading_kwh }} kWh</p>
                <p><strong>Cost:</strong> €{{ uploadResult.cost?.toFixed(2) }}</p>
              </div>
              <p v-else class="text-sm mt-2">{{ uploadResult.error }}</p>
            </AlertDescription>
          </Alert>
        </div>
      </DrawerContent>
    </Drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import { format } from 'date-fns'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { RangeCalendar } from '@/components/ui/range-calendar'
import { Drawer, DrawerContent, DrawerDescription, DrawerHeader, DrawerTitle, DrawerTrigger } from '@/components/ui/drawer'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Calendar } from '@/components/ui/calendar'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { CalendarIcon, Trash2Icon, PlusIcon, Loader2, CheckCircle2, XCircle, Upload } from 'lucide-vue-next'
import { api } from '@/lib/api'
import type { DateRange } from 'reka-ui'
import { toast } from '@/components/ui/toast'
import type { DateValue } from '@internationalized/date'
import { CalendarDate } from '@internationalized/date'

ChartJS.register(
  CategoryScale,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
)

interface Reading {
  id: number
  timestamp: string
  reading_kwh: number
  cost: number
  photo_path: string
  source: string
  device_id?: string
  battery_percent?: number
  ocr_confidence?: number
  price_per_kwh: number
  notes?: string
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
  name?: string
  status: string
}

const latestReading = ref<Reading | null>(null)
const dailyStats = ref<DailyStats | null>(null)
const monthlyEstimate = ref<MonthlyEstimate | null>(null)
const devices = ref<Device[]>([])
const readings = ref<Reading[]>([])
const isLoading = ref(true)
const selectedPeriod = ref<string>('')  // Empty = all time
const kwhPrice = ref<number>(0.42)
const selectedReading = ref<Reading | null>(null)
const readingToDelete = ref<Reading | null>(null)
const totalReadings = ref(0)
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Upload form state
interface UploadResult {
  success: boolean
  reading_kwh?: number
  ocr_confidence?: number
  cost?: number
  error?: string
}

const uploadFileInput = ref<HTMLInputElement>()
const uploadSelectedFile = ref<File | null>(null)
const uploadPreviewUrl = ref<string | null>(null)
const uploadSelectedDate = ref<DateValue>()
const uploadSelectedHour = ref<string>('')
const uploadSelectedMinute = ref<string>('')
const uploadManualReading = ref<string>('')
const uploadNotes = ref<string>('')
const uploadSelectedDevice = ref<string>('')
const uploadIsUploading = ref(false)
const uploadProgress = ref(0)
const uploadResult = ref<UploadResult | null>(null)

// OCR preview state
interface OCRPreviewResult {
  isLoading: boolean
  reading?: number
  confidence?: number
  error?: string
}

const ocrPreview = ref<OCRPreviewResult>({ isLoading: false })

// Initialize upload date/time with current
const initializeUploadDateTime = () => {
  const now = new Date()
  uploadSelectedDate.value = new CalendarDate(now.getFullYear(), now.getMonth() + 1, now.getDate())
  uploadSelectedHour.value = now.getHours().toString().padStart(2, '0')
  uploadSelectedMinute.value = now.getMinutes().toString().padStart(2, '0')
}

initializeUploadDateTime()

const uploadReadingDateTime = computed(() => {
  if (uploadSelectedDate.value) {
    const hour = uploadSelectedHour.value ? parseInt(uploadSelectedHour.value) : 0
    const minute = uploadSelectedMinute.value ? parseInt(uploadSelectedMinute.value) : 0
    const date = new Date(uploadSelectedDate.value.year, uploadSelectedDate.value.month - 1, uploadSelectedDate.value.day, hour, minute)
    return date
  }
  return null
})

const formatFileSize = (bytes: number) => {
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  if (bytes === 0) return '0 Bytes'
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

const formatUploadDateTime = (date: Date | null) => {
  if (!date) return ''
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Istanbul'
  }
  return date.toLocaleString('en-US', options)
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    setFile(target.files[0])
  }
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  if (uploadIsUploading.value) return
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    setFile(event.dataTransfer.files[0])
  }
}

const runOCRPreview = async (file: File) => {
  ocrPreview.value = { isLoading: true }

  try {
    const formData = new FormData()
    formData.append('file', file)

    // Use test-with-fallback endpoint for better results with multiple strategies
    const response = await api.post('/ocr/test-with-fallback?primary_strategy=auto&confidence_threshold=50', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    console.log('OCR Response:', response.data)

    if (response.data.success && response.data.reading_kwh != null) {
      ocrPreview.value = {
        isLoading: false,
        reading: response.data.reading_kwh,
        confidence: response.data.confidence
      }
      // Auto-populate manual reading field
      uploadManualReading.value = response.data.reading_kwh.toString()
    } else {
      ocrPreview.value = {
        isLoading: false,
        error: response.data.error_message || 'Could not read meter value'
      }
    }
  } catch (error) {
    console.error('OCR preview failed:', error)
    ocrPreview.value = {
      isLoading: false,
      error: 'OCR failed'
    }
  }
}

const setFile = (file: File) => {
  uploadResult.value = null
  if (!file.type.startsWith('image/')) {
    uploadResult.value = {
      success: false,
      error: 'Please select an image file (JPEG, PNG, GIF, etc.)'
    }
    toast.error('Invalid file type', {
      description: 'Please select an image file',
    })
    return
  }
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    uploadResult.value = {
      success: false,
      error: `File is too large. Maximum size is 10MB`
    }
    toast.error('File too large', {
      description: `Maximum size is 10MB`,
    })
    return
  }

  // Clean up old preview URL
  if (uploadPreviewUrl.value) {
    URL.revokeObjectURL(uploadPreviewUrl.value)
  }

  // Create new preview URL
  uploadPreviewUrl.value = URL.createObjectURL(file)
  uploadSelectedFile.value = file

  // Trigger OCR preview
  runOCRPreview(file)
}

const removeFile = () => {
  // Clean up preview URL
  if (uploadPreviewUrl.value) {
    URL.revokeObjectURL(uploadPreviewUrl.value)
    uploadPreviewUrl.value = null
  }

  uploadSelectedFile.value = null
  uploadResult.value = null
  ocrPreview.value = { isLoading: false }
  uploadManualReading.value = ''
  if (uploadFileInput.value) {
    uploadFileInput.value.value = ''
  }
}

const handleUploadSubmit = async () => {
  if (!uploadSelectedFile.value && !uploadManualReading.value) {
    toast.error('Missing input', {
      description: 'Please provide either a photo or enter a manual reading',
    })
    return
  }

  if (uploadManualReading.value) {
    const reading = parseFloat(uploadManualReading.value)
    if (isNaN(reading) || reading < 0) {
      toast.error('Invalid reading', {
        description: 'Manual reading must be a positive number',
      })
      return
    }
  }

  uploadIsUploading.value = true
  uploadResult.value = null
  uploadProgress.value = 0

  try {
    toast.info('Uploading...', {
      description: 'Processing your meter reading',
    })

    // Always use manual upload endpoint (supports device_id, notes, timestamp, manual reading override)
    const formData = new FormData()

    if (uploadSelectedFile.value) {
      formData.append('file', uploadSelectedFile.value)
    }

    if (uploadReadingDateTime.value) {
      formData.append('timestamp', uploadReadingDateTime.value.toISOString())
    }

    if (uploadNotes.value && uploadNotes.value.trim()) {
      formData.append('notes', uploadNotes.value.trim())
    }

    if (uploadManualReading.value) {
      formData.append('reading_kwh', uploadManualReading.value)
    }

    // Add device_id if selected
    if (uploadSelectedDevice.value && uploadSelectedDevice.value !== 'manual') {
      formData.append('device_id', uploadSelectedDevice.value)
    }

    const response = await api.post('/upload/manual', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          uploadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        }
      }
    })

    if (response.data.reading_kwh && !uploadManualReading.value) {
      uploadManualReading.value = response.data.reading_kwh.toString()
    }

    uploadResult.value = {
      success: true,
      reading_kwh: response.data.reading_kwh,
      ocr_confidence: response.data.ocr_confidence,
      cost: response.data.cost
    }

    toast.success('Upload successful!', {
      description: `Reading: ${response.data.reading_kwh} kWh • Cost: €${response.data.cost ? response.data.cost.toFixed(2) : '0.00'}`,
    })

    // Refresh dashboard and reset form
    await fetchData()
    setTimeout(() => {
      removeFile()
      initializeUploadDateTime()
      uploadManualReading.value = ''
      uploadNotes.value = ''
      uploadSelectedDevice.value = ''
      uploadProgress.value = 0
      uploadResult.value = null
    }, 2000)
  } catch (error) {
    console.error('Upload error:', error)
    let errorMessage = 'Upload failed. Please try again.'
    if (error && typeof error === 'object' && 'response' in error) {
      const axiosError = error as { response?: { data?: { detail?: string } } }
      if (axiosError.response?.data?.detail) {
        errorMessage = axiosError.response.data.detail
      }
    }
    uploadResult.value = {
      success: false,
      error: errorMessage
    }
    toast.error('Upload failed', {
      description: errorMessage,
    })
  } finally {
    uploadIsUploading.value = false
  }
}

// Custom date range
const dateRange = ref<DateRange>()

const periodOptions = [
  { value: '7', label: '7 days' },
  { value: '15', label: '15 days' },
  { value: '30', label: '30 days' },
  { value: '90', label: '3 months' },
  { value: '180', label: '6 months' },
  { value: '365', label: '12 months' }
]

// Watch for date range changes
watch(dateRange, (newVal) => {
  if (newVal && (newVal.start || newVal.end)) {
    selectedPeriod.value = ''  // Clear preset period when using custom dates
    fetchData()
  }
})

const activeDevices = computed(() => devices.value.filter(d => d.status === 'online').length)
const totalDevices = computed(() => devices.value.length)

const currentMonthName = computed(() => {
  return format(new Date(), 'MMMM yyyy')
})

const selectedPeriodLabel = computed(() => {
  if (dateRange.value && (dateRange.value.start || dateRange.value.end)) {
    const parts = []
    if (dateRange.value.start) {
      const startDate = `${dateRange.value.start.year}-${String(dateRange.value.start.month).padStart(2, '0')}-${String(dateRange.value.start.day).padStart(2, '0')}`
      parts.push(`from ${formatDateOnly(startDate)}`)
    }
    if (dateRange.value.end) {
      const endDate = `${dateRange.value.end.year}-${String(dateRange.value.end.month).padStart(2, '0')}-${String(dateRange.value.end.day).padStart(2, '0')}`
      parts.push(`to ${formatDateOnly(endDate)}`)
    }
    return parts.join(' ')
  }

  const periodMap: Record<string, string> = {
    '7': '7 days',
    '15': '15 days',
    '30': '30 days',
    '90': '3 months',
    '180': '6 months',
    '365': '12 months'
  }
  return periodMap[selectedPeriod.value] || 'all time'
})

// Filter readings based on selected period or custom date range
const filteredReadings = computed(() => {
  // Create a copy to avoid mutating the original array
  let filtered = [...readings.value]

  // Handle custom date range
  if (dateRange.value && dateRange.value.start) {
    const startDate = new Date(`${dateRange.value.start.year}-${String(dateRange.value.start.month).padStart(2, '0')}-${String(dateRange.value.start.day).padStart(2, '0')}`)
    startDate.setHours(0, 0, 0, 0) // Start of day
    filtered = filtered.filter(r => new Date(r.timestamp) >= startDate)
  }
  if (dateRange.value && dateRange.value.end) {
    const endDate = new Date(`${dateRange.value.end.year}-${String(dateRange.value.end.month).padStart(2, '0')}-${String(dateRange.value.end.day).padStart(2, '0')}`)
    endDate.setHours(23, 59, 59, 999)  // End of day
    filtered = filtered.filter(r => new Date(r.timestamp) <= endDate)
  }

  // Handle preset period if no custom dates
  if (!dateRange.value && selectedPeriod.value) {
    const daysAgo = parseInt(selectedPeriod.value)
    if (!isNaN(daysAgo)) {
      const periodStartDate = new Date()
      periodStartDate.setDate(periodStartDate.getDate() - daysAgo)
      filtered = filtered.filter(r => new Date(r.timestamp) >= periodStartDate)
    }
  }

  // Sort by timestamp descending (most recent first) - only for table display
  return filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
})

const chartData = computed(() => {
  if (!readings.value.length) return null

  return {
    datasets: [
      {
        label: 'kWh',
        data: readings.value.map(r => ({
          x: new Date(r.timestamp),
          y: r.reading_kwh
        })),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.1,
        pointRadius: 4,
        pointHoverRadius: 6
      }
    ]
  }
})

const chartOptions = computed(() => {
  // Determine time bounds based on custom dates or preset period
  let startDate: Date
  let endDate: Date
  let daysAgo = 0

  if (dateRange.value && (dateRange.value.start || dateRange.value.end)) {
    // Use custom date range
    if (dateRange.value.start) {
      startDate = new Date(`${dateRange.value.start.year}-${String(dateRange.value.start.month).padStart(2, '0')}-${String(dateRange.value.start.day).padStart(2, '0')}`)
    } else {
      startDate = new Date(readings.value[0]?.timestamp || new Date())
    }
    if (dateRange.value.end) {
      endDate = new Date(`${dateRange.value.end.year}-${String(dateRange.value.end.month).padStart(2, '0')}-${String(dateRange.value.end.day).padStart(2, '0')}`)
    } else {
      endDate = new Date()
    }
    daysAgo = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))
  } else if (selectedPeriod.value) {
    // Use preset period
    daysAgo = parseInt(selectedPeriod.value)
    endDate = new Date()
    startDate = new Date()
    startDate.setDate(startDate.getDate() - daysAgo)
  } else {
    // All time - use data bounds
    if (readings.value.length > 0) {
      const timestamps = readings.value.map(r => new Date(r.timestamp).getTime())
      startDate = new Date(Math.min(...timestamps))
      endDate = new Date(Math.max(...timestamps))
      daysAgo = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))
    } else {
      endDate = new Date()
      startDate = new Date()
      startDate.setDate(startDate.getDate() - 90)
      daysAgo = 90
    }
  }

  // Calculate y-axis range based on data
  let yMin, yMax
  if (readings.value.length > 0) {
    const values = readings.value.map(r => r.reading_kwh)
    const dataMin = Math.min(...values)
    const dataMax = Math.max(...values)
    const range = dataMax - dataMin

    // Add 10% padding on each side, or at least 50 kWh
    const padding = Math.max(range * 0.1, 50)
    yMin = Math.floor(dataMin - padding)
    yMax = Math.ceil(dataMax + padding)
  }

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
          title: (context: any) => {
            return format(new Date(context[0].parsed.x), 'MMM dd, yyyy HH:mm')
          },
          label: (context: any) => {
            return `${context.parsed.y.toFixed(1)} kWh`
          }
        }
      }
    },
    scales: {
      x: {
        type: 'time' as const,
        min: startDate.getTime(),
        max: endDate.getTime(),
        time: {
          unit: daysAgo > 90 ? 'month' as const : 'day' as const,
          displayFormats: {
            day: 'MMM dd',
            month: 'MMM yyyy'
          },
          tooltipFormat: 'MMM dd, yyyy'
        },
        title: {
          display: false
        }
      },
      y: {
        min: yMin,
        max: yMax,
        title: {
          display: true,
          text: 'kWh'
        },
        ticks: {
          callback: function(value: any) {
            return value.toLocaleString()
          }
        }
      }
    }
  }
})

// Calculate consumption between readings
const consumptionPeriods = computed(() => {
  if (readings.value.length < 2) return []

  const periods = []
  for (let i = 1; i < readings.value.length; i++) {
    const current = readings.value[i]
    const previous = readings.value[i - 1]

    const startDate = new Date(previous.timestamp)
    const endDate = new Date(current.timestamp)
    const days = Math.max(1, (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))

    const consumption = current.reading_kwh - previous.reading_kwh
    const dailyRate = consumption / days
    const avgPrice = (current.price_per_kwh + previous.price_per_kwh) / 2
    const cost = consumption * avgPrice

    periods.push({
      startDate,
      endDate,
      days: Math.round(days * 10) / 10,
      consumption,
      dailyRate,
      cost,
      label: `${format(startDate, 'MMM dd')} - ${format(endDate, 'MMM dd')}`
    })
  }

  return periods
})

// Daily cost chart data (with kWh data embedded for tooltip)
const costChartData = computed(() => {
  if (!consumptionPeriods.value.length) return null

  return {
    datasets: [{
      label: '€/day',
      data: consumptionPeriods.value.map((p, index) => ({
        x: p.endDate.getTime(),
        y: p.cost / p.days,  // Daily cost instead of total cost
        periodIndex: index,  // Store index for tooltip lookup
        period: p  // Store full period data for tooltip
      })),
      backgroundColor: 'rgba(34, 197, 94, 0.5)',
      borderColor: 'rgb(34, 197, 94)',
      borderWidth: 1
    }]
  }
})

// Cost chart options with custom tooltip showing both € and kWh
const costChartOptions = computed(() => {
  // Determine time bounds based on custom dates or preset period
  let startDate: Date
  let endDate: Date
  let daysAgo = 0

  if (dateRange.value && (dateRange.value.start || dateRange.value.end)) {
    // Use custom date range
    if (dateRange.value.start) {
      startDate = new Date(`${dateRange.value.start.year}-${String(dateRange.value.start.month).padStart(2, '0')}-${String(dateRange.value.start.day).padStart(2, '0')}`)
    } else {
      startDate = new Date(readings.value[0]?.timestamp || new Date())
    }
    if (dateRange.value.end) {
      endDate = new Date(`${dateRange.value.end.year}-${String(dateRange.value.end.month).padStart(2, '0')}-${String(dateRange.value.end.day).padStart(2, '0')}`)
    } else {
      endDate = new Date()
    }
    daysAgo = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))
  } else if (selectedPeriod.value) {
    // Use preset period
    daysAgo = parseInt(selectedPeriod.value)
    endDate = new Date()
    startDate = new Date()
    startDate.setDate(startDate.getDate() - daysAgo)
  } else {
    // All time - use data bounds
    if (readings.value.length > 0) {
      const timestamps = readings.value.map(r => new Date(r.timestamp).getTime())
      startDate = new Date(Math.min(...timestamps))
      endDate = new Date(Math.max(...timestamps))
      daysAgo = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))
    } else {
      endDate = new Date()
      startDate = new Date()
      startDate.setDate(startDate.getDate() - 90)
      daysAgo = 90
    }
  }

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
          title: (context: any) => {
            const dataPoint = context[0].raw
            if (!dataPoint || !dataPoint.period) return ''
            return dataPoint.period.label
          },
          afterTitle: (context: any) => {
            const dataPoint = context[0].raw
            if (!dataPoint || !dataPoint.period) return ''
            return `${dataPoint.period.days} days`
          },
          label: (context: any) => {
            const dataPoint = context.raw
            if (!dataPoint || !dataPoint.period) return ''

            const dailyCost = dataPoint.period.cost / dataPoint.period.days
            return `Cost: €${dailyCost.toFixed(2)}/day`
          },
          afterLabel: (context: any) => {
            const dataPoint = context.raw
            if (!dataPoint || !dataPoint.period) return ''

            const dailyKwh = dataPoint.period.dailyRate
            return `Consumption: ${dailyKwh.toFixed(2)} kWh/day`
          }
        }
      }
    },
    scales: {
      x: {
        type: 'time' as const,
        min: startDate.getTime(),
        max: endDate.getTime(),
        time: {
          unit: daysAgo > 90 ? 'month' as const : 'day' as const,
          displayFormats: {
            day: 'MMM dd',
            month: 'MMM yyyy'
          }
        }
      },
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: '€/day'
        },
        ticks: {
          callback: function(value: any) {
            return '€' + value.toFixed(2)
          }
        }
      }
    }
  }
})

const formatNumber = (num: number) => {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(num)
}

const formatDate = (dateString: string) => {
  return format(new Date(dateString), 'MMM dd, HH:mm')
}

const formatDateTime = (dateString: string) => {
  return format(new Date(dateString), 'MMM dd, yyyy HH:mm')
}

const formatDateOnly = (dateString: string) => {
  return format(new Date(dateString), 'MMM dd, yyyy')
}

const getConfidenceVariant = (confidence: number) => {
  if (confidence >= 90) return 'default'
  if (confidence >= 70) return 'secondary'
  return 'outline'
}

const selectPeriod = async (period: string) => {
  if (period === '') {
    // Reset button clicked
    selectedPeriod.value = ''
    dateRange.value = undefined
    fetchData()
  } else {
    selectedPeriod.value = period
    // Auto-fill date range picker when selecting preset period
    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - parseInt(period))

    // Convert to DateValue format for RangeCalendar
    const { CalendarDate } = await import('@internationalized/date')
    dateRange.value = {
      start: new CalendarDate(startDate.getFullYear(), startDate.getMonth() + 1, startDate.getDate()),
      end: new CalendarDate(endDate.getFullYear(), endDate.getMonth() + 1, endDate.getDate())
    }
    fetchData()
  }
}

const selectReading = (reading: Reading) => {
  selectedReading.value = reading
}

const confirmDeleteReading = (reading: Reading) => {
  readingToDelete.value = reading
}

const deleteReading = async () => {
  if (!readingToDelete.value) return

  try {
    await api.delete(`/readings/${readingToDelete.value.id}`)
    readingToDelete.value = null
    // Refresh data
    fetchData()
  } catch (error) {
    console.error('Error deleting reading:', error)
    alert('Failed to delete reading')
  }
}

const fetchData = async () => {
  console.log('Fetching dashboard data...')
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
      devices.value = devicesResponse.data.devices || []
    } catch (error) {
      console.log('No devices found')
      devices.value = [] // Ensure empty array on error
    }

    // Fetch readings for chart
    try {
      // Fetch all readings (without date filter)
      const readingsResponse = await api.get('/readings', {
        params: {
          limit: 1000
        }
      })

      const allReadings = readingsResponse.data.readings?.reverse() || []
      let periodStartDate: Date | null = null

      // Determine period start based on dateRange or selectedPeriod
      if (dateRange.value && dateRange.value.start) {
        periodStartDate = new Date(`${dateRange.value.start.year}-${String(dateRange.value.start.month).padStart(2, '0')}-${String(dateRange.value.start.day).padStart(2, '0')}`)
        periodStartDate.setHours(0, 0, 0, 0)
      } else if (selectedPeriod.value) {
        const daysAgo = parseInt(selectedPeriod.value)
        if (!isNaN(daysAgo)) {
          periodStartDate = new Date()
          periodStartDate.setDate(periodStartDate.getDate() - daysAgo)
        }
      }

      // If no period selected, show all readings
      if (!periodStartDate) {
        readings.value = allReadings
        totalReadings.value = readingsResponse.data.total || 0
      } else {
        // Find the last reading before the period start
        const readingsBeforePeriod = allReadings.filter(r =>
          new Date(r.timestamp) < periodStartDate!
        )
        const lastReadingBeforePeriod = readingsBeforePeriod.length > 0
          ? readingsBeforePeriod[readingsBeforePeriod.length - 1]
          : null

        // Get readings within the period
        const readingsInPeriod = allReadings.filter(r =>
          new Date(r.timestamp) >= periodStartDate!
        )

        // Combine: include the last point before period (if exists) + all points in period
        readings.value = lastReadingBeforePeriod
          ? [lastReadingBeforePeriod, ...readingsInPeriod]
          : readingsInPeriod

        totalReadings.value = readingsResponse.data.total || 0
      }

    } catch (error) {
      console.log('No readings found')
      readings.value = [] // Ensure empty array on error
      totalReadings.value = 0
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