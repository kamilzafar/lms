<template>
	<header
		class="sticky flex items-center justify-between top-0 z-10 border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />

		<Dropdown
			placement="start"
			side="bottom"
			v-if="canCreateCourse()"
			:options="[
				{
					label: __('New Course'),
					icon: 'book-open',
					onClick() {
						router.push({
							name: 'CourseForm',
							params: { courseName: 'new' },
						})
					},
				},
				{
					label: __('Import Course'),
					icon: 'upload',
					onClick() {
						router.push({
							name: 'NewDataImport',
							params: { doctype: 'LMS Course' },
						})
					},
				},
			]"
		>
			<template v-slot="{ open }">
				<Button variant="solid">
					<template #prefix>
						<Plus class="h-4 w-4 stroke-1.5" />
					</template>
					{{ __('Create') }}
					<template #suffix>
						<ChevronDown
							:class="[
								'w-4 h-4 stroke-1.5 ml-1 transform transition-transform',
								open ? 'rotate-180' : '',
							]"
						/>
					</template>
				</Button>
			</template>
		</Dropdown>
	</header>
	<div class="p-5 pb-10">
		<div
			class="flex flex-col lg:flex-row space-y-4 lg:space-y-0 lg:items-center justify-between mb-5"
		>
			<div class="text-lg text-ink-gray-9 font-semibold">
				{{ __('All Courses') }}
			</div>
			<div
				class="flex flex-col space-y-3 lg:space-y-0 lg:flex-row lg:items-center lg:space-x-4"
			>
				<TabButtons :buttons="courseTabs" v-model="currentTab" class="w-fit" />

				<div class="grid grid-cols-2 gap-2">
					<FormControl
						v-model="title"
						:placeholder="__('Search by Title')"
						type="text"
						class="w-full lg:min-w-0 lg:w-32 xl:w-40"
						@input="updateCourses()"
					/>
					<div class="w-full lg:min-w-0 lg:w-32 xl:w-40">
						<Select
							v-if="categories.length"
							v-model="currentCategory"
							:options="categories"
							:placeholder="__('Category')"
							@update:modelValue="updateCourses()"
						/>
					</div>
				</div>

				<FormControl
					v-model="certification"
					:label="__('Certification')"
					type="checkbox"
					@change="updateCourses()"
				/>
			</div>
		</div>
		<!-- Recorded Lectures Section (only for Recorded tab) -->
		<div v-if="currentTab === 'Recorded' && recordedLectures.data?.length" class="mb-10">
			<div class="text-lg font-semibold text-ink-gray-9 mb-5">
				{{ __('Recorded Lectures') }}
			</div>
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
				<div
					v-for="lecture in recordedLectures.data"
					:key="lecture.name"
					class="border rounded-md p-4 hover:border-outline-gray-3 cursor-pointer transition-colors"
					@click="openRecordingModal(lecture)"
				>
					<div class="font-semibold text-ink-gray-9 mb-2">{{ lecture.title }}</div>
					<div class="text-sm text-ink-gray-7 mb-2">{{ lecture.course_title }}</div>
					<div class="text-xs text-ink-gray-5">
						{{ dayjs(lecture.date).format('DD MMM YYYY') }}
					</div>
				</div>
			</div>
		</div>

		<!-- Courses Section -->
		<div
			v-if="courses.data?.length && currentTab !== 'Recorded'"
			class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-8"
		>
			<router-link
				v-for="course in courses.data"
				:to="{ name: 'CourseDetail', params: { courseName: course.name } }"
			>
				<CourseCard :course="course" />
			</router-link>
		</div>
		<EmptyState v-else-if="!courses.list.loading && currentTab !== 'Recorded'" type="Courses" />
		<EmptyState v-else-if="currentTab === 'Recorded' && !recordedLectures.list.loading && !recordedLectures.data?.length" type="Courses" />
		<div
			v-if="!courses.list.loading && courses.hasNextPage && currentTab !== 'Recorded'"
			class="flex justify-center mt-5"
		>
			<Button @click="courses.next()">
				{{ __('Load More') }}
			</Button>
		</div>
	</div>

	<!-- Recording Modal -->
	<Dialog
		v-model="showRecordingModal"
		:options="{
			title: currentRecording?.title || __('Recorded Lecture'),
			size: 'xl',
		}"
	>
		<template #body-content>
			<div v-if="currentRecording" class="p-4">
				<div v-if="currentRecording.description" class="mb-4 text-ink-gray-7">
					{{ currentRecording.description }}
				</div>
				<ZoomRecordingEmbed :liveClassId="currentRecording.name" />
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Breadcrumbs,
	Button,
	call,
	createListResource,
	Dialog,
	Dropdown,
	FormControl,
	Select,
	TabButtons,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { ChevronDown, Plus } from 'lucide-vue-next'
import { sessionStore } from '@/stores/session'
import { canCreateCourse } from '@/utils'
import CourseCard from '@/components/CourseCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import ZoomRecordingEmbed from '@/components/ZoomRecordingEmbed.vue'
import router from '../router'

const user = inject('$user')
const dayjs = inject('$dayjs')
const start = ref(0)
const pageLength = ref(30)
const categories = ref([])
const currentCategory = ref(null)
const title = ref('')
const certification = ref(false)
const filters = ref({})
const currentTab = ref('Live')
const { brand } = sessionStore()
const courseCount = ref(0)
const showRecordingModal = ref(false)
const currentRecording = ref(null)

const recordedLectures = createListResource({
	doctype: 'LMS Live Class',
	url: 'lms.lms.api.get_recorded_lectures',
	auto: false,
})

onMounted(() => {
	// Set default tab based on user role
	const isStudent = user.data && 
		!(user.data?.is_moderator || user.data?.is_instructor || user.data?.is_evaluator)
	const isInstructorOrModerator = user.data && 
		(user.data?.is_moderator || user.data?.is_instructor || user.data?.is_evaluator) &&
		!user.data?.is_system_manager
	const isAdmin = user.data?.is_system_manager
	
	if (isStudent) {
		// Students can access Enrolled, Live, and Recorded tabs
		const validStudentTabs = ['Enrolled', 'Live', 'Recorded']
		if (!validStudentTabs.includes(currentTab.value)) {
			currentTab.value = 'Enrolled'
		} else if (currentTab.value === 'Live' && !location.search.includes('tab=')) {
			// Default to Enrolled if no tab specified
			currentTab.value = 'Enrolled'
		}
	} else if (isInstructorOrModerator) {
		// Instructors/moderators can only access Created tab
		if (currentTab.value !== 'Created') {
			currentTab.value = 'Created'
		}
	} else if (isAdmin) {
		// Admins default to All tab
		if (currentTab.value === 'Live' && !location.search.includes('tab=')) {
			currentTab.value = 'All'
		}
	}
	
	setFiltersFromQuery()
	updateCourses()
	getCourseCount()
	categories.value = [
		{
			label: '',
			value: null,
		},
	]
})

const setFiltersFromQuery = () => {
	let queries = new URLSearchParams(location.search)
	title.value = queries.get('title') || ''
	currentCategory.value = queries.get('category') || null
	certification.value = queries.get('certification') || false
}

const courses = createListResource({
	doctype: 'LMS Course',
	url: 'lms.lms.utils.get_courses',
	cache: ['courses', user.data?.name],
	pageLength: pageLength.value,
	start: start.value,
	onSuccess(data) {
		setCategories(data)
	},
})

const setCategories = (data) => {
	let allCategories = data.map((course) => course.category)
	allCategories = allCategories.filter(
		(category, index) => allCategories.indexOf(category) === index && category
	)
	if (categories.value.length <= allCategories.length) {
		updateCategories(data)
	}
}

const isPersonaCaptured = async () => {
	let persona = await call('frappe.client.get_single_value', {
		doctype: 'LMS Settings',
		field: 'persona_captured',
	})
	return persona
}

const identifyUserPersona = async () => {
	if (user.data?.is_system_manager && !user.data?.developer_mode) {
		let personaCaptured = await isPersonaCaptured()
		if (personaCaptured) return
		if (!courseCount.value) {
			router.push({
				name: 'PersonaForm',
			})
		}
	}
}

const getCourseCount = () => {
	if (!user.data) return

	call('frappe.client.get_count', {
		doctype: 'LMS Course',
	}).then((data) => {
		courseCount.value = data
		identifyUserPersona()
	})
}

const updateCourses = () => {
	updateFilters()
	courses.update({
		filters: filters.value,
	})
	courses.reload()
}

const updateFilters = () => {
	updateCategoryFilter()
	updateTitleFilter()
	updateCertificationFilter()
	updateTabFilter()
	updateStudentFilter()
	setQueryParams()
}

const updateCategoryFilter = () => {
	if (currentCategory.value) {
		filters.value['category'] = currentCategory.value
	} else {
		delete filters.value['category']
	}
}

const updateTitleFilter = () => {
	if (title.value) {
		filters.value['title'] = ['like', `%${title.value}%`]
	} else {
		delete filters.value['title']
	}
}

const updateCertificationFilter = () => {
	if (certification.value) {
		filters.value['certification'] = 1
	} else {
		delete filters.value['certification']
	}
}

const updateTabFilter = () => {
	delete filters.value['live']
	delete filters.value['created']
	delete filters.value['published_on']
	delete filters.value['upcoming']
	delete filters.value['recorded']

	if (currentTab.value == 'All') {
		// All tab - show all courses without filters (only for admins)
		delete filters.value['published']
		delete filters.value['enrolled']
		delete filters.value['upcoming']
	} else if (currentTab.value == 'Enrolled' && user.data?.is_student) {
		filters.value['enrolled'] = 1
		delete filters.value['published']
	} else if (currentTab.value == 'Recorded' && user.data?.is_student) {
		// Recorded tab - show courses with recorded lectures for enrolled students
		filters.value['recorded'] = 1
		delete filters.value['published']
		delete filters.value['enrolled']
	} else if (currentTab.value == 'Created') {
		// For instructors/moderators, show all their created courses
		filters.value['created'] = 1
		delete filters.value['published']
		delete filters.value['enrolled']
	} else {
		delete filters.value['published']
		delete filters.value['enrolled']

		if (currentTab.value == 'Live') {
			filters.value['published'] = 1
			filters.value['upcoming'] = 0
			filters.value['live'] = 1
		} else if (currentTab.value == 'Upcoming') {
			filters.value['upcoming'] = 1
		} else if (currentTab.value == 'New') {
			filters.value['published'] = 1
			filters.value['published_on'] = [
				'>=',
				dayjs().add(-3, 'month').format('YYYY-MM-DD'),
			]
		} else if (currentTab.value == 'Unpublished') {
			filters.value['published'] = 0
		}
	}
}

const updateStudentFilter = () => {
	if (!user.data || (user.data?.is_student && currentTab.value != 'Enrolled')) {
		filters.value['published'] = 1
	}
}

const setQueryParams = () => {
	let queries = new URLSearchParams(location.search)
	let filterKeys = {
		title: title.value,
		category: currentCategory.value,
		certification: certification.value,
	}

	Object.keys(filterKeys).forEach((key) => {
		if (filterKeys[key]) {
			queries.set(key, filterKeys[key])
		} else {
			queries.delete(key)
		}
	})

	let queryString = ''
	if (queries.toString()) {
		queryString = `?${queries.toString()}`
	}

	history.replaceState({}, '', `${location.pathname}${queryString}`)
}

const updateCategories = (data) => {
	data.forEach((course) => {
		if (
			course.category &&
			!categories.value.find((category) => category.value === course.category)
		)
			categories.value.push({
				label: course.category,
				value: course.category,
			})
	})
}

watch(currentTab, () => {
	if (currentTab.value === 'Recorded') {
		// Load recorded lectures when Recorded tab is selected
		recordedLectures.reload()
	} else {
		updateCourses()
	}
})

const openRecordingModal = (lecture) => {
	currentRecording.value = lecture
	showRecordingModal.value = true
}

const courseTabs = computed(() => {
	// Check if user is a student (not moderator, instructor, or evaluator)
	const isStudent = user.data && 
	!(user.data?.is_moderator || user.data?.is_instructor || user.data?.is_evaluator)
	const isAdmin = user.data?.is_system_manager
	
	if (isStudent) {
		// Students see Enrolled, Live, and Recorded tabs
		return [
			{
				label: __('Enrolled'),
			},
			{
				label: __('Live'),
			},
			{
				label: __('Recorded'),
			},
		]
	}
	
	// For admins (System Managers) - show all tabs
	if (isAdmin) {
		return [
			{
				label: __('All'),
			},
			{
				label: __('Live'),
			},
			{
				label: __('New'),
			},
			{
				label: __('Upcoming'),
			},
			{
				label: __('Created'),
			},
			{
				label: __('Unpublished'),
			},
		]
	}
	
	// For instructors, moderators, and evaluators - only show Created tab
	if (
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	) {
		return [
			{
				label: __('Created'),
			},
		]
	}
	
	// Fallback (should not reach here for logged-in users)
	return [
		{
			label: __('Live'),
		},
	]
})

const breadcrumbs = computed(() => [
	{
		label: __('Courses'),
		route: { name: 'Courses' },
	},
])

usePageMeta(() => {
	return {
		title: __('Courses'),
		icon: brand.favicon,
	}
})
</script>
