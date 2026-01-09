<template>
	<div class="vimeo-recording-container">
		<div v-if="loading" class="flex items-center justify-center p-10">
			<div class="flex flex-col items-center space-y-2">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
				<span class="text-ink-gray-7">{{ __('Loading recording...') }}</span>
			</div>
		</div>
		<div v-else-if="processing" class="text-center p-10 bg-surface-gray-2 rounded-lg">
			<div class="flex flex-col items-center space-y-3">
				<div class="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
					<svg class="w-6 h-6 text-blue-600 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
					</svg>
				</div>
				<div class="text-ink-gray-7 font-medium">
					{{ __('Recording is being processed...') }}
				</div>
				<div class="text-sm text-ink-gray-5 max-w-md">
					{{ processingMessage || __('Your recording is being uploaded and processed. This usually takes a few minutes.') }}
				</div>
				<div v-if="vimeoStatus" class="text-xs text-ink-gray-4 mt-2">
					{{ __('Status') }}: {{ vimeoStatus }}
				</div>
				<Button @click="retryLoad" variant="outline" size="sm" class="mt-4">
					<template #prefix>
						<RefreshCw class="w-4 h-4" />
					</template>
					{{ __('Check Again') }}
				</Button>
			</div>
		</div>
		<div v-else-if="error" class="text-center p-10 bg-red-50 rounded-lg">
			<div class="flex flex-col items-center space-y-3">
				<div class="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
					<svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
				</div>
				<div class="text-ink-red-3 font-medium">{{ __('Recording Unavailable') }}</div>
				<div class="text-sm text-ink-gray-5">{{ error }}</div>
				<Button v-if="!loading" @click="retryLoad" variant="outline" size="sm" class="mt-2">
					<template #prefix>
						<RefreshCw class="w-4 h-4" />
					</template>
					{{ __('Retry') }}
				</Button>
			</div>
		</div>
		<div
			v-else-if="embedUrl"
			class="relative w-full bg-black rounded-lg overflow-hidden vimeo-player-container"
			style="padding-bottom: 56.25%; height: 0; user-select: none;"
			@contextmenu.prevent
			@dragstart.prevent
			@drop.prevent
		>
			<!-- Vimeo Player iframe -->
			<iframe
				:src="embedUrl"
				class="absolute top-0 left-0 w-full h-full border-0"
				frameborder="0"
				allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media"
				allowfullscreen
				:title="recordingTitle || __('Vimeo Recording')"
				@load="onIframeLoad"
				@error="onIframeError"
				referrerpolicy="strict-origin-when-cross-origin"
			></iframe>
			<div v-if="iframeLoading" class="absolute inset-0 flex items-center justify-center bg-black bg-opacity-70 z-10">
				<div class="flex flex-col items-center space-y-2">
					<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
					<span class="text-white text-sm">{{ __('Loading video player...') }}</span>
				</div>
			</div>
		</div>
		<div v-else class="text-center p-10 bg-surface-gray-2 rounded-lg">
			<div class="flex flex-col items-center space-y-3">
				<div class="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
					<svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
					</svg>
				</div>
				<div class="text-ink-gray-5">{{ __('Recording not available') }}</div>
			</div>
		</div>

		<!-- Recording Info -->
		<div v-if="embedUrl && (recordingTitle || recordingDescription)" class="mt-4 p-4 bg-surface-gray-2 rounded-lg">
			<h3 v-if="recordingTitle" class="font-semibold text-ink-gray-9">{{ recordingTitle }}</h3>
			<p v-if="recordingDescription" class="text-sm text-ink-gray-6 mt-1">{{ recordingDescription }}</p>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { call, Button } from 'frappe-ui'
import { RefreshCw } from 'lucide-vue-next'

const props = defineProps({
	liveClassId: {
		type: String,
		required: true
	}
})

const loading = ref(true)
const embedUrl = ref(null)
const error = ref(null)
const recordingTitle = ref(null)
const recordingDescription = ref(null)
const iframeLoading = ref(true)
const processing = ref(false)
const processingMessage = ref(null)
const vimeoStatus = ref(null)
let retryTimeout = null

const loadRecording = async () => {
	try {
		loading.value = true
		error.value = null
		processing.value = false
		processingMessage.value = null
		vimeoStatus.value = null
		iframeLoading.value = true
		embedUrl.value = null

		// Clear any existing retry timeout
		if (retryTimeout) {
			clearTimeout(retryTimeout)
			retryTimeout = null
		}

		console.log('[VimeoRecordingEmbed] Loading recording for:', props.liveClassId)

		// Get Vimeo embed URL from backend
		const data = await call('lms.lms.api.get_vimeo_embed_url', {
			live_class: props.liveClassId
		})

		console.log('[VimeoRecordingEmbed] API response:', data)

		if (data.embed_url && data.recording_available) {
			// Recording is ready
			embedUrl.value = data.embed_url
			recordingTitle.value = data.title || null
			recordingDescription.value = data.description || null
			processing.value = false
		} else if (data.status === "processing" || data.vimeo_status) {
			// Recording is still being processed
			processing.value = true
			vimeoStatus.value = data.vimeo_status || 'processing'
			processingMessage.value = data.message || __('Recording is being processed. Please check back in a few minutes.')
			recordingTitle.value = data.title || null
			recordingDescription.value = data.description || null

			// Auto-retry after 2 minutes
			retryTimeout = setTimeout(() => {
				if (processing.value) {
					loadRecording()
				}
			}, 120000) // 2 minutes
		} else if (data.status === "error") {
			error.value = data.message || __('Recording upload failed')
			processing.value = false
		} else if (data.status === "not_available") {
			error.value = data.message || __('Recording not available')
			processing.value = false
		} else {
			error.value = data.message || __('Recording not found')
		}
	} catch (err) {
		console.error('[VimeoRecordingEmbed] Error loading recording:', err)

		const errorMessage = err.messages?.[0] || err.message || ''

		// Check if error indicates processing
		if (errorMessage.includes('processed') || errorMessage.includes('processing')) {
			processing.value = true
			processingMessage.value = errorMessage

			// Auto-retry after 2 minutes
			retryTimeout = setTimeout(() => {
				if (processing.value) {
					loadRecording()
				}
			}, 120000)
		} else {
			error.value = errorMessage || __('Failed to load recording')
			processing.value = false
		}
	} finally {
		loading.value = false
	}
}

const retryLoad = () => {
	// Clear any existing timeout
	if (retryTimeout) {
		clearTimeout(retryTimeout)
		retryTimeout = null
	}
	loadRecording()
}

const onIframeLoad = () => {
	iframeLoading.value = false
	console.log('[VimeoRecordingEmbed] Iframe loaded successfully')
}

const onIframeError = () => {
	iframeLoading.value = false
	console.error('[VimeoRecordingEmbed] Iframe load error')
	// Set a timeout to check if iframe is still having issues
	setTimeout(() => {
		if (iframeLoading.value) {
			iframeLoading.value = false
		}
	}, 5000)
}

onMounted(() => {
	loadRecording()
})

onBeforeUnmount(() => {
	// Clean up retry timeout when component is unmounted
	if (retryTimeout) {
		clearTimeout(retryTimeout)
		retryTimeout = null
	}
})
</script>

<style scoped>
.vimeo-recording-container {
	user-select: none;
	-webkit-user-select: none;
	-moz-user-select: none;
	-ms-user-select: none;
}

.vimeo-player-container {
	/* Prevent text selection on the video container */
	user-select: none;
	-webkit-user-select: none;
	-moz-user-select: none;
	-ms-user-select: none;
}

/* Hide Vimeo branding elements via CSS (backup) */
.vimeo-player-container iframe {
	pointer-events: auto;
}
</style>
