const timeAgo = timeago();

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

const getApiClient = () => {
  const identity = auth.tryGetUserIdentity();
  const client = new AnnotateApiClient(
    identity.name, identity.password, cochleaAppSettings.apiHost);
  return client;
};

/*
*
*
*/
const featurePromise =
  (sound, featureDataMapping, feature, startSeconds, durationSeconds=null) => {

  // Check if we've already fetched features for this sound
  let featureDataPromise = featureDataMapping[sound];


  if (featureDataPromise === undefined) {
    const apiClient = getApiClient();

    // audio and features have not yet been fetched
    featureDataPromise = apiClient
      // Get sound data from the API
      .getResource(apiClient.buildUri(sound))
      // Fetch audio data from the remote audio url
      .then(data => {
        const audioUrl = data.low_quality_audio_url || data.audio_url;
        return new Promise(function(resolve, reject) {
          return fetchAudio(audioUrl, context).then(buffer => {
            resolve({
              buffer,
              audioUrl,
              soundUri: sound,
              sound: data
             });
          });
        });
      });

      if(feature.user_name === 'audio') {
        // If the current feature being viewed is audio, we've already fetched
        // it
        featureDataPromise = featureDataPromise
          .then(data => {
            const {buffer, audioUrl, soundUri, sound} = data;
            const audioData = buffer.getChannelData(0);
            const frequency = 1 / buffer.sampleRate;
            const fd = new FeatureData(
              audioData, [audioData.length], frequency, frequency);
            return {featureData: fd, audioUrl, sound};
          });
      } else {
        // The feature being viewed is other than audio and needs to be fetched
        featureDataPromise = featureDataPromise
          .then(data => {
            const {buffer, audioUrl, soundUri, sound} = data;

            const promise = getApiClient().getSoundAnnotationsByUser(
              sound.id, feature.id);
            return promiseContext(promise, r => ({audioUrl, sound}));
          })
          .then(result => {
            const {data, audioUrl, sound} = result;
            const promise = fetchBinary(data.items[0].data_url);
            return promiseContext(promise, r => ({audioUrl, sound}));
          })
          .then(result => {
            const {data, audioUrl, sound} = result;
            const featureData = unpackFeatureData(data);
            return {featureData, audioUrl, sound};
          });
      }

    // Put the pending promise into the map
    featureDataMapping[sound] = featureDataPromise;
  }

  const slicedPromise = featureDataPromise.then(data => {
    const {featureData, audioUrl, sound} = data;
    return featureData.timeSlice(
      startSeconds, durationSeconds || sound.duration_seconds);
  });

  const audioUrlPromise = featureDataPromise.then(data => {
    const {featureData, audioUrl, sound} = data;
    return audioUrl;
  });

  const soundPromise = featureDataPromise.then(data => {
    return sound;
  });

  return [slicedPromise, audioUrlPromise, soundPromise];
};

document.addEventListener('DOMContentLoaded', function() {

  const Welcome = Vue.component('welcome', {
    props: ['user'],
    template: '#welcome-template'
  });

  const Menu = Vue.component('main-menu', {
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

  const Selection = Vue.component('selection', {
    template: '#selection-template',
    props: ['start', 'duration', 'isSelecting'],
    methods: {
      adjustLeft: function() {
        console.log('adjust left');
      },
      adjustRight: function() {
        console.log('adjust right');
      },
      adjust: function() {
        console.log('adjust');
      }
    }
  });

  const SoundView = Vue.component('sound-view', {
    template: '#sound-view-template',
    props: ['featureData', 'audioUrl', 'startSeconds'],
    data: function() {
      return {
        zoom: 1,
        panListener: null,
        resizeHandler: null,
        selection: {
          start: null,
          end: null
        },
        isSelecting: false,
        rect: null
      }
    },
    watch: {
      zoom: function(val) {
        this.draw();
      },
      featureData: function(val) {
        this.draw();
      }
    },
    methods: {
      resetSelection: function() {
        this.selection = { start: null, end: null };
      },
      selectionWidth: function(event) {
        return Math.abs(this.selection.end - this.selection.start);
      },
      selectionStart: function(event) {
        if (this.$refs.container === undefined) {
          return 0;
        }
        const start = Math.min(this.selection.start, this.selection.end);
        return start - this.$refs.container.scrollLeft;
      },
      updateSelection: function(event) {
        const pos = event.offsetX;
        this.selection.end = pos;
        const selection = {...this.selection};
      },
      startSelection: function(event) {
        this.resetSelection();
        this.isSelecting = true;
        console.log('starting selection');
        // TODO: This needs to take into account overall offset as well.  This
        // should be factored out because I'm surely doing it elsewhere
        this.selection.start = event.offsetX;
        this.$refs.canvas.addEventListener('mousemove', this.updateSelection);
      },
      endSelection: function(event) {
        this.$refs.canvas.removeEventListener(
          'mousemove', this.updateSelection);
        console.log('end selection', event);
        const startSeconds = this.coordinateToSeconds(
          Math.min(this.selection.start, this.selection.end));
        const endSeconds = this.coordinateToSeconds(
          Math.max(this.selection.start, this.selection.end));
        console.log('Selection created', startSeconds, endSeconds);
        this.isSelecting = false;
        // TODO: fire an event and clear the selection
      },
      zoomIn: function() {
        this.resetSelection();
        this.zoom = Math.min(20, this.zoom + 1);
      },
      zoomOut: function() {
        this.resetSelection();
        this.zoom = Math.max(1, this.zoom - 1);
      },
      containerWidth: function() {
        return this.$refs.container.clientWidth;
      },
      elementWidth: function() {
        return this.containerWidth() * this.zoom;
      },
      coordinateToSeconds: function(coordinate) {
        // the starting point in seconds relative to this slice
        const relativeStartSeconds =
          (coordinate / this.elementWidth()) * this.featureData.durationSeconds;
        // the starting point in seconds in the sound as a whole
        const startSeconds = this.startSeconds + relativeStartSeconds;
        return startSeconds;
      },
      playAudio: function(event) {
        this.resetSelection();
        // the starting point in seconds relative to this slice
        const relativeStartSeconds =
          (event.offsetX / this.elementWidth()) * this.featureData.durationSeconds;
        // the starting point in seconds in the sound as a whole
        const startSeconds = this.startSeconds + relativeStartSeconds;
        const durationSeconds =
          Math.min(2.5, this.featureData.durationSeconds - relativeStartSeconds);
        playAudio(this.audioUrl, context, startSeconds, durationSeconds);
      },
      clear: function() {
        this.drawContext.clearRect(
          0, 0, this.$refs.canvas.width, this.$refs.canvas.height);
      },
      draw: function(preserveOffset=false) {

        const canvas = this.$refs.canvas;
        const container = this.$refs.container;
        const elementWidth = this.elementWidth();

        canvas.width = elementWidth;
        canvas.style.width = `${this.zoom * 100}%`;
        canvas.height = container.clientHeight;
        canvas.style.height = '100%';

        this.clear();

        if(preserveOffset) {
          container.scrollLeft = this.offsetPercent * elementWidth;
        } else {
          const offsetPercent = container.scrollLeft / elementWidth;
          this.offsetPercent = offsetPercent;
        }

        if(this.featureData === null) {
          return;
        }

        const height = container.clientHeight;

        const stride = this.featureData.length / elementWidth;
        const increment = Math.max(1, 1 / stride);

        const imageData = this.drawContext.getImageData(
          container.scrollLeft,
          0,
          this.containerWidth(),
          container.clientHeight);

        if (this.featureData.rank === 2) {
          this.draw2D(stride, increment, height, imageData);
        } else if(this.featureData.rank === 1) {
          this.draw1D(stride, increment, height, imageData);
        } else {
          throw new Error('Dimensions greater than 2 not currently supported');
        }
      },
      draw1D: function(stride, increment, height, imageData) {
        for (let i = 0; i < this.containerWidth(); i++) {
          const index =
            (this.featureData.length * this.offsetPercent) + (i * stride);
          const sample =
            Math.abs(this.featureData.binaryData[Math.round(index)]);

          // KLUDGE: This assumes that all data will be in range 0-1
          const value = 0.25 + (sample);
          const color = `rgba(0, 0, 0, ${value})`;
          this.drawContext.fillStyle = color;

          const size = sample * height;
          this.drawContext.fillRect(
            this.$refs.container.scrollLeft + i,
            (height - size) / 2,
            increment,
            size);
        }
      },
      draw2D: function(_, increment, height, imageData) {
        const container = this.$refs.container;

        // The Uint8ClampedArray contains height × width × 4
        const timeDim = this.featureData.dimensions[0];
        const featureDim = this.featureData.dimensions[1];
        const stride = 4;

        const timeRatio = timeDim / this.elementWidth();
        const featureRatio = featureDim / imageData.height;

        for(let i = 0; i < imageData.data.length; i += stride) {
          // compute image coordinates
          const x = (i / stride) % imageData.width;
          const y = Math.floor((i / stride) / imageData.width);

          const timeIndex = Math.floor((container.scrollLeft + x) * timeRatio);
          // // since the coordinate system goes from top to bottom, we'll need to
          // // invert the order we draw features in
          const featureIndex = featureDim - Math.floor(y * featureRatio);

          // normalize to the range 0-1 based on statistics from the metadata
          const maxValue = this.featureData.metadata.max_value;
          const value = this.featureData.item([timeIndex, featureIndex]) / maxValue;
          const imageValue = Math.floor(255 * value);

          // Translate the scalar value into color space
          imageData.data[i] = imageValue;
          imageData.data[i + 1] = imageValue;
          imageData.data[i + 2] = imageValue;
          imageData.data[i + 3] = 255;
        }
        this.drawContext.putImageData(imageData, container.scrollLeft, 0);
      }
    },
    beforeDestroy: function() {
      this.$refs.container.removeEventListener('scroll', this.panListener);
      window.removeEventListener('resize', this.resizeListener);
    },
    mounted: function() {
      this.drawContext = this.$refs.canvas.getContext('2d');
      this.rect = this.$refs.canvas.getBoundingClientRect();
      // re-draw whenever the scroll position changes
      this.panListener =
        onScroll(this.$refs.container, () => {
          this.draw(false);
          this.resetSelection();
        }, 100);
      // re-draw whenever the window is resized
      this.resizeHandler =
        onResize(window, () => this.draw(true), 100);
    },
  });

  const Annotation = Vue.component('annotation', {
    template: '#annotation-template',
    props: ['annotation'],
    data: function() {
      return {
        timeago: timeAgo,
        featureData: null,
        audioUrl: null,
        scrollListener: null,
      };
    },
    methods: {
      selectQuery: function(tag) {
        this.$emit('select-query', tag);
      },
      offsetSeconds: function() {
        return this.annotation.start_seconds;
      },
    },
    beforeDestroy: function() {
      document.removeEventListener('scroll', this.scrollListener[0]);
    },
    mounted: function() {
      const [checkVisibility, promise] = scrolledIntoView(this.$refs.container);
      this.scrollListener = checkVisibility;

      promise
        .then(() => {
          this.isVisible = true;
          const [slicedPromise, audioUrlPromise] =
            this.annotation.featurePromise();

          audioUrlPromise.then(audioUrl => {
            this.audioUrl = audioUrl;
          });

          slicedPromise.then(featureData => {
            this.featureData = featureData;
          });
        });
    },
  });

  const Annotations = Vue.component('annotations', {
    template: '#annotations-template',
    data: function() {
      return {
        query: null,
        annotations: [],
        currentFeature: {
          user_name: 'audio'
        },
        allFeatures: []
      }
    },
    methods: {
      setQuery: function(tag) {
        this.query = tag;
        this.handleSubmit();
      },
      handleSubmit: function() {
        this.annotations = [];
        getApiClient()
          .getAnnotations(this.query)
          .then(data => {
            const annotations = data.items;
            const featureDataMapping = {};
            annotations.forEach(annotation => {
              const fp = () => featurePromise(
                annotation.sound,
                featureDataMapping,
                this.currentFeature,
                annotation.start_seconds,
                annotation.duration_seconds);
              annotation.featurePromise = fp;
            });
            this.annotations = annotations;
          });
      },
      changeFeature: function() {
        this.handleSubmit();
      }
    },
    mounted: function() {


      this.allFeatures.push(this.currentFeature);
      this.handleSubmit();
      getApiClient().getFeatureBots()
        .then(data => {
          this.allFeatures = this.allFeatures.concat(data.items);
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
    template: '#sound-template',
    data: function() {
      return {
        featureData: null,
        audioUrl: null,
        sound: null
      };
    },
    mounted: function() {
      const [slicedPromise, audioUrlPromise, soundPromise] =
        featurePromise(`/sounds/${this.id}`, {}, { user_name: 'audio' }, 0);
      slicedPromise.then(featureData => {
        this.featureData = featureData;
      });
      audioUrlPromise.then(audioUrl => {
        this.audioUrl = audioUrl;
      })
      soundPromise.then(sound => {
        this.sound = sound;
      })
    }
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
