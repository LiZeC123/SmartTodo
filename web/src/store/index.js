import { createStore } from 'vuex'

export default createStore({
  state: {
    token: '',
    tomatoTime: 25,
  },
  mutations: {
    set_token(state, token) {
      state.token = token
      localStorage.token = token
    },
    del_token(state) {
        state.token = ''
        localStorage.removeItem('token')
    },
    set_tomato_time(state, tomatoTime) {
      state.tomatoTime = tomatoTime
      localStorage.tomatoTime = tomatoTime
    }
  },
  actions: {
  },
  modules: {
  }
})

