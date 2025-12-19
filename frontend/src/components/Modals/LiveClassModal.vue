<template>
	<Dialog
		v-model="show"
		:options="{
			title: __('Create a Live Class'),
			size: 'xl',
			actions: [
				{
					label: 'Submit',
					variant: 'solid',
					onClick: ({ close }) => submitLiveClass(close),
				},
			],
		}"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<div class="grid grid-cols-2 gap-4">
					<div class="space-y-4">
						<FormControl
							type="text"
							v-model="liveClass.title"
							:label="__('Title')"
							:required="true"
						/>
						<FormControl
							v-model="liveClass.date"
							type="date"
							:label="__('Date')"
							:required="true"
						/>
						<Tooltip :text="__('Duration of the live class in minutes')">
							<FormControl
								type="number"
								v-model="liveClass.duration"
								:label="__('Duration')"
								:required="true"
							/>
						</Tooltip>
					</div>
					<div class="space-y-4">
						<Tooltip
							:text="
								__(
									'Time must be in 24 hour format (HH:mm). Example 11:30 or 22:00'
								)
							"
						>
							<FormControl
								v-model="liveClass.time"
								type="time"
								:label="__('Time')"
								:required="true"
							/>
						</Tooltip>

						<div class="space-y-1.5">
							<label class="block text-ink-gray-5 text-xs" for="batchTimezone">
								{{ __('Timezone') }}
								<span class="text-ink-red-3">*</span>
							</label>
							<Autocomplete
								:modelValue="liveClass.timezone || ''"
								@update:modelValue="(value) => { 
									liveClass.timezone = typeof value === 'object' && value !== null ? (value?.value || value) : (value || 'UTC')
								}"
								:options="getTimezoneOptions()"
								:required="true"
							/>
						</div>
						<FormControl
							v-model="liveClass.auto_recording"
							type="select"
							:options="getRecordingOptions()"
							:label="__('Auto Recording')"
						/>
					</div>
				</div>
				<FormControl
					v-model="liveClass.description"
					type="textarea"
					:label="__('Description')"
				/>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Dialog,
	createResource,
	Tooltip,
	FormControl,
	Autocomplete,
	toast,
} from 'frappe-ui'
import { reactive, inject, onMounted } from 'vue'
import { getTimezones, getUserTimezone } from '@/utils/'

const liveClasses = defineModel('reloadLiveClasses')
const show = defineModel()
const user = inject('$user')
const dayjs = inject('$dayjs')

const props = defineProps({
	batch: {
		type: String,
		required: true,
	},
	zoomAccount: {
		type: String,
		required: true,
	},
})

let liveClass = reactive({
	title: '',
	description: '',
	date: '',
	time: '',
	duration: '',
	timezone: '',
	auto_recording: 'No Recording',
	batch: props.batch,
	host: user.data.name,
})

onMounted(() => {
	const userTimezone = getUserTimezone()
	liveClass.timezone = userTimezone || 'UTC'  // Fallback to UTC if null
})

const getTimezoneOptions = () => {
	return getTimezones().map((timezone) => {
		return {
			label: timezone,
			value: timezone,
		}
	})
}

const getRecordingOptions = () => {
	return [
		{
			label: 'No Recording',
			value: 'No Recording',
		},
		{
			label: 'Local',
			value: 'Local',
		},
		{
			label: 'Cloud',
			value: 'Cloud',
		},
	]
}

const createLiveClass = createResource({
	url: 'lms.lms.doctype.lms_batch.lms_batch.create_live_class',
	makeParams(values) {
		// Remove doctype from params - it's not needed
		const { doctype, ...rest } = values
		return {
			batch_name: rest.batch,
			zoom_account: props.zoomAccount,
			...rest,
		}
	},
})

const submitLiveClass = (close) => {
	return createLiveClass.submit(liveClass, {
		validate() {
			validateFormFields()
		},
		onSuccess() {
			liveClasses.value.reload()
			refreshForm()
			close()
		},
		onError(err) {
			toast.error(err.messages?.[0] || err)
		},
	})
}

const validateFormFields = () => {
	if (!liveClass.title || !liveClass.title.trim()) {
		return __('Please enter a title.')
	}
	if (!liveClass.date || !liveClass.date.trim()) {
		return __('Please select a date.')
	}
	if (!liveClass.time || !liveClass.time.trim()) {
		return __('Please select a time.')
	}
	if (!liveClass.timezone || !liveClass.timezone.trim()) {
		return __('Please select a timezone.')
	}
	if (!valideTime()) {
		return __('Please enter a valid time in the format HH:mm.')
	}
	
	try {
		const liveClassDateTime = dayjs(`${liveClass.date}T${liveClass.time}`).tz(
			liveClass.timezone,
			true
		)
		if (!liveClassDateTime.isValid()) {
			return __('Invalid date or time. Please check your inputs.')
		}
		if (
			liveClassDateTime.isSameOrBefore(
				dayjs().tz(liveClass.timezone, false),
				'minute'
			)
		) {
			return __('Please select a future date and time.')
		}
	} catch (error) {
		return __('Error validating date/time. Please check your timezone selection.')
	}
	
	if (!liveClass.duration || liveClass.duration <= 0) {
		return __('Please enter a valid duration (greater than 0).')
	}
}

const valideTime = () => {
	if (!liveClass.time) {
		return false
	}
	let time = liveClass.time.split(':')
	if (time.length != 2) {
		return false
	}
	const hours = parseInt(time[0], 10)
	const minutes = parseInt(time[1], 10)
	
	if (isNaN(hours) || isNaN(minutes)) {
		return false
	}
	if (hours < 0 || hours > 23) {
		return false
	}
	if (minutes < 0 || minutes > 59) {
		return false
	}
	return true
}

const refreshForm = () => {
	liveClass.title = ''
	liveClass.description = ''
	liveClass.date = ''
	liveClass.time = ''
	liveClass.duration = ''
	liveClass.timezone = getUserTimezone() || 'UTC'  // Fallback to UTC
	liveClass.auto_recording = 'No Recording'
}
</script>
