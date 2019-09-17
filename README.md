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
|`order`|If `desc`, return results from most to least recent, if `asc` return results from least to most recent.|
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
            "id": "592c4858c0226e4d30f8b9940788f",
            "date_created": "2019-09-17T19:13:55.343927Z",
            "user_name": "HalIncandenza",
            "user_type": "human",
            "email": "hal@eta.net",
            "about_me": "Tennis 4 Life",
            "info_url": "https://halation.com"
        },
        {
            "id": "592c4858c026ed33439d40abc29c4",
            "date_created": "2019-09-17T19:13:55.343990Z",
            "user_name": "MikePemulis",
            "user_type": "human",
            "about_me": "Tennis 4 Life",
            "info_url": "https://peemster.com"
        },
        {
            "id": "592c4858c02a46492a36820237d73",
            "date_created": "2019-09-17T19:13:55.344043Z",
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
    "id": "592c4858c1720d645821cc5b643a8",
    "date_created": "2019-09-17T19:13:55.349291Z",
    "user_name": "HalIncandenza",
    "user_type": "human",
    "email": "hal@enfield.com",
    "about_me": "Tennis 4 Life",
    "info_url": null,
    "links": [
        {
            "href": "sounds",
            "rel": "sounds",
            "type": "GET"
        },
        {
            "href": "annotations",
            "rel": "annotations",
            "type": "GET"
        }
    ]
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
            "id": "592c4858c2f031d73686327e0f11d",
            "date_created": "2019-09-17T19:13:55.355404Z",
            "created_by": "/users/592c4858c2eaf970a1dd1e8b1b8b6",
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
            "id": "592c4858c2f49665d7726c595073c",
            "date_created": "2019-09-17T19:13:55.355472Z",
            "created_by": "/users/592c4858c2eaf970a1dd1e8b1b8b6",
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
            "id": "592c4858c2f8bdfef872cfa487bb9",
            "date_created": "2019-09-17T19:13:55.355538Z",
            "created_by": "/users/592c4858c2eaf970a1dd1e8b1b8b6",
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
    "id": "592c4858c3e55f88a526ad370af46",
    "date_created": "2019-09-17T19:13:55.359325Z",
    "created_by": "/users/592c4858c3deec0b4a3106a9bacf4",
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
|`order`|If `desc`, return results from most to least recent, if `asc` return results from least to most recent.|
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
            "id": "592c4858c510089270be01db0ce93",
            "date_created": "2019-09-17T19:13:55.364102Z",
            "created_by": "/users/592c4858c5060d465f3a79a721238",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592c4858c50d5a4fba784c69630d6",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "592c4858c51274c2d0b13346fc373",
            "date_created": "2019-09-17T19:13:55.364141Z",
            "created_by": "/users/592c4858c5060d465f3a79a721238",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592c4858c50d5a4fba784c69630d6",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "592c4858c515a86ca3b1da61f6a9b",
            "date_created": "2019-09-17T19:13:55.364193Z",
            "created_by": "/users/592c4858c5094b8a9988544237bdc",
            "created_by_user_name": "FFTBot",
            "sound": "/sounds/592c4858c50d5a4fba784c69630d6",
            "start_seconds": 0.0,
            "duration_seconds": 12.3,
            "end_seconds": 12.3,
            "data_url": "https://s3/fft-data/file.dat",
            "tags": []
        }
    ],
    "total_count": 100,
    "next": "/sounds/592c4858c50d5a4fba784c69630d6/annotations?page_size=3&page_number=2"
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
|`order`|If `desc`, return results from most to least recent, if `asc` return results from least to most recent.|
|`tags`|Only return sounds with all tags specified|

### Responses

#### `200 OK`

Successfully fetched a list of sounds
##### Example Response

```json
{
    "items": [
        {
            "id": "592c4858c69f79c3f2c38be6ae52d",
            "date_created": "2019-09-17T19:13:55.370495Z",
            "created_by": "/users/592c4858c69b60cfa003a58117ad0",
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
            "id": "592c4858c6a2c323786df9c2bdde4",
            "date_created": "2019-09-17T19:13:55.370546Z",
            "created_by": "/users/592c4858c69b60cfa003a58117ad0",
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
            "id": "592c4858c6a5d1d03eab23d4076c9",
            "date_created": "2019-09-17T19:13:55.370595Z",
            "created_by": "/users/592c4858c69b60cfa003a58117ad0",
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
    "next": "/users/592c4858c69b60cfa003a58117ad0/sounds?page_number=2&page_size=3"
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
|`order`|If `desc`, return results from most to least recent, if `asc` return results from least to most recent.|

### Responses

#### `200 OK`

Successfully fetched a list of annotations
##### Example Response

```json
{
    "items": [
        {
            "id": "592c4858c7797a0a4248e7435fbcd",
            "date_created": "2019-09-17T19:13:55.373981Z",
            "created_by": "/users/592c4858c772a56057af60c185efd",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592c4858c77712da242c601ce0133",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "592c4858c77b9e6c6b2b1fbbb9ce9",
            "date_created": "2019-09-17T19:13:55.374015Z",
            "created_by": "/users/592c4858c772a56057af60c185efd",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592c4858c77712da242c601ce0133",
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
    "next": "/users/592c4858c772a56057af60c185efd/annotations?page_size=2&page_number=2"
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
|`order`|If `desc`, return results from most to least recent, if `asc` return results from least to most recent.|
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
            "id": "592c4858c850968ebb609bbbaaed6",
            "date_created": "2019-09-17T19:13:55.377423Z",
            "created_by": "/users/592c4858c846c3084f028fa6049a1",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592c4858c84b00a1d2ae28a9039ca",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "592c4858c852bc6136c90de6ed326",
            "date_created": "2019-09-17T19:13:55.377457Z",
            "created_by": "/users/592c4858c846c3084f028fa6049a1",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592c4858c84b00a1d2ae28a9039ca",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "592c4858c854caf3f80e73a7f5165",
            "date_created": "2019-09-17T19:13:55.377490Z",
            "created_by": "/users/592c4858c846c3084f028fa6049a1",
            "created_by_user_name": "HalIncandenza",
            "sound": "/sounds/592c4858c84e6f7779215eaafb1e7",
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
