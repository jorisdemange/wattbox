<script setup lang="ts">
import { ref, computed } from 'vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { api } from '@/lib/api'
import { Loader2, CheckCircle2, XCircle, Upload, CalendarIcon } from 'lucide-vue-next'
import { toast } from '@/components/ui/toast'
import type { DateValue } from '@internationalized/date'
import { CalendarDate } from '@internationalized/date'

interface UploadResult {
  success: boolean
  reading_kwh?: number
  ocr_confidence?: number
  cost?: number
  error?: string
}

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  'upload-success': []
}>()

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
  if (isUploading.value) return

  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    setFile(event.dataTransfer.files[0])
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

  selectedFile.value = file

  const reader = new FileReader()
  reader.onload = (e) => {
    imagePreview.value = e.target?.result as string
  }
  reader.readAsDataURL(file)
}

const removeFile = () => {
  selectedFile.value = null
  imagePreview.value = null
  uploadResult.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const handleSubmit = async () => {
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

    if (selectedFile.value) {
      formData.append('file', selectedFile.value)
    }

    if (readingDateTime.value) {
      formData.append('timestamp', readingDateTime.value.toISOString())
    }

    if (notes.value && notes.value.trim()) {
      formData.append('notes', notes.value.trim())
    }

    if (manualReading.value) {
      formData.append('reading_kwh', manualReading.value)
    }

    toast.info('Uploading...', {
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

    if (response.data.reading_kwh && !manualReading.value) {
      manualReading.value = response.data.reading_kwh.toString()
      toast.info('OCR Reading Detected', {
        description: `Auto-filled: ${response.data.reading_kwh} kWh (${response.data.ocr_confidence?.toFixed(1)}% confidence)`,
      })
    }

    uploadResult.value = {
      success: true,
      reading_kwh: response.data.reading_kwh,
      ocr_confidence: response.data.ocr_confidence,
      cost: response.data.cost
    }

    toast.success('Upload successful!', {
      description: `Reading: ${response.data.reading_kwh} kWh • Cost: €${response.data.cost.toFixed(2)}`,
    })

    // Emit success event to refresh dashboard
    emit('upload-success')

    // Clear form and close sheet after delay
    setTimeout(() => {
      removeFile()
      initializeDateTime()
      manualReading.value = ''
      notes.value = ''
      uploadProgress.value = 0
      uploadResult.value = null
      emit('update:open', false)
    }, 2000)
  } catch (error: any) {
    console.error('Upload error:', error)

    let errorMessage = 'Upload failed. Please try again.'

    if (error.response?.data?.detail) {
      errorMessage = error.response.data.detail
    }

    uploadResult.value = {
      success: false,
      error: errorMessage
    }

    toast.error('Upload failed', {
      description: errorMessage,
    })
  } finally {
    isUploading.value = false
  }
}
</script>

<template>
  <Sheet :open="open" @update:open="emit('update:open', $event)">
    <SheetContent side="bottom">
      <SheetHeader>
        <SheetTitle>Add Reading</SheetTitle>
        <SheetDescription>
          Upload a photo of your meter or enter the reading manually
        </SheetDescription>
      </SheetHeader>

      <div class="p-4 space-y-4 overflow-y-auto max-h-[70vh]">
        <!-- File Upload -->
        <div class="space-y-2">
          <Label>Meter Photo (optional)</Label>
          <div
            @drop="handleDrop"
            @dragover.prevent
            @dragenter.prevent
            :class="[
              'border-2 border-dashed rounded-lg p-6 text-center transition-all',
              isUploading ? 'border-gray-200 bg-gray-50 dark:bg-gray-900 cursor-not-allowed' : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600 cursor-pointer'
            ]"
            @click="!isUploading && fileInput?.click()"
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
              <p class="text-sm text-gray-600 dark:text-gray-400">
                Drag and drop or tap to choose
              </p>
            </div>

            <div v-else class="space-y-2">
              <p class="text-sm font-medium">{{ selectedFile.name }}</p>
              <p class="text-xs text-gray-500">{{ formatFileSize(selectedFile.size) }}</p>
              <Button type="button" variant="outline" size="sm" @click.stop="removeFile">
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
        </div>

        <!-- Image Preview -->
        <div v-if="imagePreview" class="space-y-2">
          <Label>Preview</Label>
          <img :src="imagePreview" alt="Preview" class="max-w-full h-48 object-contain rounded-lg" />
        </div>

        <!-- Manual Reading Input -->
        <div class="space-y-2">
          <Label for="manual-reading">Manual Reading (kWh)</Label>
          <Input
            id="manual-reading"
            v-model="manualReading"
            type="number"
            step="0.01"
            placeholder="Enter meter reading"
            :disabled="isUploading"
          />
          <p class="text-sm text-muted-foreground">
            Enter manually or let OCR auto-detect from photo
          </p>
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
            Defaults to now
          </p>
        </div>

        <!-- Notes Input -->
        <div class="space-y-2">
          <Label for="notes">Notes (optional)</Label>
          <Textarea
            id="notes"
            v-model="notes"
            placeholder="Add any observations..."
            :disabled="isUploading"
            class="min-h-[60px] resize-y"
          />
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

        <!-- Result Alert -->
        <Alert v-if="uploadResult" :variant="uploadResult.success ? 'default' : 'destructive'" class="mt-4">
          <CheckCircle2 v-if="uploadResult.success" class="h-4 w-4" />
          <XCircle v-else class="h-4 w-4" />
          <AlertTitle>{{ uploadResult.success ? 'Success' : 'Error' }}</AlertTitle>
          <AlertDescription>
            <div v-if="uploadResult.success" class="space-y-1 mt-2 text-sm">
              <p><strong>Reading:</strong> {{ uploadResult.reading_kwh }} kWh</p>
              <p><strong>Cost:</strong> €{{ uploadResult.cost?.toFixed(2) }}</p>
              <p v-if="uploadResult.ocr_confidence">
                <strong>Confidence:</strong>
                <Badge :variant="uploadResult.ocr_confidence > 90 ? 'default' : 'secondary'" class="ml-2">
                  {{ uploadResult.ocr_confidence.toFixed(1) }}%
                </Badge>
              </p>
            </div>
            <p v-else class="text-sm mt-2">{{ uploadResult.error }}</p>
          </AlertDescription>
        </Alert>
      </div>
    </SheetContent>
  </Sheet>
</template>
