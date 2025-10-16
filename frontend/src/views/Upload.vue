<template>
  <div class="container mx-auto p-6 max-w-2xl">
    <h1 class="text-3xl font-bold mb-6">Upload Reading</h1>

    <Card>
      <CardHeader>
        <CardTitle>Manual Upload</CardTitle>
        <CardDescription>
          Upload a photo of your electricity meter. The system will attempt to extract the reading automatically.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div class="space-y-4">
          <!-- File Upload -->
          <div class="space-y-2">
            <Label>Meter Photo (optional)</Label>
            <div
              @drop="handleDrop"
              @dragover.prevent
              @dragenter.prevent
              :class="[
                'border-2 border-dashed rounded-lg p-6 text-center transition-all',
                isUploading ? 'border-gray-200 bg-gray-50 cursor-not-allowed' : 'border-gray-300 hover:border-gray-400 cursor-pointer'
              ]"
              @click="!isUploading && $refs.fileInput.click()"
            >
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                @change="handleFileSelect"
                :disabled="isUploading"
                class="hidden"
              />
              
              <div v-if="!selectedFile" class="space-y-2">
                <Upload class="mx-auto h-12 w-12 text-gray-400" />
                <p class="text-sm text-gray-600">
                  Drag and drop your image here, or
                </p>
                <Button type="button" variant="secondary" :disabled="isUploading">
                  <Upload class="mr-2 h-4 w-4" />
                  Choose File
                </Button>
              </div>
              
              <div v-else class="space-y-2">
                <p class="text-sm font-medium">{{ selectedFile.name }}</p>
                <p class="text-xs text-gray-500">{{ formatFileSize(selectedFile.size) }}</p>
                <Button type="button" variant="outline" size="sm" @click="removeFile">
                  Remove
                </Button>
              </div>
            </div>
          </div>

          <!-- Upload Progress -->
          <div v-if="isUploading" class="space-y-2">
            <div class="flex items-center justify-between">
              <Label>Upload Progress</Label>
              <span class="text-sm font-medium">{{ uploadProgress }}%</span>
            </div>
            <Progress :value="uploadProgress" class="h-3" />
            <p class="text-xs text-muted-foreground">Processing your meter image...</p>
          </div>

          <!-- Image Preview -->
          <div v-if="imagePreview" class="space-y-2">
            <Label>Preview</Label>
            <img :src="imagePreview" alt="Preview" class="max-w-full h-64 object-contain rounded-lg" />
          </div>

          <!-- Date/Time Selection -->
          <div class="space-y-2">
            <Label>Reading Date & Time</Label>
            <Popover>
              <PopoverTrigger as-child>
                <Button
                  type="button"
                  variant="outline"
                  :class="[
                    'w-full justify-start text-left font-normal',
                    !readingDateTime && 'text-muted-foreground'
                  ]"
                  :disabled="isUploading"
                >
                  <CalendarIcon class="mr-2 h-4 w-4" />
                  <span v-if="readingDateTime">{{ formatDateTime(readingDateTime) }}</span>
                  <span v-else>Pick a date and time</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-auto p-0" align="start">
                <Calendar
                  v-model="selectedDate"
                  mode="single"
                  :initial-focus="true"
                />
                <div class="p-3 border-t">
                  <Label class="text-xs text-muted-foreground">Time</Label>
                  <div class="flex gap-2 mt-2">
                    <Input
                      v-model="selectedHour"
                      type="number"
                      min="0"
                      max="23"
                      placeholder="HH"
                      class="w-16 text-center"
                    />
                    <span class="flex items-center">:</span>
                    <Input
                      v-model="selectedMinute"
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
            <p class="text-sm text-muted-foreground">
              Set the date and time for this reading (defaults to now)
            </p>
          </div>

          <!-- Manual Reading Input -->
          <div class="space-y-2">
            <Label for="manual-reading">Manual Reading (kWh)</Label>
            <Input
              id="manual-reading"
              v-model="manualReading"
              type="number"
              step="0.01"
              placeholder="Enter meter reading in kWh"
              :disabled="isUploading"
            />
            <p class="text-sm text-muted-foreground">
              Enter manually or let OCR auto-detect from photo. At least one is required.
            </p>
          </div>

          <!-- Notes Input -->
          <div class="space-y-2">
            <Label for="notes">Notes (optional)</Label>
            <Textarea
              id="notes"
              v-model="notes"
              placeholder="Add any observations about this reading..."
              :disabled="isUploading"
              class="min-h-[80px] resize-y"
            />
            <p class="text-sm text-muted-foreground">
              Record any observations or context for this reading
            </p>
          </div>

          <!-- Submit Button -->
          <Button
            type="button"
            class="w-full"
            :disabled="(!selectedFile && !manualReading) || isUploading"
            @click="handleSubmit"
          >
            <Loader2 v-if="isUploading" class="mr-2 h-4 w-4 animate-spin" />
            <span v-if="isUploading">Uploading... {{ uploadProgress }}%</span>
            <span v-else>Submit Reading</span>
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- Result Alert -->
    <Alert v-if="uploadResult" :variant="uploadResult.success ? 'default' : 'destructive'" class="mt-6">
      <CheckCircle2 v-if="uploadResult.success" class="h-4 w-4" />
      <XCircle v-else class="h-4 w-4" />
      <AlertTitle>{{ uploadResult.success ? 'Upload Successful' : 'Upload Failed' }}</AlertTitle>
      <AlertDescription>
        <div v-if="uploadResult.success" class="space-y-2 mt-2">
          <div class="flex items-center justify-between">
            <span class="text-sm">Reading:</span>
            <span class="font-bold text-lg">{{ uploadResult.reading_kwh }} kWh</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm">OCR Confidence:</span>
            <Badge :variant="uploadResult.ocr_confidence && uploadResult.ocr_confidence > 90 ? 'default' : 'secondary'">
              {{ uploadResult.ocr_confidence?.toFixed(1) }}%
            </Badge>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm">Cost:</span>
            <span class="font-semibold text-lg">€{{ uploadResult.cost?.toFixed(2) }}</span>
          </div>
          <div class="mt-4 pt-4 border-t">
            <Button @click="navigateToHistory" variant="outline" class="w-full">
              View in History
            </Button>
          </div>
        </div>
        <div v-else class="mt-2">
          <p>{{ uploadResult.error }}</p>
          <Button @click="retryUpload" variant="outline" size="sm" class="mt-3">
            Try Again
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'
import { api } from '@/lib/api'
import { Loader2, CheckCircle2, XCircle, Upload, CalendarIcon } from 'lucide-vue-next'
import { toast } from '@/components/ui/toast'
import type { DateValue } from '@internationalized/date'
import { CalendarDate, toCalendarDate, getLocalTimeZone, today } from '@internationalized/date'

interface UploadResult {
  success: boolean
  reading_kwh?: number
  ocr_confidence?: number
  cost?: number
  error?: string
}

const fileInput = ref<HTMLInputElement>()
const selectedFile = ref<File | null>(null)
const imagePreview = ref<string | null>(null)
const selectedDate = ref<DateValue>()
const selectedHour = ref<string>('')
const selectedMinute = ref<string>('')
const manualReading = ref<string>('')
const notes = ref<string>('')
const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadResult = ref<UploadResult | null>(null)

// Initialize with current date and time
const initializeDateTime = () => {
  const now = new Date()
  selectedDate.value = new CalendarDate(now.getFullYear(), now.getMonth() + 1, now.getDate())
  selectedHour.value = now.getHours().toString().padStart(2, '0')
  selectedMinute.value = now.getMinutes().toString().padStart(2, '0')
}

// Initialize on mount
initializeDateTime()

// Computed property for the combined date/time
const readingDateTime = computed(() => {
  if (selectedDate.value) {
    const hour = selectedHour.value ? parseInt(selectedHour.value) : 0
    const minute = selectedMinute.value ? parseInt(selectedMinute.value) : 0
    // Convert DateValue to JavaScript Date
    const date = new Date(selectedDate.value.year, selectedDate.value.month - 1, selectedDate.value.day, hour, minute)
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

const formatDateTime = (date: Date | null) => {
  if (!date) return ''
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Istanbul' // GMT+3
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
  if (isUploading.value) return
  
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    setFile(event.dataTransfer.files[0])
  }
}

const setFile = (file: File) => {
  // Clear previous error
  uploadResult.value = null
  
  // Validate file type
  if (!file.type.startsWith('image/')) {
    uploadResult.value = {
      success: false,
      error: 'Please select an image file (JPEG, PNG, GIF, etc.)'
    }
    toast.error('Invalid file type', {
      description: 'Please select an image file (JPEG, PNG, GIF, etc.)',
    })
    return
  }
  
  // Validate file size (max 10MB)
  const maxSize = 10 * 1024 * 1024 // 10MB
  if (file.size > maxSize) {
    uploadResult.value = {
      success: false,
      error: `File is too large. Maximum size is 10MB, your file is ${formatFileSize(file.size)}`
    }
    toast.error('File too large', {
      description: `Maximum size is 10MB, your file is ${formatFileSize(file.size)}`,
    })
    return
  }
  
  selectedFile.value = file
  
  // Create preview
  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target?.result as string
  }
  reader.readAsDataURL(file)
}

const removeFile = () => {
  selectedFile.value = null
  imagePreview.value = null
  uploadResult.value = null // Clear any errors
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const router = useRouter()

const navigateToHistory = () => {
  router.push('/history')
}

const retryUpload = () => {
  uploadResult.value = null
  uploadProgress.value = 0
}

const handleSubmit = async () => {
  console.log('Submit button clicked')
  console.log('Selected file:', selectedFile.value)
  console.log('Manual reading:', manualReading.value)

  // Validate that either file or manual reading is provided
  if (!selectedFile.value && !manualReading.value) {
    uploadResult.value = {
      success: false,
      error: 'Please provide either a photo or enter a manual reading'
    }
    toast.error('Missing input', {
      description: 'Please provide either a photo or enter a manual reading',
    })
    return
  }

  // Validate manual reading if provided
  if (manualReading.value) {
    const reading = parseFloat(manualReading.value)
    if (isNaN(reading) || reading < 0) {
      uploadResult.value = {
        success: false,
        error: 'Manual reading must be a positive number'
      }
      toast.error('Invalid reading', {
        description: 'Manual reading must be a positive number',
      })
      return
    }
  }

  isUploading.value = true
  uploadResult.value = null
  uploadProgress.value = 0

  try {
    const formData = new FormData()

    // Add file if provided
    if (selectedFile.value) {
      formData.append('file', selectedFile.value)
    }

    // Add timestamp (always use current if set)
    if (readingDateTime.value) {
      formData.append('timestamp', readingDateTime.value.toISOString())
    }

    // Add notes if provided
    if (notes.value && notes.value.trim()) {
      formData.append('notes', notes.value.trim())
    }

    // Add manual reading if provided
    if (manualReading.value) {
      formData.append('reading_kwh', manualReading.value)
    }
    
    console.log('Sending request to /upload/manual')
    
    // Show upload started toast
    toast.info('Uploading image...', {
      description: 'Processing your meter reading',
    })
    
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
    
    console.log('Upload response:', response.data)

    // If OCR was successful and no manual reading was provided, fill it in
    if (response.data.reading_kwh && !manualReading.value) {
      manualReading.value = response.data.reading_kwh.toString()
      toast.info('OCR Reading Detected', {
        description: `Auto-filled reading: ${response.data.reading_kwh} kWh (${response.data.ocr_confidence?.toFixed(1)}% confidence)`,
      })
    }

    uploadResult.value = {
      success: true,
      reading_kwh: response.data.reading_kwh,
      ocr_confidence: response.data.ocr_confidence,
      cost: response.data.cost
    }

    // Show success toast
    toast.success('Upload successful!', {
      description: `Reading: ${response.data.reading_kwh} kWh • Cost: €${response.data.cost.toFixed(2)}`,
    })
    
    // Clear form after a delay
    setTimeout(() => {
      removeFile()
      selectedDate.value = undefined
      selectedHour.value = ''
      selectedMinute.value = ''
      manualReading.value = ''
      notes.value = ''
      uploadProgress.value = 0
    }, 2000)
  } catch (error: any) {
    console.error('Upload error:', error)
    console.error('Error response:', error.response)
    
    let errorMessage = 'Upload failed. Please try again.'
    let errorTitle = 'Upload failed'
    
    if (error.code === 'ERR_NETWORK') {
      errorMessage = 'Network error. Please check your connection and ensure the backend is running.'
      errorTitle = 'Network error'
    } else if (error.code === 'ECONNABORTED') {
      errorMessage = 'Upload timeout. The file might be too large or the connection is slow.'
      errorTitle = 'Upload timeout'
    } else if (error.response) {
      // Server responded with error
      if (error.response.status === 413) {
        errorMessage = 'File is too large for the server to process.'
        errorTitle = 'File too large'
      } else if (error.response.status === 415) {
        errorMessage = 'Invalid file type. Please upload an image file.'
        errorTitle = 'Invalid file type'
      } else if (error.response.status === 500) {
        errorMessage = 'Server error. Please try again later.'
        errorTitle = 'Server error'
      } else if (error.response.data?.detail) {
        errorMessage = error.response.data.detail
      }
    }
    
    uploadResult.value = {
      success: false,
      error: errorMessage
    }
    
    // Show error toast
    toast.error(errorTitle, {
      description: errorMessage,
    })
  } finally {
    isUploading.value = false
  }
}
</script>