import {createApp} from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import axios from 'axios'
import VueAxios from 'vue-axios'


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
    if (!res.data.success) {
        store.commit('del_token')
        router.push({path: '/login'}).then(doNone);
    }

    return res;
});


// 页面刷新时，重新赋值token
if (localStorage.getItem('token')) {
    store.commit('set_token', localStorage.getItem('token'))
}

router.beforeEach((to, from, next) => {
    console.log(["In router beforeEach, Token = ", store.state.token])
    const isLogin = store.state.token;  // 是否登录

    if (!isLogin && to.path !== "/login") {
        // 未登录状态；跳转至login
        console.log("GOTO Login Page")
        router.push({path: '/login'}).then(doNone);
    }

    if (to.path === '/login') {
        // 已登录状态；当路由到login时，跳转至home
        if (isLogin) {
            console.log("GOTO Home Page")
            router.push({path: '/home/todo'}).then(doNone);
        }
    }
    next();
});


createApp(App).use(store).use(router).use(VueAxios, axios).mount('#app')
