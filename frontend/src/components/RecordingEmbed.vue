<template>
	<div class="recording-embed-container">
		<!-- Loading state while determining which player to use -->
		<div v-if="loading" class="flex items-center justify-center p-10">
			<div class="flex flex-col items-center space-y-2">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
				<span class="text-ink-gray-7">{{ __('Loading recording...') }}</span>
			</div>
		</div>

		<!-- Vimeo Player (when Vimeo is configured and video is uploaded) -->
		<VimeoRecordingEmbed
			v-else-if="useVimeo"
			:liveClassId="liveClassId"
		/>

		<!-- Zoom Player (fallback when Vimeo is not configured) -->
		<ZoomRecordingEmbed
			v-else
			:liveClassId="liveClassId"
		/>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { call } from 'frappe-ui'
import VimeoRecordingEmbed from '@/components/VimeoRecordingEmbed.vue'
import ZoomRecordingEmbed from '@/components/ZoomRecordingEmbed.vue'

const props = defineProps({
	liveClassId: {
		type: String,
		required: true
	}
})

const loading = ref(true)
const useVimeo = ref(false)

const determinePlayer = async () => {
	try {
		loading.value = true

		// Check if this live class has a Vimeo video
		const response = await call('lms.lms.api.get_recording_type', {
			live_class: props.liveClassId
		})

		console.log('[RecordingEmbed] Recording type check:', response)

		// Use Vimeo if video is uploaded to Vimeo (has URI and not in error state)
		if (response && response.has_vimeo && response.vimeo_status !== 'error') {
			useVimeo.value = true
			console.log('[RecordingEmbed] Using Vimeo player')
		} else {
			useVimeo.value = false
			console.log('[RecordingEmbed] Using Zoom player')
		}
	} catch (err) {
		console.error('[RecordingEmbed] Error determining player:', err)
		// Default to Zoom on error
		useVimeo.value = false
	} finally {
		loading.value = false
	}
}

onMounted(() => {
	determinePlayer()
})
</script>

<style scoped>
.recording-embed-container {
	width: 100%;
}
</style>
