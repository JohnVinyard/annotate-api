document.addEventListener('DOMContentLoaded', function() {

  const Welcome = Vue.component('welcome', {
    props: ['user'],
    template: '#welcome-template'
  });

  const Menu = Vue.component('menu', {
    template: '#menu-template'
  });

  const UserDetail = Vue.component('user', {
    props: ['user', 'id'],
    template: '#user-detail-template',
    data: function() {
      return {
        userName: null,
        aboutMe: null,
        infoUrl: null
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
          this.infoUrl = data.info_url;
        });

    }
  });

  const Annotation = Vue.component('annotation', {
    template: '#annotation-template',
    props: ['annotation'],
    data: function() {
      return {
        isVisible: false,
        zoom: 1,
        featureData: undefined
      };
    },
    methods: {
      zoomIn: function() {
        this.zoom = Math.min(20, this.zoom + 1);
      },
      zoomOut: function() {
        this.zoom = Math.max(1, this.zoom - 1);
      }
    },
    mounted: function() {
      scrolledIntoView(this.$refs.container)
        .then(() => {
          this.isVisible = true;
          const drawContext = this.$refs.canvas.getContext('2d');
          // drawContext.fillRect(Math.random() * 100, Math.random() * 100, 10, 10);
          drawContext.fillText((new Date()).toString(), 10, 50);
        });
    },
  });

  const Annotations = Vue.component('annotations', {
    template: '#annotations-template',
    data: function() {
      return {
        query: null,
        annotations: []
      }
    },
    mounted: function() {
      const identity = auth.tryGetUserIdentity();
      const client = new AnnotateApiClient(
        identity.name, identity.password, cochleaAppSettings.apiHost);
      client
        .getAnnotations()
        .then(data => {
          this.annotations = data.items;
        });
    }
  });


  const UserSummary = Vue.component('user-summary', {
    props: ['user'],
    template: '#user-summary-template',
    data: function() {
      return {

      };
    }
  });

  const UserList = Vue.component('user-list', {
    template: '#users-template',
    data: function() {
      return {
        query: null,
        users: []
      };
    },
    mounted: function() {
      const identity = auth.tryGetUserIdentity();
      const client = new AnnotateApiClient(
        identity.name, identity.password, cochleaAppSettings.apiHost);
      client
        .getUsers()
        .then(data => {
          this.users = data.items;
        });
    }
  });

  const Register = Vue.component('register', {
    template: '#register-template',
    data: function() {
      return {

      };
    }
  });

  class Authenticator {
    refreshUserIdentity(userName, password) {
      const client = new AnnotateApiClient(
        userName, password, cochleaAppSettings.apiHost);

      return client.getUserByName(userName)
        .then(data => {
          // set the item in local storage
          window.localStorage.setItem('identity', JSON.stringify({
            name: userName,
            password: password,
            data: data.items[0]
          }));
          return data.items[0];
        });
    }

    tryGetUserIdentity() {
      return JSON.parse(window.localStorage.getItem('identity'));
    }

    logOut() {
      window.localStorage.removeItem('identity');
    }
  }

  const auth = new Authenticator();

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

        auth
          .refreshUserIdentity(this.user.name, this.user.password)
          .then(data => {
            this.user.data = data;
            // TODO: The sign-in location should be factored out somewhere
            this.$router.push({ name: 'menu' });
          })
          .catch(error => {
            this.user.name = null;
            this.user.password = null;
            this.error = true;
          });
      }
    }
  });



  const Sounds = Vue.component('sounds', {
    template: '#sounds-template'
  });

  const Sound = Vue.component('sound', {
    props: ['id'],
    template: '#sound-template'
  });

  const routerPath = (path) => cochleaAppSettings.basePath + path;

  const router = new VueRouter({
    routes: [
      { path: routerPath('/welcome'), name: 'welcome', component: Welcome, props: true },
      { path: routerPath('/menu'), name: 'menu', component: Menu},
      { path: routerPath('/sign-in'), name: 'sign-in', component: SignIn, props: true },
      { path: routerPath('/register'), name: 'register', component: Register},
      { path: routerPath('/annotations'), name: 'annotations', component: Annotations},
      { path: routerPath('/sounds'), name: 'sounds', component: Sounds },
      { path: routerPath('/sounds/:id'), name: 'sound', component: Sound, props: true},
      { path: routerPath('/users/:id'), name: 'user', component: UserDetail, props: true},
      { path: routerPath('/users'), name: 'users', component: UserList, props: true}
    ],
    // mode: 'history'
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
    methods: {
      initializeCredentials: function() {
        const identity = auth.tryGetUserIdentity();
        if (identity === null) {
          return;
        }
        this.user.name = identity.name;
        this.user.password = identity.password;
        this.user.data = identity.data;
      },
      isAuthenticated: function() {
        return Boolean(this.user.data);
      },
      logOut: function() {
        auth.logOut();
        this.user = {
          name: null,
          password: null,
          data: null
        };
        this.$router.push({ name: 'welcome', params: { user: this.user } });
      },
      homeLink: function() {
        return this.isAuthenticated() ?
          { name: 'menu' } : { name: 'welcome', params: { user: this.user }};
      }
    },
    mounted: function() {
      this.initializeCredentials();
      this.$router.push(this.homeLink());
    },
  }).$mount('#app');
});
