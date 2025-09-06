<template>
  <div class="min-h-screen bg-white dark:bg-zinc-900">
    <!-- Toast notifications -->
    <Toaster />
    
    <!-- Navigation Header -->
    <header class="border-b">
      <div class="container mx-auto px-6 py-4">
        <nav class="flex items-center justify-between">
          <div class="flex items-center space-x-8">
            <h1 class="text-2xl font-bold">⚡ WattBox</h1>
            
            <div class="hidden md:flex space-x-6">
              <RouterLink
                to="/"
                class="text-sm font-medium transition-colors hover:text-blue-600 dark:hover:text-blue-400"
                :class="{ 'text-blue-600 dark:text-blue-400': $route.path === '/' }"
              >
                Dashboard
              </RouterLink>
              <RouterLink
                to="/upload"
                class="text-sm font-medium transition-colors hover:text-blue-600 dark:hover:text-blue-400"
                :class="{ 'text-blue-600 dark:text-blue-400': $route.path === '/upload' }"
              >
                Upload
              </RouterLink>
              <RouterLink
                to="/history"
                class="text-sm font-medium transition-colors hover:text-blue-600 dark:hover:text-blue-400"
                :class="{ 'text-blue-600 dark:text-blue-400': $route.path === '/history' }"
              >
                History
              </RouterLink>
              <RouterLink
                to="/devices"
                class="text-sm font-medium transition-colors hover:text-blue-600 dark:hover:text-blue-400"
                :class="{ 'text-blue-600 dark:text-blue-400': $route.path === '/devices' }"
              >
                Devices
              </RouterLink>
            </div>
          </div>
          
          <!-- Mobile menu button -->
          <button
            @click="mobileMenuOpen = !mobileMenuOpen"
            class="md:hidden p-2 rounded-md hover:bg-gray-100"
          >
            <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                v-if="!mobileMenuOpen"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
              <path
                v-else
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </nav>
        
        <!-- Mobile menu -->
        <div v-if="mobileMenuOpen" class="md:hidden mt-4 pb-4 space-y-2">
          <RouterLink
            to="/"
            class="block px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-100"
            :class="{ 'bg-gray-100': $route.path === '/' }"
            @click="mobileMenuOpen = false"
          >
            Dashboard
          </RouterLink>
          <RouterLink
            to="/upload"
            class="block px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-100"
            :class="{ 'bg-gray-100': $route.path === '/upload' }"
            @click="mobileMenuOpen = false"
          >
            Upload
          </RouterLink>
          <RouterLink
            to="/history"
            class="block px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-100"
            :class="{ 'bg-gray-100': $route.path === '/history' }"
            @click="mobileMenuOpen = false"
          >
            History
          </RouterLink>
          <RouterLink
            to="/devices"
            class="block px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-100"
            :class="{ 'bg-gray-100': $route.path === '/devices' }"
            @click="mobileMenuOpen = false"
          >
            Devices
          </RouterLink>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main>
      <RouterView :key="$route.fullPath" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { Toaster } from '@/components/ui/toast'
import 'vue-sonner/style.css'

const mobileMenuOpen = ref(false)
const route = useRoute()

onMounted(() => {
  console.log('App mounted, current route:', route.path)
})
</script>

<style>
/* Ensure proper styling for the entire app */
body {
  margin: 0;
  padding: 0;
}
</style>