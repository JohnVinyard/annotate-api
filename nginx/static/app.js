
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
