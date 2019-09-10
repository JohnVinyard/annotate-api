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
            "id": "592330e4b3747ba78eccd2970f8eb",
            "date_created": "2019-09-10T13:41:04.351061Z",
            "user_name": "HalIncandenza",
            "user_type": "human",
            "email": "hal@eta.net",
            "about_me": "Tennis 4 Life",
            "info_url": "https://halation.com"
        },
        {
            "id": "592330e4b378ecb8c842e179a00fc",
            "date_created": "2019-09-10T13:41:04.351126Z",
            "user_name": "MikePemulis",
            "user_type": "human",
            "about_me": "Tennis 4 Life",
            "info_url": "https://peemster.com"
        },
        {
            "id": "592330e4b37c67fbf71c14168577f",
            "date_created": "2019-09-10T13:41:04.351181Z",
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
    "id": "592330e4b4c847aa57ac367bcc3dd",
    "date_created": "2019-09-10T13:41:04.356496Z",
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
            "id": "592330e4b652e8598bf1fc319cbbd",
            "date_created": "2019-09-10T13:41:04.362806Z",
            "created_by": "/users/592330e4b64d8984861e58e03923e",
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
            "id": "592330e4b6573811bcbcc50629359",
            "date_created": "2019-09-10T13:41:04.362874Z",
            "created_by": "/users/592330e4b64d8984861e58e03923e",
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
            "id": "592330e4b65b55aa86cec72ab86a5",
            "date_created": "2019-09-10T13:41:04.362940Z",
            "created_by": "/users/592330e4b64d8984861e58e03923e",
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
    "id": "592330e4b72f5fffa4a085efdd18d",
    "date_created": "2019-09-10T13:41:04.366333Z",
    "created_by": "/users/592330e4b72a546b1c48725c7ab9f",
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
            "id": "592330e4b84749b3bdba6e78f56fd",
            "date_created": "2019-09-10T13:41:04.370811Z",
            "created_by": "/users/592330e4b83d7ee7a61a3c7fa62e1",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592330e4b844b9215196a04b1b76f",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "592330e4b849ba7a7a173cf915f88",
            "date_created": "2019-09-10T13:41:04.370849Z",
            "created_by": "/users/592330e4b83d7ee7a61a3c7fa62e1",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592330e4b844b9215196a04b1b76f",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "592330e4b84cf732c8a3c36513643",
            "date_created": "2019-09-10T13:41:04.370902Z",
            "created_by": "/users/592330e4b840bef145b18ee85c1ce",
            "created_by_user_name": "FFTBot",
            "sound": "/sounds/592330e4b844b9215196a04b1b76f",
            "start_seconds": 0.0,
            "duration_seconds": 12.3,
            "end_seconds": 12.3,
            "data_url": "https://s3/fft-data/file.dat",
            "tags": []
        }
    ],
    "total_count": 100,
    "next": "/sounds/592330e4b844b9215196a04b1b76f/annotations?page_size=3&page_number=2"
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
            "id": "592330e4b9b349894fd6e03e9b557",
            "date_created": "2019-09-10T13:41:04.376635Z",
            "created_by": "/users/592330e4b9ade7e024910d15862ab",
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
            "id": "592330e4b9b68b2cd7090896557dd",
            "date_created": "2019-09-10T13:41:04.376687Z",
            "created_by": "/users/592330e4b9ade7e024910d15862ab",
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
            "id": "592330e4b9b9a9f0b81d02af4673e",
            "date_created": "2019-09-10T13:41:04.376735Z",
            "created_by": "/users/592330e4b9ade7e024910d15862ab",
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
    "next": "/users/592330e4b9ade7e024910d15862ab/sounds?page_number=2&page_size=3"
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
            "id": "592330e4ba7f6252a1b50f8ba24ea",
            "date_created": "2019-09-10T13:41:04.379901Z",
            "created_by": "/users/592330e4ba781e1cf7f60bc9d9808",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592330e4ba7cca822ec8fe15ecc85",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "592330e4ba81c98f2d822747cfc63",
            "date_created": "2019-09-10T13:41:04.379938Z",
            "created_by": "/users/592330e4ba781e1cf7f60bc9d9808",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592330e4ba7cca822ec8fe15ecc85",
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
    "next": "/users/592330e4ba781e1cf7f60bc9d9808/annotations?page_size=2&page_number=2"
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
|`with_tags`|Only return annotations that have at least one tag, generally excluding dense features computed by featurebots.  This parameter is mutually exclusive with `tags` and will be ignored if it is present.|

### Responses

#### `200 OK`

Successfully fetched an annotation
##### Example Response

```json
{
    "items": [
        {
            "id": "592330e4bb44ed24d1fdbbfba5134",
            "date_created": "2019-09-10T13:41:04.383060Z",
            "created_by": "/users/592330e4bb3b5100697d108a97b86",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592330e4bb3f50adf28bc2c1cc15c",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "592330e4bb470b0e05a1064e38037",
            "date_created": "2019-09-10T13:41:04.383094Z",
            "created_by": "/users/592330e4bb3b5100697d108a97b86",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592330e4bb3f50adf28bc2c1cc15c",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "592330e4bb491597e2e99f210201b",
            "date_created": "2019-09-10T13:41:04.383126Z",
            "created_by": "/users/592330e4bb3b5100697d108a97b86",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592330e4bb42b9a4bfb6d10c78b55",
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
