import {createApp} from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import axios from 'axios'
import VueAxios from 'vue-axios'
import { library } from '@fortawesome/fontawesome-svg-core'
import { faTrashAlt, faClock, faCheck, faUndo, faAngleDoubleDown, faListOl, faCalculator } from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from "@fortawesome/vue-fontawesome";

library.add(faTrashAlt, faClock, faCheck, faUndo, faAngleDoubleDown, faListOl, faCalculator)

axios.defaults.baseURL = '/api'
axios.interceptors.request.use(config => {
    // 这是一个函数, 因此并不会在定义时立即执行, 而是在每次发送请求时执行此操作
    if (store.state.token) {
        config.headers.common['Token'] = store.state.token;
    }
    return config;
});

const doNone = function () {
    // Do Nothing
};

axios.interceptors.response.use(res => {
    return res;
}, error=> {
    if (error.response.status === 401) {
        console.log("返回401, 跳转到登录页面")
        store.commit('del_token')
        router.push({path: '/login'}).then(doNone)
    } else {
        console.log("返回错误代码:", error.response.status)
    }
});

// 页面刷新时，重新赋值存储的变量
if (localStorage.getItem('token')) {
    store.commit('set_token', localStorage.getItem('token'))
}
if (localStorage.getItem('tomatoTime')) {
    store.commit('set_tomato_time', localStorage.getItem('tomatoTime'))
}

router.beforeEach((to, from, next) => {
    // console.log(["In router beforeEach, Token = ", store.state.token])
    const isLogin = store.state.token;  // 是否登录

    if (!isLogin && to.path !== "/login") {
        // 未登录状态；跳转至login
        router.push({path: '/login'}).then(doNone);
    }

    if (to.path === '/login') {
        // 已登录状态；当路由到login时，跳转至home
        if (isLogin) {
            router.push({path: '/home/todo'}).then(doNone);
        }
    }
    next();
});

// 请求发送通知权限, 用于番茄钟提醒
Notification.requestPermission().then(doNone)

createApp(App).use(store).use(router).use(VueAxios, axios).component('font-awesome-icon', FontAwesomeIcon)
    .mount('#app')
