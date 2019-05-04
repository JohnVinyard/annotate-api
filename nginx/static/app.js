
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

class SoundView1D {
  constructor(parentElement, featureData) {
    const template = document.querySelector('#sound-view-template');
    const clone = document.importNode(template.content, true);
    const canvas = clone.querySelector('canvas');

    this.canvas = canvas;
    this.drawContext = canvas.getContext('2d');
    this.parentElement = parentElement;
    this.parentElement.appendChild(clone);
    canvas.width = parentElement.clientWidth;
    canvas.height = parentElement.clientHeight;
    this.featureData = featureData;
    this.zoom = 1;
    this.draw();
  }

  get containerWidth() {
    return this.parentElement.clientWidth;
  }

  draw() {
    this.drawContext.fillStyle = 'black';
    const stride = this.featureData.length / this.elementWidth;
    const height = this.parentElement.clientHeight;
    for(let i = 0; i < this.containerWidth; i++) {
      // KLUDGE: This should be behind the FeatureData interface
      const sample =
        Math.abs(this.featureData.binaryData[Math.round(i * stride)]);
      this.drawContext.fillRect(i, height - (sample * height), 1, sample * height);
    }
  }

  clear() {
    this.drawContext.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  get elementWidth() {
    return this.containerWidth * this.zoom;
  }

  setZoom(zoom) {
    this.zoom = zoom;
    this.clear()
    this.canvas.width = Math.round(this.containerWidth * this.zoom);
    // TODO: This should resize the canvas and re-draw too
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


const onClick = (selector, handler) => {
  document.addEventListener('click', function(event) {
    if(event.target.matches(selector)) {
      event.preventDefault();
      handler(event);
    }
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
      new SoundView1D(parentElement, fd);
    });
});
