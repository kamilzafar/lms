<template>
	<div>
		<header
			class="sticky flex items-center justify-between top-0 z-10 border-b bg-surface-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs :items="breadcrumbs" />
			<Button @click="refresh" :loading="diagnostics.loading">
				<template #prefix>
					<RefreshCw class="h-4 w-4" :class="{ 'animate-spin': diagnostics.loading }" />
				</template>
				Refresh
			</Button>
		</header>

		<div class="p-5 pb-10 max-w-6xl mx-auto">
			<div class="text-2xl font-bold text-ink-gray-9 mb-6">
				Zoom Recording Diagnostics
			</div>

			<div v-if="diagnostics.loading" class="flex justify-center py-20">
				<Spinner class="w-8 h-8" />
			</div>

			<div v-else-if="diagnostics.data" class="space-y-8">
				<!-- Zoom Accounts Status -->
				<div class="border rounded-lg p-4">
					<div class="flex items-center gap-2 mb-4">
						<Settings class="h-5 w-5 text-ink-gray-7" />
						<h2 class="text-lg font-semibold text-ink-gray-9">Zoom Accounts</h2>
					</div>

					<div v-if="diagnostics.data.zoom_accounts?.length" class="space-y-3">
						<div
							v-for="account in diagnostics.data.zoom_accounts"
							:key="account.name"
							class="border rounded p-3 bg-surface-gray-1"
						>
							<div class="flex items-center justify-between mb-2">
								<div class="font-medium">{{ account.account_name }}</div>
								<Badge :theme="account.enabled ? 'green' : 'gray'">
									{{ account.enabled ? 'Enabled' : 'Disabled' }}
								</Badge>
							</div>
							<div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
								<div class="flex items-center gap-1">
									<component :is="account.has_account_id ? CheckCircle : XCircle"
										:class="account.has_account_id ? 'text-green-600' : 'text-red-500'"
										class="h-4 w-4" />
									Account ID
								</div>
								<div class="flex items-center gap-1">
									<component :is="account.has_client_id ? CheckCircle : XCircle"
										:class="account.has_client_id ? 'text-green-600' : 'text-red-500'"
										class="h-4 w-4" />
									Client ID
								</div>
								<div class="flex items-center gap-1">
									<component :is="account.has_client_secret ? CheckCircle : XCircle"
										:class="account.has_client_secret ? 'text-green-600' : 'text-red-500'"
										class="h-4 w-4" />
									Client Secret
								</div>
								<div class="flex items-center gap-1">
									<component :is="account.has_webhook_secret ? CheckCircle : XCircle"
										:class="account.has_webhook_secret ? 'text-green-600' : 'text-orange-500'"
										class="h-4 w-4" />
									Webhook Secret
								</div>
							</div>
							<div class="mt-2 text-sm">
								<span class="text-ink-gray-5">Auth Status:</span>
								<Badge
									:theme="account.auth_status === 'OK' ? 'green' : (account.auth_status.startsWith('Error') ? 'red' : 'gray')"
									class="ml-2"
								>
									{{ account.auth_status }}
								</Badge>
							</div>
							<div v-if="account.webhook_url" class="mt-2 text-xs text-ink-gray-5 break-all">
								Webhook URL: {{ account.webhook_url }}
							</div>
						</div>
					</div>
					<div v-else class="text-ink-gray-5 italic">
						No Zoom accounts configured
					</div>
				</div>

				<!-- Webhook Config -->
				<div class="border rounded-lg p-4">
					<div class="flex items-center gap-2 mb-4">
						<Webhook class="h-5 w-5 text-ink-gray-7" />
						<h2 class="text-lg font-semibold text-ink-gray-9">Webhook Configuration</h2>
					</div>
					<div class="space-y-2 text-sm">
						<div>
							<span class="text-ink-gray-5">Webhook URLs:</span>
							<div class="mt-1 space-y-1">
								<div v-for="url in diagnostics.data.webhook_config?.webhook_urls" :key="url"
									class="bg-surface-gray-2 px-2 py-1 rounded text-xs font-mono break-all">
									{{ url }}
								</div>
							</div>
						</div>
						<div class="flex items-center gap-2 mt-3">
							<component
								:is="diagnostics.data.webhook_config?.signature_verification_enabled ? CheckCircle : AlertTriangle"
								:class="diagnostics.data.webhook_config?.signature_verification_enabled ? 'text-green-600' : 'text-orange-500'"
								class="h-4 w-4"
							/>
							<span>
								Signature Verification:
								{{ diagnostics.data.webhook_config?.signature_verification_enabled ? 'Enabled' : 'Not configured' }}
							</span>
						</div>
					</div>
				</div>

				<!-- Pending Recordings -->
				<div class="border rounded-lg p-4">
					<div class="flex items-center gap-2 mb-4">
						<Clock class="h-5 w-5 text-ink-gray-7" />
						<h2 class="text-lg font-semibold text-ink-gray-9">
							Pending Recordings ({{ diagnostics.data.pending_recordings?.length || 0 }})
						</h2>
					</div>

					<div v-if="diagnostics.data.pending_recordings?.length" class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b text-left text-ink-gray-5">
									<th class="pb-2 pr-4">Title</th>
									<th class="pb-2 pr-4">Date</th>
									<th class="pb-2 pr-4">Meeting ID</th>
									<th class="pb-2 pr-4">Status</th>
									<th class="pb-2">Actions</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="lc in diagnostics.data.pending_recordings" :key="lc.name" class="border-b">
									<td class="py-2 pr-4">
										<div class="font-medium">{{ lc.title }}</div>
										<div class="text-xs text-ink-gray-5">{{ lc.batch }}</div>
									</td>
									<td class="py-2 pr-4 whitespace-nowrap">{{ lc.date }} {{ lc.time }}</td>
									<td class="py-2 pr-4 font-mono text-xs">{{ lc.meeting_id || '-' }}</td>
									<td class="py-2 pr-4">
										<Badge :theme="getStatusTheme(lc.status)">{{ lc.status }}</Badge>
										<div v-if="lc.minutes_since_end" class="text-xs text-ink-gray-5 mt-1">
											{{ lc.minutes_since_end }} min ago
										</div>
									</td>
									<td class="py-2">
										<Button
											size="sm"
											@click="testFetch(lc.name)"
											:loading="fetchingClass === lc.name"
											:disabled="!lc.meeting_id"
										>
											Test Fetch
										</Button>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<div v-else class="text-ink-gray-5 italic">
						No pending recordings
					</div>
				</div>

				<!-- Recent Recordings -->
				<div class="border rounded-lg p-4">
					<div class="flex items-center gap-2 mb-4">
						<Video class="h-5 w-5 text-ink-gray-7" />
						<h2 class="text-lg font-semibold text-ink-gray-9">
							Recent Recordings ({{ diagnostics.data.recent_recordings?.length || 0 }})
						</h2>
					</div>

					<div v-if="diagnostics.data.recent_recordings?.length" class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b text-left text-ink-gray-5">
									<th class="pb-2 pr-4">Title</th>
									<th class="pb-2 pr-4">Date</th>
									<th class="pb-2 pr-4">Recording URL</th>
									<th class="pb-2 pr-4">Lesson</th>
									<th class="pb-2">Modified</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="lc in diagnostics.data.recent_recordings" :key="lc.name" class="border-b">
									<td class="py-2 pr-4">
										<div class="font-medium">{{ lc.title }}</div>
										<div class="text-xs text-ink-gray-5">{{ lc.batch }}</div>
									</td>
									<td class="py-2 pr-4 whitespace-nowrap">{{ lc.date }}</td>
									<td class="py-2 pr-4">
										<Badge :theme="lc.has_recording_url ? 'green' : 'red'">
											{{ lc.has_recording_url ? 'Available' : 'Missing' }}
										</Badge>
									</td>
									<td class="py-2 pr-4">
										<Badge :theme="lc.lesson_created ? 'green' : 'orange'">
											{{ lc.lesson_created ? 'Created' : 'Not Created' }}
										</Badge>
									</td>
									<td class="py-2 text-xs text-ink-gray-5">{{ lc.modified }}</td>
								</tr>
							</tbody>
						</table>
					</div>
					<div v-else class="text-ink-gray-5 italic">
						No recent recordings
					</div>
				</div>

				<!-- Cron Job Status -->
				<div class="border rounded-lg p-4">
					<div class="flex items-center gap-2 mb-4">
						<Timer class="h-5 w-5 text-ink-gray-7" />
						<h2 class="text-lg font-semibold text-ink-gray-9">Cron Job Status</h2>
					</div>
					<div class="text-sm space-y-2">
						<div>
							<span class="text-ink-gray-5">Job:</span>
							<code class="ml-2 text-xs bg-surface-gray-2 px-1 py-0.5 rounded">
								{{ diagnostics.data.cron_job_status?.job_name }}
							</code>
						</div>
						<div>
							<span class="text-ink-gray-5">Schedule:</span>
							<span class="ml-2">{{ diagnostics.data.cron_job_status?.schedule }}</span>
						</div>
						<div v-if="diagnostics.data.cron_job_status?.recent_runs?.length" class="mt-3">
							<div class="text-ink-gray-5 mb-2">Recent Runs:</div>
							<div class="space-y-1">
								<div
									v-for="(run, idx) in diagnostics.data.cron_job_status.recent_runs"
									:key="idx"
									class="flex items-center gap-2 text-xs"
								>
									<Badge :theme="run.status === 'Complete' ? 'green' : 'red'" size="sm">
										{{ run.status }}
									</Badge>
									<span class="text-ink-gray-5">{{ run.creation }}</span>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Recent Errors -->
				<div v-if="diagnostics.data.recent_errors?.length" class="border border-red-200 rounded-lg p-4 bg-red-50">
					<div class="flex items-center gap-2 mb-4">
						<AlertTriangle class="h-5 w-5 text-red-600" />
						<h2 class="text-lg font-semibold text-red-700">
							Recent Errors ({{ diagnostics.data.recent_errors?.length }})
						</h2>
					</div>
					<div class="space-y-2">
						<div
							v-for="err in diagnostics.data.recent_errors"
							:key="err.name"
							class="bg-white border border-red-100 rounded p-2 text-sm"
						>
							<div class="font-medium text-red-700">{{ err.method }}</div>
							<div class="text-xs text-ink-gray-5">{{ err.creation }}</div>
							<div class="text-xs text-red-600 mt-1 font-mono break-all">
								{{ err.error_preview }}
							</div>
						</div>
					</div>
				</div>
			</div>

			<div v-else class="text-center py-20 text-ink-gray-5">
				Failed to load diagnostics. Please try refreshing.
			</div>
		</div>
	</div>
</template>

<script setup>
import { inject, ref } from 'vue'
import { Badge, Breadcrumbs, Button, Spinner, createResource, toast } from 'frappe-ui'
import {
	AlertTriangle,
	CheckCircle,
	Clock,
	RefreshCw,
	Settings,
	Timer,
	Video,
	Webhook,
	XCircle,
} from 'lucide-vue-next'

const user = inject('$user')
const fetchingClass = ref(null)

const diagnostics = createResource({
	url: 'lms.lms.api.zoom_recording_diagnostics',
	auto: true,
})

const refresh = () => {
	diagnostics.reload()
}

const getStatusTheme = (status) => {
	switch (status) {
		case 'Ready for fetch':
			return 'green'
		case 'Just ended - waiting':
			return 'blue'
		case 'In progress':
			return 'orange'
		case 'Past fetch window':
			return 'red'
		default:
			return 'gray'
	}
}

const testFetch = async (liveClassName) => {
	fetchingClass.value = liveClassName
	try {
		const result = await fetch('/api/method/lms.lms.api.test_zoom_recording_fetch', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-Frappe-CSRF-Token': window.csrf_token,
			},
			body: JSON.stringify({ live_class_name: liveClassName }),
		})
		const data = await result.json()

		if (data.message?.status === 'success' || data.message?.status === 'info') {
			toast.success(data.message?.message || 'Fetch completed')
			diagnostics.reload()
		} else {
			toast.error(data.message?.message || 'Fetch failed')
		}
	} catch (error) {
		toast.error('Error: ' + error.message)
	} finally {
		fetchingClass.value = null
	}
}

const breadcrumbs = [
	{ label: 'Home', route: { name: 'Home' } },
	{ label: 'Zoom Diagnostics', route: { name: 'ZoomDiagnostics' } },
]
</script>
