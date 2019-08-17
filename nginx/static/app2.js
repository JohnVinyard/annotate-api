document.addEventListener('DOMContentLoaded', function() {
  const Welcome = Vue.component('welcome', {
    template: '#welcome-template'
  });

  const User = Vue.component('user', {
    props: ['user', 'id'],
    template: '#user-template',
    data: function() {
      return {
        userName: null,
        aboutMe: null
      }
    },
    mounted: function() {
      const client = new AnnotateApiClient(
        this.user.name,
        this.user.password,
        cochleaAppSettings.apiHost);
      client.getUser(this.user.data.id)
        .then(data => {
          this.userName = data.user_name;
          this.aboutMe = data.about_me;
        });

    }
  });

  const SignIn = Vue.component('sign-in', {
    props: ['user'],
    template: '#sign-in-template',
    data: function() {
      return {
        error: false
      };
    },
    methods: {
      signIn : function(event) {
        this.error = false;

        const client = new AnnotateApiClient(
          this.user.name,
          this.user.password,
          cochleaAppSettings.apiHost);

        client.getUserByName(this.user.name)
          .then(data => {
            this.user.data = data.items[0];
            this.$router.push({ name: 'user', params: {
              user: this.user,
              id: this.user.data.id
            }});
          })
          .catch(error => {
            this.user.name = null;
            this.user.password = null;
            this.error = true;
          });
      }
    }
  });

  const Annotations = Vue.component('annotations', {
    template: '#annotations-template'
  });

  const Sound = Vue.component('sound', {
    props: ['id'],
    template: '#sound-template'
  });



  const router = new VueRouter({
    routes: [
      { path: '/welcome', name: 'welcome', component: Welcome },
      { path: '/sign-in', name: 'sign-in', component: SignIn, props: true },
      { path: '/annotations', name: 'annotations', component: Annotations},
      { path: '/sounds/:id', name: 'sound', component: Sound, props: true},
      { path: '/users/:id', name: 'user', component: User, props: true}
    ],
    mode: 'history'
  });

  app = new Vue({
    router,
    data: {
      user: {
        name: null,
        password: null,
        data: null
      },
    },
    methods: { },
    mounted: function() {
      this.$router.push({ path: '/welcome' });
    },
  }).$mount('#app');
});
