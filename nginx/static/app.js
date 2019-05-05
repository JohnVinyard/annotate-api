
class FeatureData {
  constructor(binaryData, dimensions, sampleFrequency, sampleDuration) {
    this.binaryData = binaryData;
    const dimProduct = dimensions.reduce((x, y) => x * y, 1);
    if(dimProduct !== this.binaryData.length) {
      throw new RangeError(
        "The product of dimensions must equal binaryData.length");
    }
    this.dimensions = dimensions;
    this.sampleFrequency = sampleFrequency;
    this.sampleDuration = sampleDuration;
  }

  get rank() {
    return this.dimensions.length;
  }

  get length() {
    return this.dimensions[0];
  }

  slice(start, end) {
    const latterDimensions = this.dimensions.slice(1);
    const stride = latterDimensions.reduce((x, y) => x * y, 1);
    const startIndex =
      start === undefined ? 0 : start * latterDimensions;
    const endIndex =
      end === undefined ? this.binaryData.length : end * latterDimensions;
    const newFirstDimension = (endIndex - startIndex) / stride;
    const newDimensions = [newFirstDimension].concat(latterDimensions);
    return new FeatureData(
      // Use subarray so that the same underlying buffer is used
      this.binaryData.subarray(startIndex, endIndex),
      newDimensions,
      this.sampleFrequency,
      this.sampleDuration
    );
  }
}

const addTemplate = (templateSelector, parentElement) => {
  const template = document.querySelector(templateSelector);
  const clone = document.importNode(template.content, true);
  parentElement.appendChild(clone);
};

const onClick = (selector, handler) => {
  document.addEventListener('click', function(event) {
    if(event.target.matches(selector)) {
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

// TODO: redraw on resize
class SoundView1D {
  constructor(parentElement, featureData) {
    const template = document.querySelector('#sound-view-template');
    const clone = document.importNode(template.content, true);
    const canvas = clone.querySelector('canvas');

    this.canvas = canvas;
    this.drawContext = canvas.getContext('2d');
    this.parentElement = parentElement;
    this.parentElement.appendChild(clone);
    this.container = parentElement.querySelector('.sound-view-container');

    canvas.width = this.container.clientWidth;
    canvas.style.width = '100%';
    canvas.height = this.container.clientHeight;
    canvas.style.height = '100%';
    this.featureData = featureData;
    this.zoom = 1;
    this.draw();

    const self = this;
    onScroll(this.container, () => this.draw(), 100);
    onResize(window, () => this.draw(), 100);
  }

  get containerWidth() {
    return this.container.clientWidth;
  }

  clear() {
    this.drawContext.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  draw1D(i, increment, height, index) {
    const sample =
      Math.abs(this.featureData.binaryData[Math.round(index)]);
    this.drawContext.fillRect(
      this.container.scrollLeft + i,
      height - (sample * height),
      increment,
      sample * height);
  }

  draw2D(i, increment, height, index) {
    const roundedIndex = Math.round(index);
    const slice = this.featureData.slice(roundedIndex, roundedIndex + 1);
    const data = slice.binaryData;
    const verticalStride = height / data.length;

    for(let j = 0; j < data.length; j++) {
      // KLUDGE: This assumes that all data will be in range 0-1
      const value = Math.round(Math.abs(data[j]) * 255);
      const color = `rgb(${value}, ${value}, ${value})`;
      this.drawContext.fillStyle = color;
      this.drawContext.fillRect(
        this.container.scrollLeft + i,
        verticalStride * j,
        increment,
        verticalStride);
    }
  }

  draw() {
    this.clear()
    const stride = this.featureData.length / this.elementWidth;
    const offsetPercent = this.container.scrollLeft / this.elementWidth;
    const height = this.container.clientHeight;
    const increment = Math.max(1, 1 / stride);


    this.drawContext.fillStyle = 'black';
    for(let i = 0; i < this.containerWidth; i+=increment) {
      const index = (this.featureData.length * offsetPercent) + (i * stride);
      if (this.featureData.rank === 1) {
        this.draw1D(i, increment, height, index);
      } else if (this.featureData.rank === 2) {
        this.draw2D(i, increment, height, index);
      } else {
        throw new Error('Dimensions greater than 2 not currently supported');
      }
    }
  }

  get elementWidth() {
    return this.containerWidth * this.zoom;
  }

  setZoom(zoom) {
    this.zoom = zoom;
    this.canvas.width = this.elementWidth;
    this.canvas.style.width = `${this.zoom * 100}%`;
    this.draw();
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

const handleSubmit = (event) => {
  const rawQuery = document.querySelector('#search-criteria').value;

  annotateClient.getAnnotations(rawQuery)
    .then(data => {
      const searchResults = document.querySelector('#search-results');

      // clear the results
      while(searchResults.firstChild) {
        searchResults.firstChild.remove();
      }

      // get unique list of all sounds and fetch them greedily
      const sounds = new Set(data.items.map(x => x.sound));
      const mapping = {};
      sounds.forEach(sndUri => {
        annotateClient.getResource(sndUri)
          .then(data => {
            mapping[`/sounds/${data.id}`] = data.audio_url;
            fetchAudio(data.audio_url, context);
          })
      });

      // add click-able elements to play each annotation
      data.items.forEach(annotation => {
        const item = document.createElement('li');
        item.innerText = `${annotation.sound} ${annotation.start_seconds} - ${annotation.end_seconds}`;
        item.id = `annotation-${annotation.id}`;
        onClick(`#${item.id}`, event => {
            playAudio(
              mapping[annotation.sound],
              context,
              annotation.start_seconds,
              annotation.duration_seconds);
        });
        searchResults.appendChild(item);
      });
    });
}


let soundView = null;

document.addEventListener('DOMContentLoaded', function() {
  // onClick('#search', handleSubmit);
  annotateClient.getSounds()
    .then(sounds => {
      return annotateClient.getSound(sounds.items[0].id);
    })
    .then(snd => {
      return fetchAudio(snd.audio_url, context);
    })
    .then(buffer => {
      const raw = buffer.getChannelData(0);
      const frequency = 1 / buffer.sampleRate;
      const fd = new FeatureData(raw, [raw.length], frequency, frequency);
      const parentElement = document.querySelector('#temp-container');
      soundView = new SoundView1D(parentElement, fd);
    });
});
