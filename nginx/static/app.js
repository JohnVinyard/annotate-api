
const context = new (window.AudioContext || window.webkitAudioContext)();

const authHeader = (username, password) => {
  const credentials = btoa(`${username}:${password}`);
  return `Basic ${credentials}`;
};


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
        const gain = context.createGain();
        source.buffer = audioBuffer;
        source.connect(gain);
        gain.connect(context.destination);
        const now = context.currentTime;
        gain.gain.setValueAtTime(1, now);
        source.start(0, start * audioBuffer.duration, duration * 2);
        gain.gain.setValueAtTime(1, now + duration);
        gain.gain.exponentialRampToValueAtTime(0.01, now + (duration * 2));
    });
};

const headers = new Headers();
headers.append('Authorization', authHeader('musicnet', 'password'));

fetch('/sounds', {headers})
  .then(resp => resp.json())
  .then(data => {
    return fetch(`/sounds/${data.items[0].id}/annotations`, {headers});
  })
  .then(resp => resp.json())
  .then(data => console.log(data));
