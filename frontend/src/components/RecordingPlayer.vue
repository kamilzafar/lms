<template>
	<div class="recording-player-container">
		<!-- Recording Info Header -->
		<div class="recording-header bg-gray-50 border-b p-4">
			<div class="flex items-start justify-between">
				<div class="flex-1">
					<h2 class="text-lg font-semibold text-ink-gray-9">
						{{ recording.title }}
					</h2>
					<div class="flex items-center gap-3 mt-2 text-sm text-ink-gray-6">
						<div class="flex items-center gap-1">
							<Icon icon="calendar" size="16" />
							{{ formatDate(recording.date) }}
						</div>
						<div class="flex items-center gap-1">
							<Icon icon="clock" size="16" />
							{{ recording.duration }} {{ __('minutes') }}
						</div>
					</div>
				</div>
				<div class="flex items-center gap-2">
					<Badge v-if="recording.recording_available" variant="success" size="sm">
						{{ __('Available') }}
					</Badge>
					<Badge v-else variant="outline" size="sm">
						{{ __('Processing') }}
					</Badge>
				</div>
			</div>
		</div>

		<!-- Recording Description -->
		<div v-if="recording.description" class="recording-description bg-white p-4 border-b">
			<p class="text-ink-gray-7 text-sm leading-relaxed">
				{{ recording.description }}
			</p>
		</div>

		<!-- Recording Player -->
		<div class="recording-player-wrapper bg-black">
			<!-- Loading State -->
			<div v-if="loading" class="flex items-center justify-center p-20">
				<div class="text-center">
					<div class="mb-4">
						<Icon icon="loader" size="32" class="text-white animate-spin" />
					</div>
					<p class="text-white">{{ __('Loading recording...') }}</p>
				</div>
			</div>

			<!-- Processing State -->
			<div v-else-if="processing" class="flex items-center justify-center p-20">
				<div class="text-center">
					<div class="mb-4">
						<Icon icon="hourglass" size="32" class="text-white" />
					</div>
					<p class="text-white font-semibold mb-2">
						{{ __('Recording is being processed...') }}
					</p>
					<p class="text-gray-300 text-sm mb-4">
						{{ processingMessage || __('Your recording is being prepared. Please check back in a few minutes.') }}
					</p>
					<Button @click="retryLoad" variant="solid" size="sm">
						{{ __('Check Again') }}
					</Button>
				</div>
			</div>

			<!-- Error State -->
			<div v-else-if="error" class="flex items-center justify-center p-20">
				<div class="text-center">
					<div class="mb-4">
						<Icon icon="alert-circle" size="32" class="text-red-400" />
					</div>
					<p class="text-white font-semibold mb-2">
						{{ __('Unable to load recording') }}
					</p>
					<p class="text-gray-300 text-sm mb-4">
						{{ error }}
					</p>
					<Button @click="retryLoad" variant="solid" size="sm">
						{{ __('Try Again') }}
					</Button>
				</div>
			</div>

			<!-- Recording Player Iframe -->
			<div v-else-if="recordingToken" class="recording-iframe-container">
				<iframe
					:src="`/api/method/lms.lms.api.get_recording_secure?token=${recordingToken}&live_class=${recording.name}`"
					class="recording-iframe"
					frameborder="0"
					allowfullscreen="true"
					allow="autoplay; encrypted-media; fullscreen; picture-in-picture; microphone; camera"
					:title="recording.title"
					referrerpolicy="no-referrer-when-downgrade">
				</iframe>
				<!-- Loading overlay for iframe -->
				<div v-if="iframeLoading" class="iframe-loading-overlay">
					<div class="flex items-center justify-center h-full">
						<div class="text-center">
							<Icon icon="loader" size="24" class="text-white animate-spin mb-2" />
							<p class="text-white text-sm">{{ __('Loading video player...') }}</p>
						</div>
					</div>
				</div>
			</div>

			<!-- Not Available State -->
			<div v-else class="flex items-center justify-center p-20">
				<div class="text-center">
					<Icon icon="video-off" size="32" class="text-gray-500 mb-4" />
					<p class="text-gray-400">{{ __('Recording not available') }}</p>
				</div>
			</div>
		</div>

		<!-- Recording Info Footer -->
		<div class="recording-footer bg-gray-50 border-t p-4">
			<div class="flex items-center justify-between text-sm text-ink-gray-6">
				<div>
					<span v-if="lastAccessTime" class="flex items-center gap-2">
						<Icon icon="check-circle-2" size="16" class="text-green-600" />
						{{ __('Last accessed') }}: {{ formatTime(lastAccessTime) }}
					</span>
				</div>
				<div class="text-xs text-ink-gray-5">
					{{ __('Access is logged for compliance and security') }}
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { call, Button, Badge, Icon } from 'frappe-ui'
import { formatDate, formatTime } from '@/utils'

const props = defineProps({
	recording: {
		type: Object,
		required: true,
		validator: (obj) => obj.name && obj.title
	}
})

const loading = ref(true)
const recordingToken = ref(null)
const error = ref(null)
const iframeLoading = ref(true)
const processing = ref(false)
const processingMessage = ref(null)
const lastAccessTime = ref(null)

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
		const data = await call('lms.lms.api.get_recording_embed_url', {
			live_class: props.recording.name
		})

		console.log('[RecordingPlayer] API response:', data)

		if (data.token && data.recording_available) {
			// Token identifies this viewing session
			recordingToken.value = data.token
			lastAccessTime.value = new Date().toISOString()
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
	if (retryTimeout) {
		clearTimeout(retryTimeout)
		retryTimeout = null
	}
	loadRecording()
}

onMounted(() => {
	loadRecording()
})

onBeforeUnmount(() => {
	if (retryTimeout) {
		clearTimeout(retryTimeout)
		retryTimeout = null
	}
})
</script>

<style scoped>
.recording-player-container {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: white;
	border-radius: 0.5rem;
	overflow: hidden;
}

.recording-header {
	flex-shrink: 0;
}

.recording-description {
	flex-shrink: 0;
	max-height: 120px;
	overflow-y: auto;
}

.recording-player-wrapper {
	flex: 1;
	display: flex;
	align-items: center;
	justify-content: center;
	min-height: 400px;
	position: relative;
	background-color: #000;
}

.recording-iframe-container {
	width: 100%;
	height: 100%;
	position: relative;
	padding-bottom: 56.25%;
	/* 16:9 aspect ratio */
	height: 0;
	overflow: hidden;
}

.recording-iframe {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	border: none;
}

.iframe-loading-overlay {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	background-color: rgba(0, 0, 0, 0.7);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 10;
}

.recording-footer {
	flex-shrink: 0;
}

@media (max-width: 768px) {
	.recording-player-wrapper {
		min-height: 300px;
	}

	.recording-header {
		padding: 3rem 1rem;
	}

	.recording-header h2 {
		font-size: 1.125rem;
	}
}
</style>
