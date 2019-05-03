
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

const handleSubmit = (event) => {
  const rawQuery = document.querySelector('#search-criteria').value;

  const headers = new Headers();
  headers.append('Authorization', authHeader('musicnet', 'password'));

  fetch(`/annotations?tags=${rawQuery}&page_size=25`, {headers})
    .then(resp => resp.json())
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
        fetch(sndUri, {headers})
          .then(resp => resp.json())
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
            console.log(`playing ${item.id}`);
            playAudio(
              mapping[annotation.sound],
              context,
              annotation.start_seconds,
              annotation.duration_seconds);
        });
        searchResults.appendChild(item);
      });
      console.log(data);
      console.log(sounds)
    });
}


document.addEventListener('DOMContentLoaded', function() {
  onClick('#search', handleSubmit);
});
