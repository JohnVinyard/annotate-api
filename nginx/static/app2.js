const timeAgo = timeago();

const EventBus = new Vue();

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
  const identity = auth.tryGetUserIdentity() || {};
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
    const {featureData, audioUrl, sound} = data;
    return sound;
  });

  return [slicedPromise, audioUrlPromise, soundPromise];
};

document.addEventListener('DOMContentLoaded', function() {

  const Welcome = Vue.component('welcome', {
    props: ['user'],
    template: '#welcome-template'
  });

  const NotFound = Vue.component('not-found', {
    template: '#not-found-template'
  });

  const Menu = Vue.component('main-menu', {
    template: '#menu-template'
  });

  const AddAnnotationModal = Vue.component('add-annotation-modal', {
    template: '#add-annotation-modal-template',
    props: ['featureData', 'audioUrl', 'startSeconds', 'span'],
    data: function() {
      return {
        rawTags: '',
        slicedFeatureData: null,
        modifiedStartSeconds: null
      };
    },
    computed: {
      tags: function() {
        return new Set(
          this.rawTags.split(' ').filter(x => x).map(x => x.toLowerCase()));
      }
    },
    created: function() {
      this.slicedFeatureData = this.featureData.timeSlice(
        this.span.startSeconds, this.span.durationSeconds);
      this.modifiedStartSeconds = this.startSeconds + this.span.startSeconds;
    },
    methods: {
      close: function() {
        this.$emit('modal-close');
      },
      createAnnotation: function() {
        this.$emit('confirm-annotation', { tags: Array.from(this.tags) });
        this.close();
      }
    }
  });

  const Selection = Vue.component('selection', {
    template: '#selection-template',
    props: ['width', 'featureData', 'audioUrl', 'startSeconds'],
    data: function() {
      return {
        acceptsEvents: false,
        pointA: null,
        pointB: null,
        handleWidth: 5,
        isSelecting: false,
        isAdjusting: false,
        isAddingAnnotation: false
      };
    },
    methods: {
      confirmAnnotation: function(event) {
        const span = this.span();
        this.$emit('save-annotation', {
          startSeconds: this.startSeconds + span.startSeconds,
          durationSeconds: span.durationSeconds,
          tags: event.tags
        });
        this.clearSelection();
      },
      clearSelection: function() {
        this.pointA = this.pointB = null;
      },
      span: function() {
        const start = Math.min(this.pointA, this.pointB);
        const end = Math.max(this.pointA, this.pointB);
        const startSeconds = start * this.featureData.durationSeconds;
        const endSeconds = end * this.featureData.durationSeconds;
        return {
          startSeconds,
          endSeconds,
          durationSeconds: endSeconds - startSeconds
        };
      },
      addAnnotation: function() {
        this.isAddingAnnotation = true;
      },
      closeModal: function() {
        this.isAddingAnnotation = false;
      },
      acceptEvents: function(event) {
        if (event.key !== 'Control') { return ;}
        this.acceptsEvents = true;
      },
      rejectEvents: function(event) {
        if (event.key !== 'Control') { return ;}
        this.acceptsEvents = false;
      },
      percentLocation: function(event) {
        if (event.target === this.$refs.container) {
          return event.offsetX / this.width;
        } else {
          const bounds = this.$refs.container.getBoundingClientRect();
          return (event.clientX - bounds.left) / this.width;
        }

      },
      startSelection: function(event) {
        this.isSelecting = true;
        this.pointA = this.pointB = this.percentLocation(event);
        this.$refs.container.addEventListener('mousemove', this.updatePointB);
      },
      endSelection: function(event) {
        this.isSelecting = false;
        this.$refs.container.removeEventListener('mousemove', this.updatePointB);
      },
      startPixels: function() {
        return Math.min(this.pointA, this.pointB) * this.width;
      },
      widthPixels: function() {
        return Math.abs(this.pointA - this.pointB) * this.width;
      },
      adjustLeft: function(event) {
        this.isAdjusting = true;
        this.acceptsEvents = true;
        this.$refs.container.removeEventListener('mousemove', this.updateLaterPoint);
        this.$refs.container.removeEventListener('mousemove', this.updatePointB);
        this.$refs.container.addEventListener('mousemove', this.updateEarlierPoint);
      },
      updateEarlierPoint: function(event) {
        const pos = this.percentLocation(event);
        if (this.pointA < this.pointB) {
          this.pointA = pos;
        } else {
          this.pointB = pos;
        }
      },
      adjustRight: function(event) {
        this.isAdjusting = true;
        this.acceptsEvents = true;
        this.$refs.container.removeEventListener('mousemove', this.updateEarlierPoint);
        this.$refs.container.removeEventListener('mousemove', this.updatePointB);
        this.$refs.container.addEventListener('mousemove', this.updateLaterPoint);
      },
      updatePointB: function(event) {
        this.pointB = this.percentLocation(event);
      },
      updateLaterPoint: function(event) {
        const pos = this.percentLocation(event);
        if (this.pointA > this.pointB) {
          this.pointA = pos;
        } else {
          this.pointB = pos;
        }
      },
      endAdjustments: function() {
        this.isAdjusting = false;
        this.acceptsEvents = false;
        this.$refs.container.removeEventListener('mousemove', this.updateEarlierPoint);
        this.$refs.container.removeEventListener('mousemove', this.updateLaterPoint);
      },
    },
    mounted: function() {
      document.addEventListener('keydown', this.acceptEvents);
      document.addEventListener('keyup', this.rejectEvents);
    },
    beforeDestroy: function() {
      document.removeEventListener('keydown', this.acceptEvents);
      document.removeEventListener('keyup', this.rejectEvents);
    }
  });

  const SoundView = Vue.component('sound-view', {
    template: '#sound-view-template',
    props: {
      featureData: FeatureData,
      audioUrl: String,
      startSeconds: Number,
      selectable: {
        type: Boolean,
        default: true
      },
      sound: Object
    },
    data: function() {
      return {
        zoom: 1,
        panListener: null,
        resizeHandler: null,
        rect: null,
        canvasWidth: 0
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
      saveAnnotation: function(event) {
        getApiClient()
          .createAnnotation(
            this.sound.id, event.startSeconds, event.durationSeconds, event.tags)
          .then(data => {
            EventBus.$emit('global-message', {
              message: 'Annotation Created',
              type: 'success'
            });
          })
          .catch(error => {
            EventBus.$emit('global-message', {
              message: 'Something went wrong!',
              type: 'error'
            });
          });
      },
      zoomIn: function() {
        this.zoom = Math.min(20, this.zoom + 1);
      },
      zoomOut: function() {
        this.zoom = Math.max(1, this.zoom - 1);
      },
      containerWidth: function() {
        if (this.$refs.container === undefined) {
          return 0;
        }
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
        this.canvasWidth = elementWidth;
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
        onScroll(this.$refs.container, () => this.draw(false), 100);
      // re-draw whenever the window is resized
      this.resizeHandler =
        onResize(window, () => this.draw(true), 100);
      this.draw();
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
        sound: null
      };
    },
    methods: {
      selectQuery: function(tag) {
        this.$emit('select-query', tag);
      },
      offsetSeconds: function() {
        return this.annotation.start_seconds;
      },
      soundId: function() {
        return this.annotation.sound.split('/').pop();
      },
      createdByUserId: function() {
        return this.annotation.created_by.split('/').pop();
      }
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
          const [slicedPromise, audioUrlPromise, soundPromise] =
            this.annotation.featurePromise();

          soundPromise.then(sound => {
            this.sound = sound;
          });

          audioUrlPromise.then(audioUrl => {
            this.audioUrl = audioUrl;
          });

          slicedPromise.then(featureData => {
            this.featureData = featureData;
          });
        });
    },
  });

  const UserTypeIcon = Vue.component('user-type-icon', {
    template: '#user-type-icon-template',
    props: ['userType']
  });

  const TextQuery = Vue.component('text-query', {
    template: '#text-query-template',
    props: ['query', 'placeHolderText', 'labelText'],
    watch: {
      query: function(newVal, oldVal) {
        this.textQuery = newVal;
      }
    },
    data: function() {
      return {
        textQuery: this.query
      };
    },
    methods: {
      queryChange: function() {
        this.$emit('text-query-change', this.textQuery);
      },
      newSearch: function() {
        this.$emit('new-search', this.textQuery);
      }
    }
  });

  const Pagination = Vue.component('pagination', {
    template: '#pagination-template',
    props: {
      currentPage: {
          type: Number,
          default: 0
      },
      totalPages: Number,
      maxDisplayPages : {
        type: Number,
        default: 10
      }
    },
    computed: {
      displayPages: function() {
        const display = [this.currentPage];
        if (this.totalPages === 0) {
          return display;
        }

        while (display.length <= this.maxDisplayPages) {
          const startLength = display.length;

          const nextItem = display[display.length - 1] + 1;
          if (nextItem <= this.lastPage) {
            display.push(nextItem);
          }
          const previousItem = display[0] - 1;
          if(previousItem >= 0) {
            display.unshift(previousItem);
          }

          if (display.length === startLength) {
            break;
          }
        }
        return display;
      },
      needsFirstPageLink: function() {
        return !this.displayPages.includes(0);
      },
      needsLastPageLink: function() {
        return !this.displayPages.includes(this.lastPage);
      },
      lastPage: function() {
        return Math.max(0, this.totalPages - 1);
      },
      isFirstPage: function() {
        return this.currentPage === 0;
      },
      isLastPage: function() {
        return this.currentPage === this.lastPage;
      }
    },
    methods: {
      visitFirstPage: function() {
        this.visit(0);
      },
      visitLastPage: function() {
        this.visit(this.totalPages - 1);
      },
      visitPreviousPage: function() {
        if (this.isFirstPage) { return; }
        this.visit(this.currentPage - 1);
      },
      visitNextPage: function() {
        if (this.isLastPage) { return; }
        this.visit(this.currentPage + 1);
      },
      visit: function(page) {
        this.$emit('change-page', { pageNumber: page });
      }
    }
  });

  const UserDetail = Vue.component('user', {
    props: ['id'],
    template: '#user-detail-template',
    data: function() {
      return {
        timeago: timeAgo,
        user: {},
        links: {}
      }
    },
    mounted: function() {
      getApiClient()
        .getUser(this.id)
        .then(data => {
          this.user = data;
          this.user.links.forEach(link => this.links[link.rel] = link);
        });
    },
    methods: {
      aboutMe: function() {
        return new showdown.Converter().makeHtml(this.user.about_me);
      }
    }
  });


  const UserSummary = Vue.component('user-summary', {
    props: ['user'],
    template: '#user-summary-template',
    data: function() {
      return {
        timeago: timeAgo
      };
    },
    methods: {
      aboutMeRendered: function() {
        return new showdown.Converter().makeHtml(this.user.about_me);
      }
    }
  });

  const searchPage = (componentName, options) => {
    options.initialize = options.initialize || (() => {});
    options.transformResults = options.transformResults || ((x) => x);

    return Vue.component(componentName, {
      template: options.template,
      beforeRouteUpdate: function(to, from, next) {
        this.queryParams.forEach(qp => {
          this[qp] = to.query[qp];
        });
        this.pageNumber = Number.parseInt(to.query.pageNumber) || 0;
        this.handleSubmit(pushHistory=false);
        next();
      },
      data: function() {
        const base = {
          query: null,
          pageNumber: 0,
          totalPages: 0,
          totalResults: 0,
          items: [],
          pageSize: options.pageSize || 5,
          queryParams: ['query', 'pageNumber', ...(options.queryParams || [])]
        };
        return {...base, ...options.data()};
      },
      watch: options.watch,
      methods: {
        ...options.methods,
        fetchData: options.fetchData,
        transformResults: options.transformResults,
        initialize: options.initialize,
        queryChange: function(value) {
          this.query = value;
        },
        changePage: function(event) {
          this.pageNumber = event.pageNumber;
          this.handleSubmit();
        },
        newSearch: function() {
          this.pageNumber = 0;
          this.handleSubmit();
        },
        handleSubmit: function(pushHistory=true) {
          if (pushHistory) {
            const query = {};
            this.queryParams.forEach(qp => {
                if (this[qp]) {
                  query[qp] = this[qp];
                }
            });
            this.$router.push({
              path: this.$route.path,
              query
            });
          }
          this.items = [];
          this
            .fetchData(this.query, this.pageSize, this.pageNumber)
            .then(data => {
                if (this.transformResults) {
                  this.items = this.transformResults(data.items);
                } else {
                  this.items = data.items;
                }
                this.totalResults = data.total_count;
                this.totalPages = Math.ceil(data.total_count / this.pageSize);
            });
        },
      },
      mounted: function() {
        if(this.initialize) {
          this.initialize();
        }
        this.queryParams.forEach(qp => {
          this[qp] = this.$route.query[qp];
        });
        this.handleSubmit(pushHistory=false);
      }
    });
  };

  const Annotations = searchPage('annotations', {
    template: '#annotations-template',
    pageSize: 10,
    data: function() {
      return {
        currentFeature: {
          user_name: 'audio'
        },
        allFeatures: [],
      }
    },
    initialize: function() {
      this.allFeatures.push(this.currentFeature);
      getApiClient().getFeatureBots()
        .then(data => {
          this.allFeatures = this.allFeatures.concat(data.items);
        });
    },
    fetchData: function() {
      return getApiClient()
        .getAnnotations(this.query, this.pageSize, this.pageNumber);
    },
    transformResults: function(items) {
      const annotations = items;
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
      return annotations;
    },
    methods: {
      changeFeature: function() {
        this.handleSubmit();
      },
      setQuery: function(tag) {
        this.query = tag;
        this.newSearch();
      },
    }
  });

  const UserList = searchPage('user-list', {
    template: '#users-template',
    pageSize: 5,
    queryParams: ['userType'],
    data: function() {
      return {
        userType: null
      };
    },
    watch: {
      userType: function() {
        this.newSearch();
      }
    },
    fetchData : function(query, pageSize, pageNumber) {
      return getApiClient()
        .getUsers(query, this.userType, pageSize, pageNumber);
    }
  });

  const ValidationErrors = Vue.component('validation-errors', {
    template: '#validation-errors-template',
    props: ['errors'],
  });

  const validatedField = (componentName, type, validationRules) => {
    return Vue.component(componentName, {
      template: '#validated-field-template',
      props: [
        'value',
        'fieldId',
        'labelText',
        'propertyName',
        'context',
        'placeHolderText'
      ],
      data: function() {
        return {
          internalValue: this.value,
          errors: [],
          hasBeenValidated: false,
          type
        };
      },
      computed: {
        hasErrors: function() {
          return this.hasBeenValidated && this.errors.length > 0;
        }
      },
      methods: {
        validate: function(value) {
          this.hasBeenValidated = true;
          this.errors = [];
          for(let rule of validationRules) {
            rule
              .rule(value, this.context)
              .then(result => {
                if (result) { return; }
                this.errors.push({
                  message: rule.message(value)
                });
              });
          }
        }
      },
      watch: {
        context: function(value) {
          this.validate(this.internalValue);
        },
        errors: function(value) {
          this.$emit('field-errors', {
            name: this.propertyName,
            errors: this.errors.map(x => {
              return {...x};
            })
          })
        },
        internalValue: function(value) {
          this.$emit('field-value-change', {
            name: this.propertyName,
            value: value
          });
          this.validate(value);
        }
      }
    });
  };

  function toPromise (func) {
    function f() {
      const args = Array.from(arguments);
      return new Promise(function(resolve, reject) {
        resolve(func(...args))
      });
    }
    return f;
  };

  const NameInput = validatedField('user-name-input', 'text', [
    {
      rule: (value) => {
        return fetch('http://flipacoinapi.com/json')
          .then(resp => resp.json())
          .then(data => data === 'Heads');
      },
      message: (value) => 'You must get heads'
    },
    {
      rule: toPromise(value => value.length > 2),
      message: (value) => `Name must be greater than two characters but was ${value.length} characters`
    }
  ]);

  const EmailInput = validatedField('user-email-input', 'email', [
    {
      rule: toPromise(value => {
        const pattern = /[^@]+@[^@]+\.[^@]+/g;
        return pattern.test(value);
      }),
      message: (value) => 'Please enter a valid email address'
    }
  ]);

  const InfoUrl = validatedField('user-info-url', 'url', [
    {
      rule: toPromise(value => {
        const parser = document.createElement('a');
        parser.href = value;
        return parser.protocol
            && parser.hostname
            && parser.hostname != window.location.hostname;
      }),
      message: (value) => 'Please enter a valid URL'
    }
  ]);

  const PasswordInput = validatedField('user-password-input', 'password', [
    {
      rule: toPromise(value => value.length > 5),
      message: (value) => 'Please enter a password of at least five characters'
    }
  ]);

  const PasswordConfirm = validatedField('user-password-confirm', 'password', [
    {
      rule: toPromise((value, context) => value === context),
      message: (value) => 'Passwords must match'
    }
  ]);

  const Register = Vue.component('register', {
    template: '#register-template',
    data: function() {
      return {
        name: null,
        password: null,
        passwordConfirmation: null,
        email: null,
        aboutMe: null,
        infoUrl: null,
        errors: {},
        hasErrors: false
      };
    },
    computed: {
      aboutMeMarkdown: function() {
        return new showdown.Converter().makeHtml(this.aboutMe);
      }
    },
    methods : {
      fieldValueChange: function(event) {
        this[event.name] = event.value;
      },
      fieldErrors: function(event) {
        this.errors[event.name] = event.errors;
        this.hasErrors = Object.values(this.errors)
          .map(x => x.length)
          .reduce((a, b) => a + b) > 0;
      },
      submit: function() {
        if (this.hasErrors) { return; }
        getApiClient()
          .createUser(
            this.name, this.email, this.password, this.infoUrl, this.aboutMe)
          .then(data => {
            EventBus.$emit('global-message', {
              message: 'User Created',
              type: 'success'
            });
            auth
              .refreshUserIdentity(this.name, this.password)
              .then(user => {
                  EventBus.$emit('user-created', {
                    data: user
                });
              });
          })
          .catch(error => {
            EventBus.$emit('global-message', {
              message: 'Something went wrong!',
              type: 'error'
            });
          });
      }
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

      // Landing Page
      { path: routerPath('/welcome'), name: 'welcome', component: Welcome, props: true },

      // Sign in and register
      { path: routerPath('/sign-in'), name: 'sign-in', component: SignIn, props: true },
      { path: routerPath('/register'), name: 'register', component: Register},

      // Main menu for authenticated users
      { path: routerPath('/menu'), name: 'menu', component: Menu},
      { path: routerPath('/'), name: 'menu', component: Menu},

      // Annotations
      { path: routerPath('/annotations'), name: 'annotations', component: Annotations},

      // Sounds
      { path: routerPath('/sounds'), name: 'sounds', component: Sounds },
      { path: routerPath('/sounds/:id'), name: 'sound', component: Sound, props: true},

      // Users
      { path: routerPath('/users/:id'), name: 'user', component: UserDetail, props: true},
      { path: routerPath('/users'), name: 'users', component: UserList, props: true},
      { path: routerPath('*'), name: 'not-found', component: NotFound }
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
      globalMessage: null
    },
    methods: {
      clearGlobalMessage: function() {
        this.globalMessage = null;
      },
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
      },

    },
    mounted: function() {
      this.initializeCredentials();
      if (!this.isAuthenticated()) {
        this.$router.push({ name: 'welcome', params: { user: this.user }});
      }

      EventBus.$on('user-created', event => {
          this.user.name = event.name;
          this.user.password = event.password;
          this.user.data = event.data;
          this.$router.push({ name: 'menu' });
      });

      EventBus.$on('global-message', (event) => {
        console.log('global message', event);
        this.globalMessage = event;
        setTimeout(() => this.globalMessage = null, 10 * 1000);
      });
    },
  }).$mount('#app');
});
