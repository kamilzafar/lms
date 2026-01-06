<template>
	<FrappeUIProvider @contextmenu.prevent="handleContextMenu" class="lms-app-container">
		<Layout class="isolate text-base">
			<router-view />
		</Layout>
		<InstallPrompt v-if="isMobile && !settings.data?.disable_pwa" />
		<Dialogs />
	</FrappeUIProvider>
</template>
<script setup>
import { FrappeUIProvider } from 'frappe-ui'
import { Dialogs } from '@/utils/dialogs'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useScreenSize } from './utils/composables'
import { usersStore } from '@/stores/user'
import { useSettings } from '@/stores/settings'
import { useRouter } from 'vue-router'
import { posthogSettings } from '@/telemetry'
import DesktopLayout from './components/DesktopLayout.vue'
import MobileLayout from './components/MobileLayout.vue'
import NoSidebarLayout from './components/NoSidebarLayout.vue'
import InstallPrompt from './components/InstallPrompt.vue'

const { isMobile } = useScreenSize()
const router = useRouter()
const noSidebar = ref(false)
const { userResource } = usersStore()
const { settings } = useSettings()

router.beforeEach((to, from, next) => {
	if (to.query.fromLesson || to.path === '/persona') {
		noSidebar.value = true
	} else {
		noSidebar.value = false
	}
	next()
})

const Layout = computed(() => {
	if (noSidebar.value) {
		return NoSidebarLayout
	}
	if (isMobile.value) {
		return MobileLayout
	}
	return DesktopLayout
})

// Global Security Feature: Right-Click Prevention
const handleContextMenu = (event) => {
	event.preventDefault()
	return false
}

// Global Security Feature: Developer Tools Prevention
const handleKeyDown = (event) => {
	// Block F12 (open dev tools)
	if (event.key === 'F12') {
		event.preventDefault()
		return false
	}

	// Block Ctrl+Shift+I (Inspect Element)
	if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'I') {
		event.preventDefault()
		return false
	}

	// Block Ctrl+Shift+C (Inspect Element - Chrome)
	if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'C') {
		event.preventDefault()
		return false
	}

	// Block Ctrl+Shift+J (Console)
	if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'J') {
		event.preventDefault()
		return false
	}

	// Block Ctrl+Shift+K (Console - Firefox)
	if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'K') {
		event.preventDefault()
		return false
	}
}

// Setup global security event listeners on mount
onMounted(() => {
	document.addEventListener('keydown', handleKeyDown, true)
	document.addEventListener('contextmenu', handleContextMenu, true)

	// Additional DevTools detection - check if console is open
	// This is a basic check; advanced users can still bypass this
	const detectDevTools = () => {
		const start = performance.now()
		debugger
		const end = performance.now()

		if (end - start > 100) {
			console.clear()
		}
	}

	// Run detection every 2 seconds
	const devToolsInterval = setInterval(detectDevTools, 2000)

	// Cleanup on unmount
	onUnmounted(() => {
		document.removeEventListener('keydown', handleKeyDown, true)
		document.removeEventListener('contextmenu', handleContextMenu, true)
		clearInterval(devToolsInterval)
		noSidebar.value = false
	})
})

watch(userResource, () => {
	if (userResource.data) {
		posthogSettings.reload()
	}
})
</script>

<style scoped>
/* Global Security: Disable text selection across entire LMS */
.lms-app-container {
	user-select: none;
	-webkit-user-select: none;
	-moz-user-select: none;
	-ms-user-select: none;
}

/* Prevent drag selection of text */
.lms-app-container ::selection {
	background: transparent;
	color: inherit;
}

.lms-app-container ::-moz-selection {
	background: transparent;
	color: inherit;
}
</style>
