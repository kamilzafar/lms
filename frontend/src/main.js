import './index.css'
import { createApp } from 'vue'
import router from './router'
import App from './App.vue'
import { createPinia } from 'pinia'
import dayjs from '@/utils/dayjs'
import { createDialog } from '@/utils/dialogs'
import translationPlugin from './translation'
import { usersStore } from './stores/user'
import { initSocket } from './socket'
import { FrappeUI, setConfig, frappeRequest, pageMetaPlugin } from 'frappe-ui'

let pinia = createPinia()
let app = createApp(App)
setConfig('resourceFetcher', frappeRequest)

app.use(FrappeUI)
app.use(pinia)
app.use(router)
app.use(translationPlugin)
app.use(pageMetaPlugin)
app.provide('$dayjs', dayjs)
app.provide('$socket', initSocket())
app.mount('#app')

const { userResource, allUsers } = usersStore()
app.provide('$user', userResource)
app.provide('$allUsers', allUsers)

app.config.globalProperties.$user = userResource
app.config.globalProperties.$dialog = createDialog

// Hide "Built on Frappe" branding
function hideFrappeBranding() {
	// Find and hide elements containing "Built on Frappe" text
	const allElements = document.querySelectorAll('*')
	allElements.forEach((el) => {
		const text = el.textContent || el.innerText
		if (text && text.includes('Built on Frappe')) {
			el.style.display = 'none'
			el.style.visibility = 'hidden'
		}
		// Also hide links to frappe.io (except docs)
		if (el.tagName === 'A' && el.href) {
			if (el.href.includes('frappe.io') && !el.href.includes('docs')) {
				el.style.display = 'none'
				el.style.visibility = 'hidden'
			}
		}
	})
}

// Run on page load
if (document.readyState === 'loading') {
	document.addEventListener('DOMContentLoaded', hideFrappeBranding)
} else {
	hideFrappeBranding()
}

// Use MutationObserver to catch dynamically added elements
const observer = new MutationObserver(() => {
	hideFrappeBranding()
})

observer.observe(document.body, {
	childList: true,
	subtree: true,
})
