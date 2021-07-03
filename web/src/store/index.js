import { createStore } from 'vuex'

export default createStore({
  state: {
    token: ''
  },
  mutations: {
    set_token(state, token) {
      state.token = token
      localStorage.token = token
    },
    del_token(state) {
        state.token = ''
        localStorage.removeItem('token')
    }
  },
  actions: {
  },
  modules: {
  }
})

