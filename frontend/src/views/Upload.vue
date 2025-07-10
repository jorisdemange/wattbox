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
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <!-- File Upload -->
          <FormItem>
            <FormLabel>Meter Photo</FormLabel>
            <FormControl>
              <div
                @drop="handleDrop"
                @dragover.prevent
                @dragenter.prevent
                class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 transition-colors"
              >
                <input
                  ref="fileInput"
                  type="file"
                  accept="image/*"
                  @change="handleFileSelect"
                  class="hidden"
                />
                
                <div v-if="!selectedFile" class="space-y-2">
                  <p class="text-sm text-gray-600">
                    Drag and drop your image here, or
                  </p>
                  <Button type="button" variant="secondary" @click="$refs.fileInput.click()">
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
            </FormControl>
          </FormItem>

          <!-- Upload Progress -->
          <div v-if="isUploading && uploadProgress > 0" class="space-y-2">
            <Label>Upload Progress</Label>
            <Progress :value="uploadProgress" />
          </div>

          <!-- Image Preview -->
          <FormItem v-if="imagePreview">
            <FormLabel>Preview</FormLabel>
            <FormControl>
              <img :src="imagePreview" alt="Preview" class="max-w-full h-64 object-contain rounded-lg" />
            </FormControl>
          </FormItem>

          <!-- Manual Reading Input -->
          <FormItem>
            <FormLabel for="manual-reading">Manual Reading (optional)</FormLabel>
            <FormControl>
              <Input
                id="manual-reading"
                v-model="manualReading"
                type="number"
                step="0.01"
                placeholder="Enter reading if OCR fails"
              />
            </FormControl>
            <FormDescription>
              Leave empty to use automatic OCR detection
            </FormDescription>
          </FormItem>

          <!-- Submit Button -->
          <Button
            type="submit"
            class="w-full"
            :disabled="!selectedFile || isUploading"
          >
            <span v-if="isUploading">Uploading...</span>
            <span v-else>Upload Reading</span>
          </Button>
        </form>
      </CardContent>
    </Card>

    <!-- Result Alert -->
    <Alert v-if="uploadResult" :variant="uploadResult.success ? 'default' : 'destructive'" class="mt-6">
      <AlertTitle>{{ uploadResult.success ? 'Upload Successful' : 'Upload Failed' }}</AlertTitle>
      <AlertDescription>
        <div v-if="uploadResult.success" class="space-y-1">
          <p>Reading: <span class="font-bold">{{ uploadResult.reading_kwh }} kWh</span></p>
          <p>OCR Confidence: <Badge variant="outline">{{ uploadResult.ocr_confidence?.toFixed(1) }}%</Badge></p>
          <p>Cost: <span class="font-semibold">€{{ uploadResult.cost?.toFixed(2) }}</span></p>
        </div>
        <div v-else>
          <p>{{ uploadResult.error }}</p>
        </div>
      </AlertDescription>
    </Alert>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FormControl, FormDescription, FormItem, FormLabel } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'

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
const manualReading = ref<string>('')
const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadResult = ref<UploadResult | null>(null)

const formatFileSize = (bytes: number) => {
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  if (bytes === 0) return '0 Bytes'
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    setFile(target.files[0])
  }
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    setFile(event.dataTransfer.files[0])
  }
}

const setFile = (file: File) => {
  if (!file.type.startsWith('image/')) {
    alert('Please select an image file')
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
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const handleSubmit = async () => {
  if (!selectedFile.value) return
  
  isUploading.value = true
  uploadResult.value = null
  uploadProgress.value = 0
  
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    
    if (manualReading.value) {
      formData.append('reading_kwh', manualReading.value)
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
    
    uploadResult.value = {
      success: true,
      reading_kwh: response.data.reading_kwh,
      ocr_confidence: response.data.ocr_confidence,
      cost: response.data.cost
    }
    
    // Clear form after a delay
    setTimeout(() => {
      removeFile()
      manualReading.value = ''
      uploadProgress.value = 0
    }, 2000)
  } catch (error: any) {
    uploadResult.value = {
      success: false,
      error: error.response?.data?.detail || 'Upload failed'
    }
  } finally {
    isUploading.value = false
  }
}
</script>