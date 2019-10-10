
let app = null;

class FeatureData {
  constructor(
    binaryData, dimensions, sampleFrequency, sampleDuration, metadata) {

    this.metadata = metadata;
    this.binaryData = binaryData;
    const dimProduct = dimensions.reduce((x, y) => x * y, 1);

    if(dimProduct !== this.binaryData.length) {
      throw new RangeError(
        "The product of dimensions must equal binaryData.length");
    }
    this.dimensions = dimensions;
    this.sampleFrequency = sampleFrequency;
    this.sampleDuration = sampleDuration;

    const dims = Array.from(dimensions).reverse();
    const strides = dims.reduce((arr, item) => {
      const previous = (arr[arr.length - 1] || 1);
      arr.push(item * previous);
      return arr;
    }, [1]);
    strides.reverse();
    this.strides = strides.slice(1);
  }

  get rank() {
    return this.dimensions.length;
  }

  get length() {
    return this.dimensions[0];
  }

  get durationSeconds() {
    return this.sampleFrequency * this.length;
  }

  item(indices) {
    let index = 0;
    for(let i = 0; i < this.strides.length; i++) {
      index += indices[i] * this.strides[i];
    }
    return this.binaryData[index];
  }

  slice(start, end) {
    const latterDimensions = this.dimensions.slice(1);
    const stride = latterDimensions.reduce((x, y) => x * y, 1);
    const startIndex =
      start === undefined ? 0 : start * stride;
    const endIndex =
      end === undefined ?
      this.binaryData.length : Math.min(this.binaryData.length, end * stride);

    let newFirstDimension = (endIndex - startIndex) / stride;
    const newDimensions = [newFirstDimension].concat(latterDimensions);

    const subarray = this.binaryData.subarray(startIndex, endIndex);
    return new FeatureData(
      // Use subarray so that the same underlying buffer is used
      subarray,
      newDimensions,
      this.sampleFrequency,
      this.sampleDuration,
      this.metadata
    );
  }

  timeSlice(startSeconds, durationSeconds) {
    const startIndex = Math.floor(startSeconds / this.sampleFrequency);
    const endIndex =
      startIndex + Math.floor(durationSeconds / this.sampleFrequency);
    const sliced = this.slice(startIndex, endIndex);
    return sliced;
  }
}

const debounced = (element, event, func, debounce) => {
  let timeout = null;
  const f = function(event) {
    if(timeout !== null) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(function() {
      func();
    }, debounce);
  };
  element.addEventListener(event, f);
  return f;
};

const onScroll = (element, func, debounce=100) => {
  return debounced(element, 'scroll', func, debounce);
};

const onResize = (element, func, debounce=100) => {
  return debounced(element, 'resize', func, debounce);
};


const isVisible = (element) => {
  // Check if the element intersects vertically with window
  const windowTop = window.scrollY;
  const windowBottom = windowTop + window.outerHeight;
  const elementTop = element.getBoundingClientRect().top + window.pageYOffset;
  const elementBottom = elementTop + element.clientHeight;
  if(elementBottom < windowTop || elementTop > windowBottom) {
    return false;
  }
  return true;
};

const scrolledIntoView = (element) => {
  let eventHandler = [];

  const promise = new Promise(function(resolve, reject) {
    if(isVisible(element)) {
      resolve(element);
      return;
    }

    function checkVisibility(event) {
      if(isVisible(element)) {
        document.removeEventListener('scroll', checkVisibility);
        resolve(element);
      }
    }

    const handler = onScroll(document, checkVisibility, 100);
    eventHandler.push(handler);
  });

  return [eventHandler, promise];
};

const context = new (window.AudioContext || window.webkitAudioContext)();

class AnnotateApiClient {

  constructor(username, password, apiHost) {
    this.username = username;
    this.password = password;
    this.apiHost = apiHost;
  }

  buildUri(path) {
    return this.apiHost + path;
  }

  get authHeaderValue() {
    const credentials = btoa(`${this.username}:${this.password}`);
    return `Basic ${credentials}`;
  }

  get authHeaders() {
    const headers = new Headers();
    headers.append('Authorization', this.authHeaderValue);
    return headers;
  }

  getResource(url, method='GET', data=null) {
    let headers = this.authHeaders;
    if (data) {
      headers = new Headers(headers);
      headers.append('Content-Type', 'application/json');
    }
    return fetch(url, {
      headers,
      mode: 'cors',
      method,
      body: data ? JSON.stringify(data) : null
    }).then(resp => {
      if (resp.status >= 400) {
        throw Error(resp.statusText);
      }
      return method == 'GET' ? resp.json() : {};
    });
  }

  getUserByName(userName) {
    const url = this.buildUri(`/users?user_name=${userName}`);
    return this.getResource(url);
  }

  getUser(userId) {
    const url = this.buildUri(`/users/${userId}`);
    return this.getResource(url);
  }

  getUsers(
    userName=null,
    userType=null,
    pageSize=100,
    pageNumber=0,
    order='desc') {

    let url = this.buildUri(
      `/users?page_size=${pageSize}&page_number=${pageNumber}&order=${order}`);
    if (userName) {
      url += `&user_name=${userName}`;
    }
    if (userType) {
      url += `&user_type=${userType}`;
    }
    return this.getResource(url);
  }

  getSounds(rawQuery=null, pageSize=100, pageNumber=0, order='desc') {
    let url = this.buildUri(
      `/sounds?page_size=${pageSize}&page_number=${pageNumber}&order=${order}`);
    if (rawQuery) {
      url += `&tags=${encodeURIComponent(rawQuery)}`;
    }
    return this.getResource(url);
  }

  getSoundsByUser(
    userId,
    rawQuery=null,
    pageSize=100,
    pageNumber=0,
    order='desc',
    withTags=true) {
    let url = this.buildUri(
      `/users/${userId}/sounds?page_size=${pageSize}&page_number=${pageNumber}&order=${order}`);
    if (rawQuery) {
      url += `&tags=${encodeURIComponent(rawQuery)}`;
    }
    if (withTags) {
      url += `&with_tags=true`;
    }
    return this.getResource(url);
  }

  getSound(soundId) {
    const url = this.buildUri(`/sounds/${soundId}`);
    return this.getResource(url);
  }

  getAnnotations(
    rawQuery=null,
    pageSize=100,
    pageNumber=0,
    order='desc',
    withTags=true) {

    let url = this.buildUri(
      `/annotations?page_size=${pageSize}&page_number=${pageNumber}&order=${order}`);
    if (rawQuery) {
      url += `&tags=${encodeURIComponent(rawQuery)}`;
    }
    if (withTags) {
      url += '&with_tags=true';
    }
    return this.getResource(url);
  }

  getAnnotationsByUser(
    userId,
    rawQuery=null,
    pageSize=100,
    pageNumber=0,
    order='desc',
    withTags=true) {

      let url = this.buildUri(
        `/users/${userId}/annotations?page_size=${pageSize}&page_number=${pageNumber}&order=${order}`);
      if (rawQuery) {
        url += `&tags=${encodeURIComponent(rawQuery)}`;
      }
      if (withTags) {
        url += '&with_tags=true';
      }
      return this.getResource(url);
  }

  getSoundAnnotations(
    soundId,
    rawQuery=null,
    pageSize=100,
    pageNumber=0,
    order='desc',
    withTags=true,
    timeRange=null) {

    let url = this.buildUri(
      `/sounds/${soundId}/annotations?page_size=${pageSize}&page_number=${pageNumber}&order=${order}`);
    if (rawQuery) {
      url += `&tags=${encodeURIComponent(rawQuery)}`;
    }

    if (withTags) {
      url += `&with_tags=true`;
    }

    if (timeRange) {
      url += `&time_range=${timeRange.start}-${timeRange.end}`;
    }
    return this.getResource(url);
  }

  getSoundAnnotationsByUser(soundId, userId, pageSize=100) {
    const url = this.buildUri(
      `/sounds/${soundId}/annotations?created_by=${userId}&page_size=${pageSize}`);
    return this.getResource(url);
  }

  getFeatureBots(pageSize=100) {
    const url = this.buildUri(
      `/users?user_type=featurebot&page_size=${pageSize}`);
    return this.getResource(url);
  }

  createAnnotation(soundId, startSeconds, durationSeconds, tags=null) {
    const url = this.buildUri(`/sounds/${soundId}/annotations`);
    return this.getResource(url, 'POST', {
      annotations: [
          {
            start_seconds: startSeconds,
            duration_seconds: durationSeconds,
            tags: tags
          }
      ]
    })
  }

  createUser(name, email, password, infoUrl, aboutMe) {
    const url = this.buildUri('/users');
    return this.getResource(url, 'POST', {
      user_name: name,
      email,
      password,
      info_url: infoUrl,
      about_me: aboutMe,
      user_type: 'human'
    });
  }
}


const fetchBinary = (url) => {
  return new Promise(function(resolve, reject) {
      const xhr = new XMLHttpRequest();
      xhr.open('GET', url);
      xhr.responseType = 'arraybuffer';
      xhr.onload = function() {
          if(this.status >= 200 && this.status < 300) {
              resolve(xhr.response);
          } else {
              reject(this.status, xhr.statusText);
          }
      };
      xhr.onerror = function() {
          reject(this.status, xhr.statusText);
      };
      xhr.send();
  });
};

const audioCache = {};

const fetchAudio = (url, context) => {
  const cached = audioCache[url];
  if(cached !== undefined) {
      return cached;
  }

  const audioBufferPromise = fetchBinary(url)
      .then(function(data) {
          return new Promise(function(resolve, reject) {
              context.decodeAudioData(data, (buffer) => resolve(buffer));
          });
      });
   audioCache[url] = audioBufferPromise;
   return audioBufferPromise;
};

const playAudio = (url, context, start, duration) => {
  fetchAudio(url, context)
    .then((audioBuffer) => {
        const source = context.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(context.destination);
        source.start(0, start, duration);
    });
};

const playAudioElement = (url, start, duration) => {
  const sound = document.createElement('audio');
  sound.src = url;
  sound.currentTime = start;
  sound.play();
  setTimeout(() => sound.pause(), duration * 1000);
};

const promiseContext = (promise, dataFunc) => {
  return new Promise(function(resolve, reject) {
    return promise.then(data => {
      resolve({
        data,
        ...(dataFunc(data))
      });
    })
  });
};

const timeFactors = {
  'ps': 1e12
}

const decodeBase64EncodedTimeValue = (s, unit) => {
  const timeFactor = timeFactors[unit];

  if(timeFactor === undefined) {
    throw new Error(`No time factor defined for time unit: ${unit}`);
  }

	const decoded = atob(s);
  const encoded = new Uint8Array(decoded.split('').map(x => x.charCodeAt()));
  const arr = new BigUint64Array(encoded.buffer);
  const value = Number(arr[0]);
  return value / timeFactor;
};

const unpackFeatureData = (data) => {
  const view = new DataView(data);
  const byteView = new Uint8Array(data);
  const length = new Uint32Array(data, 0, 4)[0];

  // TODO: Should I use TextDecoder here?
  const rawMetadata = String.fromCharCode.apply(
    null, new Uint8Array(data, 4, length));
  const metadata = JSON.parse(rawMetadata);

  // Decode the sample frequency and duration of the first time dimension
  const timeDimension = metadata.dimensions[0];
  const [rawFrequency, freqUnit] = timeDimension.data.frequency;
  const [rawDuration, durationUnit] = timeDimension.data.duration;

  const freq = decodeBase64EncodedTimeValue(rawFrequency, freqUnit);
  const duration = decodeBase64EncodedTimeValue(rawDuration, durationUnit);

  // TODO: Array type should be dictated by metadata and not
  // hard-coded
  const rawFeatures = new Float32Array(byteView.slice(4 + length).buffer);
  return featureData = new FeatureData(
    rawFeatures,
    metadata.shape,
    freq,
    duration,
    metadata);
};

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

const fetchAudioForSound = (sound) => {
  const audioUrl = sound.low_quality_audio_url || sound.audio_url;
  return new Promise(function(resolve, reject) {
    return fetchAudio(audioUrl, context).then(buffer => {
      resolve({
        buffer,
        audioUrl,
        soundUri: `/sounds/${sound.id}`,
        sound: sound
       });
    });
  });
};

const featurePromise = (
  sound,
  featureDataMapping,
  feature,
  startSeconds,
  durationSeconds=null,
  soundMapping=null) => {

  // Check if we've already fetched features for this sound
  let featureDataPromise = featureDataMapping[sound];

  if (featureDataPromise === undefined) {

    // check if we've at least pre-fecthed the sound metadata
    let soundMetadataPromise = null;
    if (soundMapping && soundMapping[sound]) {
      soundMetadataPromise = new Promise(function(resolve, reject) {
        resolve(soundMapping[sound]);
      });
    } else {
      const apiClient = getApiClient();
      soundMetadataPromise = apiClient.getResource(apiClient.buildUri(sound));
    }

    featureDataPromise = soundMetadataPromise.then(fetchAudioForSound);


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

  const About = Vue.component('about', {
    template: '#about-template'
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
    props: {
      width: Number,
      featureData: Object,
      audioUrl: String,

      // The starting point (in seconds) of the enclosing sound view within
      // the larger/complete sound
      startSeconds: Number,

      // start seconds for the selection, relative to startSeconds
      selectionStartSeconds: {
        type: Number,
        default: 0
      },
      selectionDurationSeconds: {
        type: Number,
        default: 0
      }
    },
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
    watch: {
      featureData: function() {
        this.setupPoints();
      }
    },
    methods: {
      setupPoints: function() {
        if (!this.featureData) {
          return;
        }
        this.pointA =
          this.selectionStartSeconds / this.featureData.durationSeconds;
        this.pointB =
          (this.selectionStartSeconds + this.selectionDurationSeconds)
          / this.featureData.durationSeconds;
      },
      playSelection: function() {
        const span = this.absoluteSpan();
        playAudio(
          this.audioUrl, context, span.startSeconds, span.durationSeconds);
      },
      confirmAnnotation: function(event) {
        this.$emit('save-annotation', {
          tags: event.tags,
          ...this.absoluteSpan()
        });
        this.clearSelection();
      },
      timeRangeSearch: function() {
        this.$emit('time-range-search', this.absoluteSpan());
      },
      clearSelection: function() {
        this.pointA = this.pointB = null;
      },
      absoluteSpan: function() {
        const span = this.span();
        return {
          startSeconds: this.startSeconds + span.startSeconds,
          durationSeconds: span.durationSeconds
        };
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
        this.$refs.container.removeEventListener(
          'mousemove', this.updatePointB);
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
        this.$refs.container.removeEventListener(
          'mousemove', this.updateLaterPoint);
        this.$refs.container.removeEventListener(
          'mousemove', this.updatePointB);
        this.$refs.container.addEventListener(
          'mousemove', this.updateEarlierPoint);
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
        this.$refs.container.removeEventListener(
          'mousemove', this.updateEarlierPoint);
        this.$refs.container.removeEventListener(
          'mousemove', this.updatePointB);
        this.$refs.container.addEventListener(
          'mousemove', this.updateLaterPoint);
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
        this.$refs.container.removeEventListener(
          'mousemove', this.updateEarlierPoint);
        this.$refs.container.removeEventListener(
          'mousemove', this.updateLaterPoint);
      },
    },
    mounted: function() {
      this.setupPoints();
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
      sound: Object,
      selectionStartSeconds: {
        type: Number,
        default: 0
      },
      selectionDurationSeconds: {
        type: Number,
        default: 0
      }
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
      timeRangeSearch: function(event) {
        const start = event.startSeconds.toFixed(4);
        const end = (event.startSeconds + event.durationSeconds).toFixed(4);
        this.$router.push({
          name: 'sound-annotations',
          params: { id: this.sound.id },
          query: { timeRange: `${start}-${end}` }
        });
      },
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
        this.$emit('play-audio', {
          audioUrl: this.audioUrl,
          startSeconds,
          durationSeconds
        });
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
          // since the coordinate system goes from top to bottom, we'll need to
          // invert the order we draw features in
          const featureIndex = featureDim - 1 - Math.floor(y * featureRatio);

          // normalize to the range 0-1 based on statistics from the metadata
          const maxValue = this.featureData.metadata.max_value;
          const rawValue = this.featureData.item([timeIndex, featureIndex]);
          const value =  rawValue / maxValue;

          const colorMapIndex = Math.floor(255 * value);

          // Translate the scalar value into color space
          imageData.data[i] = COLOR_MAP[colorMapIndex][0];
          imageData.data[i + 1] = COLOR_MAP[colorMapIndex][1];
          imageData.data[i + 2] = COLOR_MAP[colorMapIndex][2];

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

  const SmallCreativeCommonsLicense = Vue.component(
    'small-creative-commons-license', {
      template: '#small-creative-commons-license-template',
      props: ['licenseUri'],
      computed: {
        licenseId: function() {
          const segments = this.licenseUri.split('/');
          return segments[segments.length - 2];
        },
        iconUrl: function() {
          return `https://mirrors.creativecommons.org/presskit/buttons/80x15/svg/${this.licenseId}.svg`;
        }
      }
  });

  const CreativeCommonsAttributes = Vue.component(
    'creative-commons-attributes', {
      template: '#creative-commons-attributes-template',
      props: ['licenseUri'],
      computed: {
        licenseId: function() {
          const segments = this.licenseUri.split('/');
          return segments[segments.length - 2];
        },
        licenseSegments: function() {
          return ['cc'].concat(this.licenseId.split('-'));
        },
        iconUrls: function() {
          return this.licenseSegments.map(x =>
            `https://mirrors.creativecommons.org/presskit/icons/${x}.svg`);
        },
        licenseDisplayName: function() {
          return this.licenseId.toUpperCase();
        }
      }
  });

  const SimilarSoundsLink = Vue.component('similar-sounds-link', {
    template: '#similar-sounds-link-template',
    props: {
      similarityQuery: Object
    },
    data: function() {
      return {

      };
    },
    methods: {
      similarSoundsRequested: function() {
        this.$emit('similar-sounds-requested', this.similarityQuery);
      }
    }
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
        sound: null,
        similarityQuery: null,
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
      },
      similarSoundsRequested: function() {
        this.$emit('similar-sounds-requested', this.similarityQuery);
      },
      audioPlayed: function(event) {
        this.similarityQuery = {
          sound: this.sound,
          ...event
        };
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

  const Icon = Vue.component('icon', {
    template: '#icon-template',
    props: ['iconName']
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


  const MarkDown = Vue.component('markdown', {
    props: {
      remoteUrl: String
    },
    data : function() {
      return {
        markdown: null
      };
    },
    template: '#markdown-template',
    beforeMount: function() {
      fetch(this.remoteUrl)
        .then(resp => resp.text())
        .then(text => {
          this.markdown = new showdown.Converter().makeHtml(text);
        })
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
    options.props = options.props || [];
    options.computeFromQuery = options.computeFromQuery || {};
    options.serializeToQuery = options.serializeToQuery || {};
    options.queryParams =
      ['query', 'pageNumber', ...(options.queryParams || [])];

    // Ensure that page numbers are interpreted as integers if another
    // page number computation has not been specified
    const pageNumberFunc = (query) =>
      query.pageNumber ? Number.parseInt(query.pageNumber) : 0;
    options.computeFromQuery.pageNumber =
      options.computeFromQuery.pageNumber || pageNumberFunc;

    // Ensure that we have a callable function to extract a value from the
    // route object for each query parameter we'd like to keep track of
    options.queryParams.forEach(qp => {
      options.computeFromQuery[qp] =
        options.computeFromQuery[qp] || ((query) => query[qp]);
      options.serializeToQuery[qp] =
        options.serializeToQuery[qp] || (function() { return this[qp]; })
    });

    return Vue.component(componentName, {
      template: options.template,
      props: options.props,
      beforeRouteUpdate: function(to, from, next) {
        this.queryParams.forEach(qp => {
          this[qp] = options.computeFromQuery[qp](to.query);
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
          queryParams: ['query', 'pageNumber', ...options.queryParams]
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
          if (this.onSubmit) {
            this.onSubmit();
          }
          if (pushHistory) {
            const query = {};
            this.queryParams.forEach(qp => {
                if (this[qp]) {
                  query[qp] = options.serializeToQuery[qp].call(this);
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
          this[qp] = options.computeFromQuery[qp](this.$route.query);
        });
        this.handleSubmit(pushHistory=false);
      }
    });
  };

  const soundSearchPage = (componentName, options) => {
    options.afterFeatureInit = options.afterFeatureInit || (() => {});
    return searchPage(componentName, {
      template: '#sound-results-template',
      props: options.props,
      pageSize: 10,
      computeFromQuery: options.computeFromQuery,
      serializeToQuery: options.serializeToQuery,
      queryParams: options.queryParams,
      data: function() {
        return {
          currentFeature: {
            user_name: 'audio'
          },
          allFeatures: [],
          placeHolderText: options.placeHolderText,
          showMap: false,
          similarityQuery: {}
        };
      },
      initialize: function() {
        this.allFeatures.push(this.currentFeature);
        getApiClient().getFeatureBots()
          .then(data => {
            this.allFeatures = this.allFeatures.concat(data.items);
            this.afterFeatureInit();
          });
      },
      methods: {
        onSubmit: function() {
          this.mapClosed();
        },
        mapClosed: function() {
          this.showMap = false;
          this.similarityQuery = {};
        },
        similarSoundsRequested: function(event) {
          this.showMap = true;
          this.similarityQuery = event;
        },
        changeFeature: function() {
          this.handleSubmit();
        },
        setQuery: function(tag) {
          this.query = tag;
          this.newSearch();
        },
        afterFeatureInit: options.afterFeatureInit
      },
      fetchData: options.fetchData,
      transformResults: options.transformResults
    });
  };

  function transformSoundResults (items) {
    // First, build a mapping from URIs to sound metadata to avoid refetching
    // each sound in the results list
    const soundMapping = {};
    items.forEach(sound => {
      const uri = `/sounds/${sound.id}`;
      soundMapping[uri] = sound;
    });

    const sounds = items.map(item => {
      const uri = `/sounds/${item.id}`;
      const annotation = {
        sound: uri,
        created_by: item.created_by,
        created_by_user_name: item.created_by_user_name,
        date_created: item.date_created,
        start_seconds: 0,
        duration_seconds: item.duration_seconds,
        end_seconds: item.duration_seconds,
        tags: item.tags,
        featurePromise: () => {
          return featurePromise(
            uri,
            {},
            this.currentFeature,
            0,    // start seconds
            null, // duration seconds
            soundMapping)
        }
      };
      return annotation;
    });
    return sounds;
  }

  const Sounds = soundSearchPage('sounds', {
    placeHolderText: 'E.g. train, test or validation',
    fetchData: function(query, pageSize, pageNumber) {
      return getApiClient()
        .getSounds(query, pageSize, pageNumber);
    },
    transformResults: transformSoundResults
  });

  const UserSounds = soundSearchPage('user-sounds', {
    props: ['id'],
    placeHolderText: 'E.g. train, test or validation',
    fetchData: function(query, pageSize, pageNumber) {
      return getApiClient()
        .getSoundsByUser(this.id, query, pageSize, pageNumber);
    },
    transformResults: transformSoundResults
  });

  function tranformAnnotationResults (items) {
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
  }

  const UserAnnotations = soundSearchPage('user-annotations', {
    props: ['id'],
    placeHolderText: 'E.g. snare, kick, or crunchy',
    fetchData: function(query, pageSize, pageNumber) {
      return getApiClient().getAnnotationsByUser(
        this.id, query, pageSize, pageNumber);
    },
    afterFeatureInit: function() {
      const feature = this.allFeatures.find(x => x.id === this.id);
      if (feature) {
        this.currentFeature = feature;
      }
    },
    transformResults: tranformAnnotationResults
  });

  const SoundAnnotations = soundSearchPage('sound-annotations', {
    props: ['id'],
    placeHolderText: 'E.g. snare, kick, or crunchy',
    queryParams: ['timeRange'],
    data: function() {
      return {
        timeRange: null
      };
    },
    computeFromQuery: {
      timeRange: function(query) {
        if (query.timeRange) {
          const segments = query.timeRange.split('-');
          return {
            start: parseFloat(segments[0]),
            end: parseFloat(segments[1])
          }
        }
        return null;
      }
    },
    serializeToQuery: {
      timeRange: function() {
        return `${this.timeRange.start.toFixed(4)}-${this.timeRange.end.toFixed(4)}`;
      }
    },
    fetchData: function(query, pageSize, pageNumber) {
      return getApiClient().getSoundAnnotations(
          this.id,
          query,
          pageSize,
          pageNumber,
          'desc',  // order
          true,   // with tags
          this.timeRange // time range
      );
    },
    transformResults: tranformAnnotationResults
  });

  const Annotations = soundSearchPage('annotations', {
    placeHolderText: 'E.g. snare, kick, or crunchy',
    fetchData: function() {
      return getApiClient()
        .getAnnotations(this.query, this.pageSize, this.pageNumber);
    },
    transformResults: tranformAnnotationResults
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
    template: '#sign-in-template',
    data: function() {
      return {
        error: false,
        user: {
          name: null,
          password: null,
          data: null
        }
      };
    },
    methods: {
      signIn : function(event) {
        this.error = false;
        auth
          .refreshUserIdentity(this.user.name, this.user.password)
          .then(data => {
            this.user.data = data;
            EventBus.$emit('user-signed-in', this.user);
          })
          .catch(error => {
            this.user.name = null;
            this.user.password = null;
            this.error = true;
          });
      }
    }
  });

  const Tags = Vue.component('tags', {
    template: '#tags-template',
    props: ['tags']
  });


  const SoundMetaData = Vue.component('sound-metadata', {
      props: {
        sound: Object,
        titleIsLink: {
          type: Boolean,
          default: false
        },
        startSeconds: {
          type: Number,
          default: 0
        },
        durationSeconds: {
          type: Number,
          default: 0
        }
      },
      template: '#sound-metadata-template',
      data: function() {
        return {
          timeago: timeAgo,
        };
      },
      computed: {
        createdByUserId: function() {
          return this.sound.created_by.split('/').pop();
        }
      },
  });

  const Sound = Vue.component('sound', {
    props: {
      id: String,
      startSeconds: {
        type: Number,
        default: 0
      },
      durationSeconds: {
        type: Number,
        default: 0
      }
    },
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

  const Map = Vue.component('explorer', {
    template: '#map-template',
    props: ['similarityQuery'],
    data: function() {
      return {
        map: null,
        markers: [],
        spatialIndexUserId: null,
        sound: null,
        currentItem: null
      };
    },
    watch: {
      similarityQuery: function() {
        this.displaySimilar();
      }
    },
    methods: {
      displaySimilar: function() {
        this.clearMarkers();
        const soundId = this.similarityQuery.sound.id;
        const startSeconds = this.similarityQuery.startSeconds;
        this.similarTo(soundId, startSeconds)
          .then(data => {
            const coordinate = this.sphericalToGeo(data.query);
            this.map.setCenter(coordinate);
            this.markers = data.items.map(this.transformResult);
          });
      },
      closed: function() {
        this.$emit('closed', {});
      },
      getHexColor: function(scalar, scale) {
        let value = (scale + Math.round(scalar * scale)).toString(16);
        if (value.length === 1) {
          value = '0' + value;
        }
        return value;
      },
      getIcon: function(item) {
        const scale = 128;
        const red = this.getHexColor(item.point[0], scale);
        const green = this.getHexColor(item.point[1], scale);
        const blue = this.getHexColor(item.point[2], scale);
        const fillColor = `#${red}${green}${blue}`;
        return {
            path: "M-20,0a20,20 0 1,0 40,0a20,20 0 1,0 -40,0",
            fillColor: fillColor,
            fillOpacity: 0.6,
            anchor: new google.maps.Point(0,0),
            strokeWeight: 0,
            scale: this.map.getZoom() / 22
        };
      },
      degreesToRadians: function(degree) {
        return degree * (Math.PI / 180);
      },
      radiansToDegrees: function(radian) {
        return radian * (180 / Math.PI);
      },
      geoToSpherical: function(coordinate) {
        const lat = this.degreesToRadians(coordinate.lat());
        const lng = this.degreesToRadians(coordinate.lng());
        const r = 1;
        const x = r * Math.cos(lat) * Math.cos(lng);
        const y = r * Math.cos(lat) * Math.sin(lng);
        const z = r * Math.sin(lat);
        return {x, y, z};
      },
      sphericalToGeo: function(coordinate) {
        const [x, y, z] = coordinate;
        const lat = this.radiansToDegrees(Math.asin(z));
        let lng = 0;
        if (x > 0) {
          lng = this.radiansToDegrees(Math.atan(y / x));
        } else if (y > 0) {
          lng = this.radiansToDegrees(Math.atan(y / x)) + 180;
        } else {
          lng = this.radiansToDegrees(Math.atan(y / x)) - 180;
        }
        return { lat, lng };
      },
      searchNearPoint: function(mapCoordinate) {
        const spherical = this.geoToSpherical(mapCoordinate);
        const {x, y, z} = spherical;
        const uri =
          `${cochleaAppSettings.remoteSearchHost}?x=${x}&y=${y}&z=${z}`;
        return fetch(uri)
          .then(resp => resp.json());
      },
      similarTo: function(soundId, time) {
        google.maps.event.clearListeners(this.map, 'idle');
        this.map.addListener('idle', this.onMapMoveComplete);
        const uri =
          `${cochleaAppSettings.remoteSearchHost}?sound_id=${soundId}&time=${time}`;
        return fetch(uri)
          .then(resp => resp.json());
      },
      clearMarkers: function() {
        this.markers.forEach(marker => marker.setMap(null));
        this.markers = [];
      },
      transformResult: function(item, index) {
        const point = item.point;
        const geo = this.sphericalToGeo(item.point);
        const marker = new google.maps.Marker({
          position: geo,
          map: this.map,
          data: item,
          icon: this.getIcon(item)
        });
        const self = this;
        marker.addListener('click', function() {
          getApiClient()
            .getSound(this.data.sound.split('/').pop())
            .then(data => {
              self.sound = data;
              self.currentItem = item;
              playAudioElement(
                data.low_quality_audio_url,
                item.start_seconds,
                item.duration_seconds);
            });
        });
        return marker;
      },
      setupMap: function(center) {
        const map = new google.maps.Map(this.$refs.container, {
          disableDefaultUI: true,
          mapTypeId: google.maps.MapTypeId.ROADMAP,
          backgroundColor: '#FFFFFF',
          zoom: 7,
          center,
          restriction: {
              latLngBounds: {
                  north: 85,
                  south: -85,
                  west: -180,
                  east: 180
              },
              strictBounds: true,
          },
        });
        map.setOptions({
          styles: [
              {
                featureType: "all",
                stylers: [{ visibility: "off" }]
              }
            ]
        });
        return map;
      },
      onMapMoveComplete: function() {
        this.clearMarkers();
        // get the map center and convert it to a spherical coordinate
        const center = this.map.getCenter();
        this.searchNearPoint(center)
          .then(data => {
            this.markers = data.items.map(this.transformResult);
          });
      }
    },
    mounted: function() {
      const austin = {lat: 29.9, lng: -97.35};
      this.map = this.setupMap(austin);
      getApiClient()
        .getUserByName('spatial_index')
        .then(data => {
          this.spatialIndexUserId = data.items[0].id;
        });
      if (this.similarityQuery) {
        this.displaySimilar();
      }
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

      // Annotations
      { path: routerPath('/annotations'), name: 'annotations', component: Annotations},
      { path: routerPath('/users/:id/annotations'), name: 'user-annotations', component: UserAnnotations, props: true},
      { path: routerPath('/sounds/:id/annotations'), name: 'sound-annotations', component: SoundAnnotations, props: true},

      { path: routerPath('/'), name: 'root', component: About},
      { path: routerPath('/about'), name: 'about', component: About},

      // Sounds
      {
        path: routerPath('/sounds/:id/'),
        name: 'sound',
        component: Sound,
        props: (route) => {
          const props = {
            startSeconds: Number.parseFloat(route.query.startSeconds) || 0,
            durationSeconds: Number.parseFloat(route.query.durationSeconds) || 0,
            ...route.params
          };
          return props;
        }
      },
      { path: routerPath('/sounds'), name: 'sounds', component: Sounds },
      { path: routerPath('/users/:id/sounds'), name: 'user-sounds', component: UserSounds, props: true},

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
        this.$router.push({ name: 'about' });
      },
      homeLink: function() {
        return { name: 'about' };
      },
      userAuthenticated: function(user) {
        this.user.name = user.name;
        this.user.password = user.password;
        this.user.data = user.data;
        this.$router.push(this.homeLink());
      },
      viewingAuthScreen: function() {
        return ['sign-in', 'register'].includes(this.$route.name);
      }
    },
    mounted: function() {
      this.initializeCredentials();
      const authed = this.isAuthenticated();
      const attemptingAuth = this.viewingAuthScreen();

      // If the user is alreay authorized and they are attempting to
      // authorize again, OR if they are not authed and are attempting to view
      // an authorized-only page, redirect to the home link
      if ((authed && attemptingAuth) || (!authed && !attemptingAuth)) {
        this.$router.push(this.homeLink());
      }

      const globalMessageDuration = 5 * 1000;

      EventBus.$on('user-created', this.userAuthenticated);
      EventBus.$on('user-signed-in', this.userAuthenticated);
      EventBus.$on('global-message', (event) => {
        console.log('global message', event);
        this.globalMessage = event;
        setTimeout(() => this.globalMessage = null, globalMessageDuration);
      });
    },
  }).$mount('#app');
});
