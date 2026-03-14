import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import axios from 'axios'

// fontAwesome相关配置
import { library } from '@fortawesome/fontawesome-svg-core'
import { faTrashAlt, faClock, faCheck, faUndo, faAngleDoubleDown, faListOl, faCalculator } from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from "@fortawesome/vue-fontawesome";
library.add(faTrashAlt, faClock, faCheck, faUndo, faAngleDoubleDown, faListOl, faCalculator)


// axios相关配置
axios.defaults.baseURL = '/api'

axios.interceptors.response.use(res => {
    return res;
}, async error=> {
    if (error.response.status === 401) {
        console.log("返回401, 跳转到登录页面")
        await router.push({path: '/login'})
    } else {
        console.log("返回错误代码:", error.response.status)
    }
});


const app = createApp(App)

app.use(createPinia())
app.use(router)
app.component('font-awesome-icon', FontAwesomeIcon)
app.mount('#app')
