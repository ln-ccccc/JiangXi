import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import { APP_TITLE } from './config/minerDefaults.js'

document.title = APP_TITLE

createApp(App).mount('#app')
