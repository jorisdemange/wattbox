<template>
  <div vaul-drawer-wrapper class="min-h-screen bg-white dark:bg-zinc-900">
    <!-- Toast notifications -->
    <Toaster />
    
    <!-- Navigation Header -->
    <header class="border-b">
      <div class="container mx-auto px-6 py-4">
        <nav class="flex items-center justify-between">
          <div class="flex items-center space-x-8">
            <h1 class="text-2xl font-bold">⚡ WattBox</h1>
          </div>

          <div class="flex items-center gap-2">
            <!-- Theme toggle -->
            <ModeToggle />
            <!-- Settings button -->
            <Button variant="outline" size="sm" @click="settingsOpen = true">
              <Settings class="h-4 w-4 mr-2" />
              Settings
            </Button>
          </div>
        </nav>
        
      </div>
    </header>

    <!-- Settings Drawer -->
    <SettingsDrawer v-model:open="settingsOpen" />

    <!-- Main Content -->
    <main>
      <RouterView :key="$route.fullPath" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterView } from 'vue-router'
import { Toaster } from '@/components/ui/toast'
import { Button } from '@/components/ui/button'
import { Settings } from 'lucide-vue-next'
import ModeToggle from '@/components/ModeToggle.vue'
import SettingsDrawer from '@/components/SettingsDrawer.vue'
import 'vue-sonner/style.css'

const settingsOpen = ref(false)
</script>

<style>
/* Ensure proper styling for the entire app */
body {
  margin: 0;
  padding: 0;
}
</style>