<template>
  <div class="p-8 space-y-4">
    <h1 class="text-2xl font-bold">Theme Test</h1>
    
    <div class="grid grid-cols-2 gap-4">
      <div class="p-4 bg-background text-foreground border rounded-lg">
        <h2 class="font-semibold">Background/Foreground</h2>
        <p>This uses the background and foreground colors</p>
      </div>
      
      <div class="p-4 bg-primary text-primary-foreground rounded-lg">
        <h2 class="font-semibold">Primary</h2>
        <p>This uses the primary colors</p>
      </div>
      
      <div class="p-4 bg-secondary text-secondary-foreground rounded-lg">
        <h2 class="font-semibold">Secondary</h2>
        <p>This uses the secondary colors</p>
      </div>
      
      <div class="p-4 bg-muted text-muted-foreground rounded-lg">
        <h2 class="font-semibold">Muted</h2>
        <p>This uses the muted colors</p>
      </div>
      
      <div class="p-4 bg-accent text-accent-foreground rounded-lg">
        <h2 class="font-semibold">Accent</h2>
        <p>This uses the accent colors</p>
      </div>
      
      <div class="p-4 bg-destructive text-destructive-foreground rounded-lg">
        <h2 class="font-semibold">Destructive</h2>
        <p>This uses the destructive colors</p>
      </div>
      
      <div class="p-4 bg-card text-card-foreground border rounded-lg">
        <h2 class="font-semibold">Card</h2>
        <p>This uses the card colors</p>
      </div>
      
      <div class="p-4 bg-popover text-popover-foreground border rounded-lg">
        <h2 class="font-semibold">Popover</h2>
        <p>This uses the popover colors</p>
      </div>
    </div>
    
    <div class="flex gap-2">
      <button @click="toggleTheme" class="px-4 py-2 bg-primary text-primary-foreground rounded-md">
        Toggle Theme ({{ isDark ? 'Dark' : 'Light' }})
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const isDark = ref(false)

const toggleTheme = () => {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

onMounted(() => {
  isDark.value = document.documentElement.classList.contains('dark')
})
</script>