# Cochlea
Cochlea allows users to annotate audio files on the internet.  Segments
or time intervals of audio can be annotated with text tags or arbitrary
structured data hosted on another server.

Basic Auth is currently the only form of authentication supported.
Requests for most resources will return a `401 Unauthorized` response if
the `Authorization` header is missing.

There are three types of users possible:

- `dataset` - can create both sounds and annotations, typically
   representing a related group of sounds on the internet, e.g
   [the MusicNet dataset](https://homes.cs.washington.edu/~thickstn/musicnet.html),
   [the NSynth dataset](https://magenta.tensorflow.org/datasets/nsynth),
   or some other collection of sound.  See
   [`nsynth_dataset.py`](examples/nsynth_dataset.py) for an
   example implementation.
- `featurebot` - an auotmated user that will compute features for
   some or all sounds, e.g., a user that computes short-time fourier
   transforms for each sound and stores the data as serialized numpy
   arrays in an S3 bucket.  See
   [`fft_bot.py`](examples/fft_bot.py) for an example
   implementation.
- `human` - a human user who is likely to interact with the API via
  a web-based GUI and may create annotations for sounds, likely
  adding textual tags to audio segments.

Sounds are typically created by `dataset` users, and annotations simply
designate a segment or interval of the sound, along with optional text
tags or a pointer to an external resource that contains some structured
data (e.g., JSON or a serialized numpy array representing dense feature
vectors) that pertain to or describe that segment of audio.

## `GET /`
Return some high-level stats about users, sounds and annotations
### Responses

#### `200 OK`

Successfully fetched stats
##### Example Response

```json
{
    "totalSounds": 100,
    "totalAnnotations": 1000,
    "totalUsers": 3
}
```
## `GET /users`
Get a list of users
### Query Parameters

|Name|Description|
|---|---|
|`page_size`|The number of results per page|
|`page_number`|The page of results to view|
|`low_id`|Only return identifiers occurring later in the series than this one|
|`user_type`|Only return users with this type|
|`user_name`|Only return users matching this name|

### Responses

#### `200 OK`

Successfully fetched a list of users
##### Example Response

```json
{
    "items": [
        {
            "id": "591fbb7b50cabb81cb44652d9c0bc",
            "date_created": "2019-09-07T19:39:48.467900Z",
            "user_name": "HalIncandenza",
            "user_type": "human",
            "email": "hal@eta.net",
            "about_me": "Tennis 4 Life",
            "info_url": "https://halation.com"
        },
        {
            "id": "591fbb7b50cf6b8d5060399e40a45",
            "date_created": "2019-09-07T19:39:48.467967Z",
            "user_name": "MikePemulis",
            "user_type": "human",
            "about_me": "Tennis 4 Life",
            "info_url": "https://peemster.com"
        },
        {
            "id": "591fbb7b50d2e15cb6c2dc64f01ef",
            "date_created": "2019-09-07T19:39:48.468021Z",
            "user_name": "MarioIncandenza",
            "user_type": "human",
            "about_me": "Movies 4 Life",
            "info_url": "https://mario.com"
        }
    ],
    "total_count": 200,
    "next": "/users?user_type=human&page_size=3&page_number=2"
}
```
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access this sound
## `POST /users`
Create a new user
### Example Request Body

```json
{
    "user_name": "HalIncandenza",
    "password": "password",
    "user_type": "human",
    "email": "hal@eta.com",
    "about_me": "Up and coming tennis star",
    "info_url": "https://hal.eta.net"
}
```
### Responses

#### `201 Created`

Successful user creation
#### `400 Bad Request`

Input model validation error
## `DELETE /users/{user_id}`
Delete a user with the specified id.  Users may only delete themselves.
### URL Parameters

|Name|Description|
|---|---|
|`user_id`|the identifier of the user to delete|

### Responses

#### `200 OK`

The user was deleted
#### `404 Not Found`

The user id does not exist
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to delete this user
## `GET /users/{user_id}`
Fetch an individual user by id.  Some details, such as email, are only included when users fetch their own record
### URL Parameters

|Name|Description|
|---|---|
|`user_id`|the identifier of the user to fetch|

### Responses

#### `200 OK`

Successfully fetched a user
##### Example Response

```json
{
    "id": "591fbb7b522d5bb7885c467b251bd",
    "date_created": "2019-09-07T19:39:48.473569Z",
    "user_name": "HalIncandenza",
    "user_type": "human",
    "email": "hal@enfield.com",
    "about_me": "Tennis 4 Life",
    "info_url": null
}
```
#### `404 Not Found`

Provided an invalid user id
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access this user
## `HEAD /users/{user_id}`
Check if a user exists by id
### URL Parameters

|Name|Description|
|---|---|
|`user_id`|check if the user with `user_id` exists|

### Responses

#### `204 No Content`

The requested user exists
#### `404 Not Found`

The requested user does not exist
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access this user
## `PATCH /users/{user_id}`
Update information about the user
### URL Parameters

|Name|Description|
|---|---|
|`user_id`|the identifier of the user to update|

### Example Request Body

```json
{
    "about_me": "Here is some updated about me text",
    "password": "Here|sANewPa$$w0rd"
}
```
### Responses

#### `204 No Content`

The user was successfully updated
#### `400 Bad Request`

Input model validation error
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to update this user
## `GET /sounds`
Get a list of sounds
### Query Parameters

|Name|Description|
|---|---|
|`page_size`|The number of results per page|
|`page_number`|The page of results to view|
|`low_id`|Only return identifiers occurring later in the series than this one|
|`created_by`|Only return sounds created by the user with this id|

### Responses

#### `200 OK`

Successfully fetched a list of sounds
##### Example Response

```json
{
    "items": [
        {
            "id": "591fbb7b53a7f23c0f8c3594f3d13",
            "date_created": "2019-09-07T19:39:48.479624Z",
            "created_by": "/users/591fbb7b53a2583a33d61a6f54e96",
            "created_by_user_name": "HalIncandenza",
            "info_url": "https://example.com/sound1",
            "audio_url": "https://example.com/sound1/file.wav",
            "low_quality_audio_url": "https://example.com/sound1/file.mp3",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "First sound",
            "duration_seconds": 12.3,
            "tags": [
                "test"
            ]
        },
        {
            "id": "591fbb7b53ac4e2fa20d2fa7f14d3",
            "date_created": "2019-09-07T19:39:48.479692Z",
            "created_by": "/users/591fbb7b53a2583a33d61a6f54e96",
            "created_by_user_name": "HalIncandenza",
            "info_url": "https://example.com/sound2",
            "audio_url": "https://example.com/sound2/file.wav",
            "low_quality_audio_url": "https://example.com/sound2/file.mp3",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "Second sound",
            "duration_seconds": 1.3,
            "tags": [
                "test"
            ]
        },
        {
            "id": "591fbb7b53b0504519dfcae51da7e",
            "date_created": "2019-09-07T19:39:48.479756Z",
            "created_by": "/users/591fbb7b53a2583a33d61a6f54e96",
            "created_by_user_name": "HalIncandenza",
            "info_url": "https://example.com/sound3",
            "audio_url": "https://example.com/sound3/file.wav",
            "low_quality_audio_url": "https://example.com/sound3/file.mp3",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "Third sound",
            "duration_seconds": 30.4,
            "tags": [
                "test"
            ]
        }
    ],
    "total_count": 100,
    "next": "/sounds?page_number=2&page_size=3"
}
```
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access this sound
## `POST /sounds`
Create a new sound
### Example Request Body

```json
{
    "info_url": "https://archive.org/details/Greatest_Speeches_of_the_20th_Century",
    "audio_url": "https://archive.org/download/Greatest_Speeches_of_the_20th_Century/AbdicationAddress.ogg",
    "license_type": "https://creativecommons.org/licenses/by/4.0",
    "title": "Abdication Address - King Edward VIII",
    "duration_seconds": 402,
    "tags": [
        "speech"
    ]
}
```
### Responses

#### `201 Created`

Successful sound creation
#### `400 Bad Request`

Input model validation error
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to create sounds
## `GET /sounds/{sound_id}`
Fetch an individual sound
### URL Parameters

|Name|Description|
|---|---|
|`sound_id`|The identifier of the sound to fetch|

### Responses

#### `200 OK`

Successfully fetched sound
##### Example Response

```json
{
    "id": "591fbb7b54893426389610d43922e",
    "date_created": "2019-09-07T19:39:48.483227Z",
    "created_by": "/users/591fbb7b54843915b8a841fe5a123",
    "created_by_user_name": "HalIncandenza",
    "info_url": "https://example.com/sound",
    "audio_url": "https://example.com/sound/file.wav",
    "low_quality_audio_url": "https://example.com/sound/file.mp3",
    "license_type": "https://creativecommons.org/licenses/by/4.0",
    "title": "A sound",
    "duration_seconds": 12.3,
    "tags": [
        "test"
    ]
}
```
#### `404 Not Found`

The sound identifier supplied does not exist
## `HEAD /sounds/{sound_id}`
Check if a sound exists by id
### URL Parameters

|Name|Description|
|---|---|
|`sound_id`|The identifier of the sound to fetch|

### Responses

#### `204 No Content`

The sound identifier exists
#### `404 Not Found`

The sound identifier does not exist
## `GET /sounds/{sound_id}/annotations`
Get a list of annotations for the sound with id `sound_id`
### URL Parameters

|Name|Description|
|---|---|
|`sound_id`|The sound to list annotations for|

### Query Parameters

|Name|Description|
|---|---|
|`page_size`|The number of results per page|
|`page_number`|The page of results to view|
|`low_id`|Only return identifiers occurring later in the series than this one|
|`time_range`|Only return annotations overlapping with the specified time range|

### Responses

#### `200 OK`

Successfully fetched a list of annotations
##### Example Response

```json
{
    "items": [
        {
            "id": "591fbb7b5593e10aedfa7650feb97",
            "date_created": "2019-09-07T19:39:48.487492Z",
            "created_by": "/users/591fbb7b558af461a22305a765b89",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/591fbb7b55916b9e3436f679c1351",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "591fbb7b559607df0054034a425c0",
            "date_created": "2019-09-07T19:39:48.487526Z",
            "created_by": "/users/591fbb7b558af461a22305a765b89",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/591fbb7b55916b9e3436f679c1351",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "591fbb7b5598f07d3d3263e181141",
            "date_created": "2019-09-07T19:39:48.487574Z",
            "created_by": "/users/591fbb7b558dd21d7fe00bab4e103",
            "created_by_user_name": "FFTBot",
            "sound": "/sounds/591fbb7b55916b9e3436f679c1351",
            "start_seconds": 0.0,
            "duration_seconds": 12.3,
            "end_seconds": 12.3,
            "data_url": "https://s3/fft-data/file.dat",
            "tags": null
        }
    ],
    "total_count": 100,
    "next": "/sounds/591fbb7b55916b9e3436f679c1351/annotations?page_size=3&page_number=2"
}
```
#### `404 Not Found`

Provided an unknown sound identifier
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access annotations for this sound
## `POST /sounds/{sound_id}/annotations`
Create a new annotation for the sound with identifier `sound_id`. Text tags can be added directly to the resource via the `tags` field, or arbitrary binary or other structured data may be pointed to via the `data_url` parameter.
### URL Parameters

|Name|Description|
|---|---|
|`sound_id`|The identifier of the sound to annotate|

### Example Request Body

```json
{
    "start_seconds": 1.2,
    "duration_seconds": 0.5,
    "tags": [
        "snare",
        "hi-hat"
    ],
    "data_url": "https://s3/data/numpy-fft-feature.dat"
}
```
### Responses

#### `201 Created`

Successful annotation creation
#### `400 Bad Request`

Input model validation error
#### `404 Not Found`

Provided an invalid `sound_id`
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to create annotations
## `GET /users/{user_id}/sounds`
Get a list of sounds belonging to a user with id `user_id`
### URL Parameters

|Name|Description|
|---|---|
|`user_id`|The user who created the sounds|

### Query Parameters

|Name|Description|
|---|---|
|`page_size`|The number of results per page|
|`page_number`|The page of results to view|
|`low_id`|Only return identifiers occurring later in the series than this one|
|`tags`|Only return sounds with all tags specified|

### Responses

#### `200 OK`

Successfully fetched a list of sounds
##### Example Response

```json
{
    "items": [
        {
            "id": "591fbb7b56fea1b52f912ec9e0c3e",
            "date_created": "2019-09-07T19:39:48.493297Z",
            "created_by": "/users/591fbb7b56fa91196d41136294f0b",
            "created_by_user_name": "HalIncandenza",
            "info_url": "https://example.com/sound1",
            "audio_url": "https://example.com/sound1/file.wav",
            "low_quality_audio_url": "https://example.com/sound1/file.mp3",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "First sound",
            "duration_seconds": 12.3,
            "tags": [
                "test"
            ]
        },
        {
            "id": "591fbb7b5701e40d676348abf83a8",
            "date_created": "2019-09-07T19:39:48.493349Z",
            "created_by": "/users/591fbb7b56fa91196d41136294f0b",
            "created_by_user_name": "HalIncandenza",
            "info_url": "https://example.com/sound2",
            "audio_url": "https://example.com/sound2/file.wav",
            "low_quality_audio_url": "https://example.com/sound2/file.mp3",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "Second sound",
            "duration_seconds": 1.3,
            "tags": [
                "test"
            ]
        },
        {
            "id": "591fbb7b570510b723675079e6e88",
            "date_created": "2019-09-07T19:39:48.493399Z",
            "created_by": "/users/591fbb7b56fa91196d41136294f0b",
            "created_by_user_name": "HalIncandenza",
            "info_url": "https://example.com/sound3",
            "audio_url": "https://example.com/sound3/file.wav",
            "low_quality_audio_url": "https://example.com/sound3/file.mp3",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "Third sound",
            "duration_seconds": 30.4,
            "tags": [
                "test"
            ]
        }
    ],
    "total_count": 100,
    "next": "/users/591fbb7b56fa91196d41136294f0b/sounds?page_number=2&page_size=3"
}
```
#### `404 Not Found`

Provided an unknown user identifier
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access sounds from this user
## `GET /users/{user_id}/annotations`
List annotations created by a user with id `user_id`
### URL Parameters

|Name|Description|
|---|---|
|`user_id`|The user who created the annotations|

### Query Parameters

|Name|Description|
|---|---|
|`page_size`|The number of results per page|
|`page_number`|The current page|

### Responses

#### `200 OK`

Successfully fetched a list of annotations
##### Example Response

```json
{
    "items": [
        {
            "id": "591fbb7b57ac6391eb183585eca43",
            "date_created": "2019-09-07T19:39:48.496076Z",
            "created_by": "/users/591fbb7b57a622cab545955f8da27",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/591fbb7b57aa2876a3ad0580d7b60",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "591fbb7b57ae90be63f8d50d085cd",
            "date_created": "2019-09-07T19:39:48.496110Z",
            "created_by": "/users/591fbb7b57a622cab545955f8da27",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/591fbb7b57aa2876a3ad0580d7b60",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        }
    ],
    "total_count": 100,
    "next": "/users/591fbb7b57a622cab545955f8da27/annotations?page_size=2&page_number=2"
}
```
#### `404 Not Found`

Provided an unknown user identifier
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access annotationsfrom this user
## `GET /annotations`
Get a list of annotations
### Query Parameters

|Name|Description|
|---|---|
|`page_size`|The number of results per page|
|`page_number`|The page of results to view|
|`low_id`|Only return identifiers occurring later in the series than this one|
|`tags`|Only return annotations with all specified tags|

### Responses

#### `200 OK`

Successfully fetched an annotation
##### Example Response

```json
{
    "items": [
        {
            "id": "591fbb7b584c93410cd7237067713",
            "date_created": "2019-09-07T19:39:48.498640Z",
            "created_by": "/users/591fbb7b583f386bed23cbd8490aa",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/591fbb7b5843c2820f9a3a00de106",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "591fbb7b584edd6adf52417627bba",
            "date_created": "2019-09-07T19:39:48.498675Z",
            "created_by": "/users/591fbb7b583f386bed23cbd8490aa",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/591fbb7b5843c2820f9a3a00de106",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "591fbb7b5850ef74dade7713e5d16",
            "date_created": "2019-09-07T19:39:48.498708Z",
            "created_by": "/users/591fbb7b583f386bed23cbd8490aa",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/591fbb7b5849ec0191eb463540425",
            "start_seconds": 10.0,
            "duration_seconds": 5.0,
            "end_seconds": 15.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        }
    ],
    "total_count": 100,
    "next": "/annotations?page_size=3&page_number=2&tags=snare"
}
```
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access this annotation
