
const FEATURE = 'spectrogram';
// KLUDGE: Don't hardcode a user id here
const SPECTROGRAM_BOT_USER_ID = '588c2a1d0be84c69361d638210a8e';


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
      end === undefined ? this.binaryData.length : end * stride;

    const newFirstDimension = (endIndex - startIndex) / stride;
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
  element.addEventListener(event, function(event) {
    if(timeout !== null) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(function() {
      func();
    }, debounce);
  });
};

const onScroll = (element, func, debounce=100) => {
  debounced(element, 'scroll', func, debounce);
};

const onResize = (element, func, debounce=100) => {
  debounced(element, 'resize', func, debounce);
};

const scrolledIntoView = (element) => {
  return new Promise(function(resolve, reject) {

    if(isVisible(element)) {
      resolve(element);
      return;
    }

    onScroll(document, function checkVisibility(event) {
      if(isVisible(element)) {
        document.removeEventListener('scroll', checkVisibility);
        resolve(element);
      }
    }, 100);
  });
};

class FeatureView {
  constructor(parentElement, promiseFunc, offsetSeconds=0) {

    const template = document.querySelector('#sound-view-template');
    const clone = document.importNode(template.content, true);
    const canvas = clone.querySelector('canvas');
    const container = clone.querySelector('.sound-view-container');
    const outerContainer = clone.querySelector('.sound-view-outer-container');

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
          // This handler depends on the audio being loaded
          onClick(this.canvas, (event) => {
            // the starting point in seconds relative to this slice
            const relativeStartSeconds =
              (event.offsetX / this.elementWidth) * this.featureData.durationSeconds;
            // the starting point in seconds in the sound as a whole
            const startSeconds = this.offsetSeconds + relativeStartSeconds;
            const durationSeconds =
              Math.min(2.5, this.featureData.durationSeconds - relativeStartSeconds);
            playAudio(this.audioUrl, context, startSeconds, durationSeconds);
          });
        });

        slicedPromise.then(featureData => {
          this.featureData = featureData;
          this.draw();
          onScroll(this.container, () => this.draw(false), 100);
          onResize(window, () => this.draw(true), 100);
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

  constructor(username, password) {
    this.username = username;
    this.password = password;
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
    return fetch(url, {headers: this.authHeaders}).then(resp => resp.json());
  }

  getSounds(pageSize=100) {
    const url = `/sounds?page_size=${pageSize}`;
    return this.getResource(url);
  }

  getSound(soundId) {
    const url = `/sounds/${soundId}`;
    return this.getResource(url);
  }

  getAnnotations(rawQuery, pageSize=100) {
    const url = `/annotations?tags=${rawQuery}&page_size=${pageSize}`;
    return this.getResource(url);
  }

  getSoundAnnotationsByUser(soundId, userId, pageSize=100) {
    const url =
      `/sounds/${soundId}/annotations?created_by=${userId}&page_size=${pageSize}`;
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

const annotateClient = new AnnotateApiClient('musicnet', 'password');

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

const featurePromise = (annotation, featureDataMapping, searchResults) => {
  let featureDataPromise = featureDataMapping[annotation.sound];
  if(featureDataPromise === undefined) {
    featureDataPromise = annotateClient
      // Get sound data from the API
      .getResource(annotation.sound)
      // Fetch audio data from the remote audio url
      .then(data => {
        return new Promise(function(resolve, reject) {
          return fetchAudio(data.audio_url, context).then(buffer => {
            resolve({
              buffer,
              audioUrl: data.audio_url,
              soundUri: annotation.sound,
              soundId: data.id
             });
          });
        });
      });

      if(FEATURE === 'audio') {
        featureDataPromise = featureDataPromise
          .then(data => {
            const {buffer, audioUrl, soundUri} = data;
            const audioData = buffer.getChannelData(0);
            const frequency = 1 / buffer.sampleRate;
            const fd = new FeatureData(
              audioData, [audioData.length], frequency, frequency);
            return {featureData: fd, audioUrl};
          });
      } else if (FEATURE === 'spectrogram') {
        featureDataPromise = featureDataPromise
          .then(data => {
            const {buffer, audioUrl, soundUri, soundId} = data;

            const promise = annotateClient.getSoundAnnotationsByUser(
              soundId, SPECTROGRAM_BOT_USER_ID);
            return promiseContext(promise, r => ({audioUrl}));
          })
          .then(result => {
            const {data, audioUrl} = result;
            const promise = fetchBinary(data.items[0].data_url);
            return promiseContext(promise, r => ({audioUrl}));
          })
          .then(result => {
            const {data, audioUrl} = result;
            const view = new DataView(data);
            const byteView = new Uint8Array(data);
            const length = new Uint32Array(data, 0, 4)[0];
            const rawMetadata = String.fromCharCode.apply(
              null, new Uint8Array(data, 4, length));
            const metadata = JSON.parse(rawMetadata);

            // TODO: Array type should be dictated by metadata and not
            // hard-coded
            const rawFeatures = new Float32Array(
              byteView.slice(4 + length).buffer);
            const featureData = new FeatureData(
              rawFeatures,
              metadata.shape,
              metadata.dimensions[0].frequency_seconds,
              metadata.dimensions[0].duration_seconds,
              metadata);
            return {featureData, audioUrl};
          });
      } else {
        throw new Error(`Feature ${FEATURE} not supported.`);
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


const handleSubmit = (event) => {
  const rawQuery = document.querySelector('#search-criteria').value;

  annotateClient.getAnnotations(rawQuery)
    .then(data => {
      const searchResults = document.querySelector('#search-results');

      // clear the results
      while(searchResults.firstChild) {
        searchResults.firstChild.remove();
      }

      const featureDataMapping = {};
      data.items.forEach(annotation => {
        new FeatureView(
          searchResults,
          () => featurePromise(annotation, featureDataMapping, searchResults),
          annotation.start_seconds);
      });
    });
}

document.addEventListener('DOMContentLoaded', function() {
  onClick('#search', handleSubmit);
});
