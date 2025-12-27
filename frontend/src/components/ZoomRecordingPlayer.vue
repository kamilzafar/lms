<template>
	<div class="zoom-recording-container">
		<!-- Recording Available Badge -->
		<div
			v-if="!showPlayer && hasRecording"
			class="bg-surface-blue-1 border border-outline-blue-3 rounded-md p-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center space-x-3">
					<div class="bg-surface-blue-3 rounded-full p-2">
						<Video class="size-5 text-ink-blue-7" />
					</div>
					<div>
						<div class="font-semibold text-ink-gray-9">
							{{ __('Live Class Recording Available') }}
						</div>
						<div class="text-sm text-ink-gray-7 mt-1">
							{{ formatDuration(recordingDuration) }}
						</div>
					</div>
				</div>
				<Button @click="loadRecording" variant="solid" :loading="loading">
					<template #prefix>
						<Play class="size-4" />
					</template>
					{{ __('Watch Recording') }}
				</Button>
			</div>
		</div>

		<!-- Zoom Player Iframe -->
		<div v-if="showPlayer" class="zoom-player-wrapper mb-6">
			<div class="relative rounded-md overflow-hidden border border-gray-200">
				<iframe
					:src="playerUrl"
					class="w-full"
					style="min-height: 500px; height: 60vh"
					frameborder="0"
					allow="autoplay; fullscreen; picture-in-picture"
					allowfullscreen
				></iframe>

				<!-- Close Player Button -->
				<Button
					@click="closePlayer"
					variant="ghost"
					class="absolute top-2 right-2 bg-black/50 hover:bg-black/70 text-white"
				>
					<template #icon>
						<X class="size-4" />
					</template>
				</Button>
			</div>

			<!-- Recording Info -->
			<div
				class="mt-2 text-sm text-ink-gray-6 flex items-center justify-between"
			>
				<span>
					{{ __('Duration:') }} {{ formatDuration(recordingDuration) }}
				</span>
				<span v-if="fileSize" class="text-xs">
					{{ __('Size:') }} {{ formatFileSize(fileSize) }}
				</span>
			</div>
		</div>

		<!-- Error State -->
		<div
			v-if="errorMessage"
			class="bg-surface-red-1 border border-outline-red-3 rounded-md p-4 mb-6"
		>
			<div class="flex items-center space-x-2">
				<AlertCircle class="size-5 text-ink-red-7" />
				<div class="text-ink-red-9">{{ errorMessage }}</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Button, call } from 'frappe-ui'
import { Video, Play, X, AlertCircle } from 'lucide-vue-next'

const props = defineProps({
	liveClassName: {
		type: String,
		required: true,
	},
	recordingDuration: {
		type: Number,
		default: 0,
	},
	hasRecording: {
		type: Boolean,
		default: false,
	},
})

const showPlayer = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const playUrl = ref('')
const passcode = ref('')
const fileSize = ref(0)

const playerUrl = computed(() => {
	if (!playUrl.value) return ''

	// Construct Zoom player URL with passcode
	let url = playUrl.value
	if (passcode.value) {
		// Append passcode as query parameter (Zoom format)
		const separator = url.includes('?') ? '&' : '?'
		url = `${url}${separator}pwd=${passcode.value}`
	}
	return url
})

const loadRecording = async () => {
	loading.value = true
	errorMessage.value = ''

	try {
		const result = await call('lms.lms.api.get_zoom_recording_playback', {
			live_class_name: props.liveClassName,
		})

		if (!result.has_access) {
			errorMessage.value =
				result.message || 'You do not have access to this recording'
			return
		}

		playUrl.value = result.play_url
		passcode.value = result.passcode
		fileSize.value = result.file_size
		showPlayer.value = true
	} catch (error) {
		errorMessage.value =
			error.message || 'Failed to load recording. Please try again.'
		console.error('Error loading Zoom recording:', error)
	} finally {
		loading.value = false
	}
}

const closePlayer = () => {
	showPlayer.value = false
	playUrl.value = ''
	passcode.value = ''
}

const formatDuration = (seconds) => {
	if (!seconds) return '0:00'
	const hours = Math.floor(seconds / 3600)
	const minutes = Math.floor((seconds % 3600) / 60)
	const secs = seconds % 60

	if (hours > 0) {
		return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
	}
	return `${minutes}:${String(secs).padStart(2, '0')}`
}

const formatFileSize = (bytes) => {
	if (!bytes) return ''
	const mb = bytes / (1024 * 1024)
	if (mb > 1024) {
		return `${(mb / 1024).toFixed(1)} GB`
	}
	return `${mb.toFixed(1)} MB`
}
</script>

<style scoped>
.zoom-player-wrapper {
	position: relative;
}

iframe {
	display: block;
	background: #000;
}
</style>
