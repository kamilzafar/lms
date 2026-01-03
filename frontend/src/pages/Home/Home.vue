<template>
	<div class="w-full px-5 pt-5 pb-10">
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<div class="text-xl font-bold text-ink-gray-9">
					{{ __('Hey') }}, {{ user.data?.full_name }} 👋
				</div>
				<div>
					<div
						@click="showStreakModal = true"
						class="bg-surface-amber-2 px-2 py-1 rounded-md cursor-pointer"
					>
						<span> 🔥 </span>
						<span class="text-ink-gray-9">
							{{ streakInfo.data?.current_streak }}
						</span>
					</div>
				</div>
			</div>

			<div class="text-lg text-ink-gray-6 leading-6">
				{{ subtitle }}
			</div>
		</div>

		<!-- Unified Homepage Layout for All Roles -->
		<UnifiedHome
			:liveClasses="liveClasses"
			:courses="courses"
			:evals="evals"
			:isAdmin="isAdmin"
		/>
	</div>
	<Streak v-model="showStreakModal" :streakInfo="streakInfo" />
</template>
<script setup lang="ts">
import { computed, inject, onMounted, ref } from 'vue'
import {
	call,
	createResource,
	usePageMeta,
} from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import UnifiedHome from '@/pages/Home/UnifiedHome.vue'
import Streak from '@/pages/Home/Streak.vue'

const user = inject<any>('$user')
const { brand } = sessionStore()
const evalCount = ref(0)
const showStreakModal = ref(false)

onMounted(() => {
	call('lms.lms.utils.get_upcoming_evals').then((data: any) => {
		evalCount.value = data.length
	})
})

// Admin = System Manager, Instructor, Moderator, Evaluator (but NOT Teacher)
const isAdmin = computed(() => {
	// Teachers are NOT admins - they only view enrolled content
	if (user.data?.is_teacher && !user.data?.is_system_manager && !user.data?.is_instructor && !user.data?.is_moderator) {
		return false
	}
	return (
		user.data?.is_system_manager ||
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	)
})

// Teachers and Students get enrolled live classes, Admins get all admin live classes
const myLiveClasses = createResource({
	url: 'lms.lms.api.get_my_live_classes',
	auto: !isAdmin.value ? true : false,
})

const adminLiveClasses = createResource({
	url: 'lms.lms.api.get_admin_live_classes',
	auto: isAdmin.value ? true : false,
})

// Unified live classes - depends on role
const liveClasses = computed(() => {
	if (isAdmin.value) {
		return adminLiveClasses
	}
	return myLiveClasses
})

// Teachers and Students get enrolled courses, Admins get created courses
const myCourses = createResource({
	url: 'lms.lms.api.get_my_courses',
	auto: !isAdmin.value ? true : false,
})

const createdCourses = createResource({
	url: 'lms.lms.api.get_created_courses',
	auto: isAdmin.value ? true : false,
})

// Unified courses - depends on role
const courses = computed(() => {
	if (isAdmin.value) {
		return createdCourses
	}
	return myCourses
})

const adminEvals = createResource({
	url: 'lms.lms.api.get_admin_evals',
	auto: isAdmin.value ? true : false,
})

// Unified evals
const evals = computed(() => {
	return adminEvals
})

const streakInfo = createResource({
	url: 'lms.lms.api.get_streak_info',
	auto: true,
})

const subtitle = computed(() => {
	const liveClassCount = liveClasses.value?.data?.length || 0
	const evalCountValue = isAdmin.value ? (adminEvals.data?.length || 0) : evalCount.value

	let liveClassSuffix = liveClassCount > 1 ? __('live classes') : __('live class')
	let evalSuffix = evalCountValue > 1 ? __('evaluations') : __('evaluation')

	if (liveClassCount > 0 && evalCountValue > 0) {
		return __('You have {0} upcoming {1} and {2} {3} scheduled.').format(
			liveClassCount,
			liveClassSuffix,
			evalCountValue,
			evalSuffix
		)
	} else if (liveClassCount > 0) {
		return __('You have {0} upcoming {1}.').format(
			liveClassCount,
			liveClassSuffix
		)
	} else if (evalCountValue > 0) {
		return __('You have {0} {1} scheduled.').format(
			evalCountValue,
			evalSuffix
		)
	}

	if (isAdmin.value) {
		return __('Manage your courses and batches at a glance')
	}
	return __('Resume where you left off')
})

usePageMeta(() => {
	return {
		title: __('Home'),
		icon: brand.favicon,
	}
})
</script>
