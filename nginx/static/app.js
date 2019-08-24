
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

const addTemplate = (templateSelector, parentElement) => {
  const template = document.querySelector(templateSelector);
  const clone = document.importNode(template.content, true);
  parentElement.appendChild(clone);
};

const onClick = (selector, handler) => {
  document.addEventListener('click', function(event) {
    let matching = false;
    if(selector instanceof Element) {
      matching = event.target === selector;
    } else {
      matching = event.target.matches(selector);
    }
    if(matching) {
      event.preventDefault();
      handler(event);
    }
  });
};

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

Vue.component('feature-view', {
  data: function() {
    return {
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
  template: '#sound-view-template'
});

class FeatureView {
  constructor(parentElement, promiseFunc, soundUri, offsetSeconds=0) {

    const template = document.querySelector('#sound-view-template');
    const clone = document.importNode(template.content, true);
    const canvas = clone.querySelector('canvas');
    const container = clone.querySelector('.sound-view-container');
    const outerContainer = clone.querySelector('.sound-view-outer-container');

    this.soundUri = soundUri;
    this.offsetSeconds = offsetSeconds;
    this.container = container;
    this.outerContainer = outerContainer;
    this.canvas = canvas;
    this.drawContext = canvas.getContext('2d');
    this.parentElement = parentElement;
    this.parentElement.appendChild(clone);
    this.zoom = 1;
    this.featureData = undefined;

    const id = Math.random();

    scrolledIntoView(this.container)
      .then(() => {
        const [slicedPromise, audioUrlPromise] = promiseFunc();

        audioUrlPromise.then(audioUrl => {
          this.audioUrl = audioUrl;

          // This handler depends on the audio being loaded and plays short
          // segments of audio starting at the click point
          onClick(this.canvas, (event) => {
            // the starting point in seconds relative to this slice
            const relativeStartSeconds =
              (event.offsetX / this.elementWidth) * this.featureData.durationSeconds;
            // the starting point in seconds in the sound as a whole
            const startSeconds = this.offsetSeconds + relativeStartSeconds;
            const durationSeconds =
              Math.min(2.5, this.featureData.durationSeconds - relativeStartSeconds);

            const candidateQueryEvent = new CustomEvent(
              'candidateQuery',
              { detail: {soundUri: this.soundUri, startSeconds}});
            document.dispatchEvent(candidateQueryEvent);

            playAudio(this.audioUrl, context, startSeconds, durationSeconds);
          });
        });


        slicedPromise.then(featureData => {
          this.featureData = featureData;

          // render for the first time once scrolled into view and feature data
          // is loaded
          this.draw();

          // re-draw whenever the scroll position changes
          onScroll(this.container, () => this.draw(false), 100);

          // re-draw whenever the window is resized
          onResize(window, () => this.draw(true), 100);

          // click handlers to handle zoom in and out
          onClick(this.outerContainer.querySelector('.sound-view-zoom-in'), () => {
            this.setZoom(Math.min(20, this.zoom + 1));
          });
          onClick(this.outerContainer.querySelector('.sound-view-zoom-out'), () => {
            this.setZoom(Math.max(1, this.zoom - 1));
          });
        });
      });
  }

  get containerWidth() {
    return this.container.clientWidth;
  }

  clear() {
    this.drawContext.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  draw1D(stride, increment, height, imageData) {
    for(let i = 0; i < this.containerWidth; i++) {
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
        this.container.scrollLeft + i,
        (height - size) / 2,
        increment,
        size);
    }
  }

  draw2D(_, increment, height, imageData) {
    // The Uint8ClampedArray contains height × width × 4
    const timeDim = this.featureData.dimensions[0];
    const featureDim = this.featureData.dimensions[1];
    const stride = 4;

    const timeRatio = timeDim / this.elementWidth;
    const featureRatio = featureDim / imageData.height;

    for(let i = 0; i < imageData.data.length; i += stride) {
      // compute image coordinates
      const x = (i / stride) % imageData.width;
      const y = Math.floor((i / stride) / imageData.width);

      const timeIndex = Math.floor((this.container.scrollLeft + x) * timeRatio);
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
    this.drawContext.putImageData(imageData, this.container.scrollLeft, 0);
  }

  draw(preserveOffset=false) {
    this.canvas.width = this.elementWidth;
    this.canvas.style.width = `${this.zoom * 100}%`;
    this.canvas.height = this.container.clientHeight;
    this.canvas.style.height = '100%';

    this.clear();

    if(preserveOffset) {
      this.container.scrollLeft = this.offsetPercent * this.elementWidth;
    } else {
      const offsetPercent = this.container.scrollLeft / this.elementWidth;
      this.offsetPercent = offsetPercent;
    }

    if(this.featureData === undefined) {
      return;
    }

    const height = this.container.clientHeight;

    const stride = this.featureData.length / this.elementWidth;
    const increment = Math.max(1, 1 / stride);

    const imageData = this.drawContext.getImageData(
      this.container.scrollLeft,
      0,
      this.containerWidth,
      this.container.clientHeight);

    if (this.featureData.rank === 2) {
      this.draw2D(stride, increment, height, imageData);
    } else if(this.featureData.rank === 1) {
      this.draw1D(stride, increment, height, imageData);
    } else {
      throw new Error('Dimensions greater than 2 not currently supported');
    }
  }

  get elementWidth() {
    return this.containerWidth * this.zoom;
  }

  setZoom(zoom) {
    if(zoom === this.zoom) {
      return;
    }
    this.zoom = zoom;
    this.draw(true);
  }
}

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

  getResource(url) {
    return fetch(url, {headers: this.authHeaders, mode: 'cors'})
      .then(resp => {
        if (!resp.ok) {
          throw Error(resp.statusText);
        }
        return resp.json();
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

  getUsers() {
    const url = this.buildUri('/users/');
    return this.getResource(url);
  }

  getSounds(pageSize=100) {
    const url = this.buildUri(`/sounds?page_size=${pageSize}`);
    return this.getResource(url);
  }

  getSound(soundId) {
    const url = this.buildUri(`/sounds/${soundId}`);
    return this.getResource(url);
  }

  getAnnotations(rawQuery=null, pageSize=100) {
    let url = this.buildUri(`/annotations?page_size=${pageSize}`);
    if (rawQuery) {
      url += `&tags=${rawQuery}`;
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

const featurePromise = (annotation, featureDataMapping, searchResults) => {

  // Check if we've already fetched features for this sound
  let featureDataPromise = featureDataMapping[annotation.sound];


  if (featureDataPromise === undefined) {
    // audio and features have not yet been fetched
    featureDataPromise = app.annotateClient()
      // Get sound data from the API
      .getResource(app.annotateClient().buildUri(annotation.sound))
      // Fetch audio data from the remote audio url
      .then(data => {
        const audioUrl = data.low_quality_audio_url || data.audio_url;
        return new Promise(function(resolve, reject) {
          return fetchAudio(audioUrl, context).then(buffer => {
            resolve({
              buffer,
              audioUrl,
              soundUri: annotation.sound,
              soundId: data.id
             });
          });
        });
      });

      if(app.currentFeature.user_name === 'audio') {
        // If the current feature being viewed is audio, we've already fetched
        // it
        featureDataPromise = featureDataPromise
          .then(data => {
            const {buffer, audioUrl, soundUri} = data;
            const audioData = buffer.getChannelData(0);
            const frequency = 1 / buffer.sampleRate;
            const fd = new FeatureData(
              audioData, [audioData.length], frequency, frequency);
            return {featureData: fd, audioUrl};
          });
      } else {
        // The feature being viewed is other than audio and needs to be fetched
        featureDataPromise = featureDataPromise
          .then(data => {
            const {buffer, audioUrl, soundUri, soundId} = data;

            const promise = app.annotateClient().getSoundAnnotationsByUser(
              soundId, app.currentFeature.id);
            return promiseContext(promise, r => ({audioUrl}));
          })
          .then(result => {
            const {data, audioUrl} = result;
            const promise = fetchBinary(data.items[0].data_url);
            return promiseContext(promise, r => ({audioUrl}));
          })
          .then(result => {
            const {data, audioUrl} = result;
            const featureData = unpackFeatureData(data);
            return {featureData, audioUrl};
          });
      }

    // Put the pending promise into the map
    featureDataMapping[annotation.sound] = featureDataPromise;
  }

  const slicedPromise = featureDataPromise.then(data => {
    const {featureData, audioUrl} = data;
    return featureData.timeSlice(
      annotation.start_seconds, annotation.duration_seconds);
  });

  const audioUrlPromise = featureDataPromise.then(data => {
    const {featureData, audioUrl} = data;
    return audioUrl;
  });

  return [slicedPromise, audioUrlPromise];
};


// document.addEventListener('DOMContentLoaded', function() {
//   app = new Vue({
//     el: '#app',
//     data: {
//       features: [],
//       currentFeature: null,
//       textQuery: null,
//       query: null,
//       results: [],
//       candidateQuery: null,
//       remoteSearchHost: cochleaAppSettings.remoteSearchHost,
//       userName: null,
//       password: null,
//       showPassword: false
//     },
//     watch: {
//       userName: function(val) {
//         this.fetchFeatures();
//       },
//       password: function(val) {
//         this.fetchFeatures();
//       }
//     },
//     methods: {
//       fetchFeatures: function() {
//         if(!this.userName || !this.password) {
//           return;
//         }
//         // TODO: Only feature bots that create full-length, dense scalar or vector
//         // features should be included in this list.  How can those be filtered out?
//         app.annotateClient().getFeatureBots()
//           .then(data => {
//             app.features = [{user_name: 'audio'}].concat(data.items);
//             app.currentFeature = app.features[0];
//           });
//       },
//
//       annotateClient: function() {
//         return new AnnotateApiClient(
//           this.userName, this.password, cochleaAppSettings.apiHost);
//       },
//
//       queryChange: function(event) {
//         this.query = () => this.annotateClient().getAnnotations(this.textQuery);
//       },
//
//       changeFeature: function() {
//         this.handleSubmit();
//       },
//
//       handleSubmit: function() {
//         this.query()
//           .then(data => {
//             const searchResults = document.querySelector('#search-results');
//
//             // clear the results
//             while(searchResults.firstChild) {
//               searchResults.firstChild.remove();
//             }
//
//             const featureDataMapping = {};
//             data.items.forEach(annotation => {
//               const fp = () => featurePromise(
//                 annotation,
//                 featureDataMapping,
//                 searchResults,
//                 annotation.sound);
//               return new FeatureView(
//                 searchResults,
//                 fp,
//                 annotation.sound,
//                 annotation.start_seconds);
//             });
//           });
//       },
//
//       remoteSearch: function() {
//         const soundUri = this.candidateQuery.soundUri;
//         const startSeconds = this.candidateQuery.startSeconds;
//         const host = this.remoteSearchHost;
//         const uri = `${host}?sound=${soundUri}&seconds=${startSeconds}`;
//         this.textQuery = '';
//         this.query = () => fetch(uri).then(data => data.json());
//         this.handleSubmit();
//       },
//     }
//   });
//
//   document.addEventListener('candidateQuery', e => {
//     console.log('Candidate Query', e.detail);
//     app.candidateQuery = e.detail;
//   });
// });
