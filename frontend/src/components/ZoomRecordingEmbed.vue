<template>
	<div class="zoom-recording-container">
		<div v-if="loading" class="flex items-center justify-center p-10">
			<span class="text-ink-gray-7">{{ __('Loading recording...') }}</span>
		</div>
		<div v-else-if="processing" class="text-center p-10">
			<div class="text-ink-gray-7 mb-2 font-medium">
				{{ __('Recording is being processed...') }}
			</div>
			<div class="text-sm text-ink-gray-5 mb-4">
				{{ processingMessage || __('Please check back in a few minutes.') }}
			</div>
			<Button @click="retryLoad" variant="outline" size="sm">
				{{ __('Check Again') }}
			</Button>
		</div>
		<div v-else-if="error" class="text-center p-10">
			<div class="text-ink-red-3 mb-2">{{ error }}</div>
			<Button v-if="!loading" @click="retryLoad" variant="outline" size="sm">
				{{ __('Retry') }}
			</Button>
		</div>
		<div v-else-if="recordingToken" class="relative w-full bg-black rounded-md overflow-hidden zoom-recording-container" style="padding-bottom: 56.25%; height: 0; user-select: none;" @contextmenu.prevent>
			<!-- Secure proxy iframe - URL is never exposed to frontend -->
			<iframe
				:src="`/api/method/lms.lms.api.get_recording_secure?token=${recordingToken}&live_class=${liveClassId}`"
				class="absolute top-0 left-0 w-full h-full border-0"
				frameborder="0"
				sandbox="allow-scripts allow-same-origin allow-presentation"
				allowfullscreen
				allow="autoplay; encrypted-media; fullscreen; picture-in-picture"
				:title="recordingTitle || __('Zoom Recording')"
				@load="onIframeLoad"
				@error="onIframeError"
				referrerpolicy="no-referrer"
				controlsList="nodownload"
			></iframe>
			<div v-if="iframeLoading" class="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 z-10">
				<span class="text-white text-sm">{{ __('Loading video player...') }}</span>
			</div>
		</div>
		<div v-else class="text-center p-10 text-ink-gray-5">
			{{ __('Recording not available') }}
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { call, Button } from 'frappe-ui'

const props = defineProps({
	liveClassId: {
		type: String,
		required: true
	}
})

const loading = ref(true)
const recordingToken = ref(null)
const error = ref(null)
const recordingTitle = ref(null)
const iframeLoading = ref(true)
const processing = ref(false)
const processingMessage = ref(null)
let retryTimeout = null

const loadRecording = async () => {
	try {
		loading.value = true
		error.value = null
		processing.value = false
		processingMessage.value = null
		iframeLoading.value = true
		recordingToken.value = null

		// Clear any existing retry timeout
		if (retryTimeout) {
			clearTimeout(retryTimeout)
			retryTimeout = null
		}

		// Get secure token from backend (NOT the actual Zoom URL)
		// Token is used to request recording from backend proxy
		// Access control verified on every request, so no expiration needed
		const data = await call('lms.lms.api.get_recording_embed_url', {
			live_class: props.liveClassId
		})

		console.log('[ZoomRecordingEmbed] API response:', data)

		if (data.token && data.recording_available) {
			// Token identifies this viewing session
			recordingToken.value = data.token
			recordingTitle.value = data.title || null
			processing.value = false
		} else if (data.status === "processing" || data.status === "error" || (!data.recording_available && !data.token)) {
			// Recording is still being processed or has an error
			processing.value = true
			processingMessage.value = data.message || __('Recording is being processed. Please check back in a few minutes.')

			// Auto-retry after 2 minutes (only if processing, not if error)
			if (data.status !== "error") {
				retryTimeout = setTimeout(() => {
					if (processing.value) {
						loadRecording()
					}
				}, 120000) // 2 minutes
			}
		} else {
			error.value = data.message || __('Recording not found')
		}
	} catch (err) {
		console.error('Error loading recording:', err)

		// Check if error indicates processing (only retry for processing, not actual errors)
		const errorMessage = err.messages?.[0] || err.message || ''
		if (errorMessage.includes('processed') || errorMessage.includes('processing')) {
			processing.value = true
			processingMessage.value = errorMessage

			// Auto-retry after 2 minutes (only for processing status)
			retryTimeout = setTimeout(() => {
				if (processing.value) {
					loadRecording()
				}
			}, 120000) // 2 minutes
		} else {
			// Actual error - don't auto-retry
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
}

const onIframeError = () => {
	iframeLoading.value = false
	// Check if iframe loaded but content might have error
	setTimeout(() => {
		// If iframe is still showing loading after 5 seconds, might be an issue
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
.zoom-recording-container {
	user-select: none;
	-webkit-user-select: none;
	-moz-user-select: none;
	-ms-user-select: none;
}
</style>
