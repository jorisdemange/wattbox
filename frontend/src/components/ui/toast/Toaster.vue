<template>
  <Toaster 
    :theme="theme"
    :position="position"
    :expand="expand"
    :richColors="richColors"
    :closeButton="closeButton"
    :duration="duration"
    class="pointer-events-auto"
  />
</template>

<script setup lang="ts">
import { Toaster } from 'vue-sonner'

interface ToastProps {
  theme?: 'light' | 'dark' | 'system'
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right'
  expand?: boolean
  richColors?: boolean
  closeButton?: boolean
  duration?: number
}

withDefaults(defineProps<ToastProps>(), {
  theme: 'system',
  position: 'bottom-right',
  expand: false,
  richColors: true,
  closeButton: true,
  duration: 5000,
})
</script>