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
   or some other collection of sound
- `featurebot` - an auotmated user that will compute features for
   some or all sounds, e.g., a user that computes short-time fourier
   transforms for each sound and stores the data as serialized numpy
   arrays in an S3 bucket
- `human` - a human user who is likely to interact with the API via
  a web-based GUI and may create annotations for sounds, likely
  adding textual tags to audio segments

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
            "id": "58efeee8ff60079d64b2ca3a60966",
            "date_created": "2019-07-31T19:14:18.802704Z",
            "user_name": "HalIncandenza",
            "user_type": "human",
            "email": "hal@eta.net",
            "about_me": "Tennis 4 Life",
            "info_url": "https://halation.com"
        },
        {
            "id": "58efeee8ff653a623fc49411897ca",
            "date_created": "2019-07-31T19:14:18.802779Z",
            "user_name": "MikePemulis",
            "user_type": "human",
            "about_me": "Tennis 4 Life",
            "info_url": "https://peemster.com"
        },
        {
            "id": "58efeee8ff68ae33c7d1bf7d7c9b4",
            "date_created": "2019-07-31T19:14:18.802834Z",
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
    "id": "58efeee900b0c3153ea331f988467",
    "date_created": "2019-07-31T19:14:18.808088Z",
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
            "id": "58efeee9022b73b6934bd0c1a5471",
            "date_created": "2019-07-31T19:14:18.814145Z",
            "created_by": "/users/58efeee902265ad546a485b7230bd",
            "info_url": "https://example.com/sound1",
            "audio_url": "https://example.com/sound1/file.wav",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "First sound",
            "duration_seconds": 12.3,
            "tags": [
                "test"
            ]
        },
        {
            "id": "58efeee9022f642d4825857a6dacd",
            "date_created": "2019-07-31T19:14:18.814205Z",
            "created_by": "/users/58efeee902265ad546a485b7230bd",
            "info_url": "https://example.com/sound2",
            "audio_url": "https://example.com/sound2/file.wav",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "Second sound",
            "duration_seconds": 1.3,
            "tags": [
                "test"
            ]
        },
        {
            "id": "58efeee90232f1ebd8d292656c5a4",
            "date_created": "2019-07-31T19:14:18.814262Z",
            "created_by": "/users/58efeee902265ad546a485b7230bd",
            "info_url": "https://example.com/sound3",
            "audio_url": "https://example.com/sound3/file.wav",
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
    "id": "58efeee9030e2e94354354294d548",
    "date_created": "2019-07-31T19:14:18.817770Z",
    "created_by": "/users/58efeee90309dc6739cfccd7f255c",
    "info_url": "https://example.com/sound",
    "audio_url": "https://example.com/sound/file.wav",
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
            "id": "58efeee90427cd3c503ccc65a4e6d",
            "date_created": "2019-07-31T19:14:18.822274Z",
            "created_by": "/users/58efeee9041f82f39d31bb45d21f6",
            "sound": "/sounds/58efeee90425aebcf51cc60dcaef5",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "58efeee90429babf75d0f46f38e8a",
            "date_created": "2019-07-31T19:14:18.822304Z",
            "created_by": "/users/58efeee9041f82f39d31bb45d21f6",
            "sound": "/sounds/58efeee90425aebcf51cc60dcaef5",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efeee9042c5672782080b4ebd0d",
            "date_created": "2019-07-31T19:14:18.822347Z",
            "created_by": "/users/58efeee904226992a76f786615dab",
            "sound": "/sounds/58efeee90425aebcf51cc60dcaef5",
            "start_seconds": 0.0,
            "duration_seconds": 12.3,
            "end_seconds": 12.3,
            "data_url": "https://s3/fft-data/file.dat",
            "tags": null
        }
    ],
    "total_count": 100,
    "next": "/sounds/58efeee90425aebcf51cc60dcaef5/annotations?page_size=3&page_number=2"
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
            "id": "58efeee90591e9a84d855cde93845",
            "date_created": "2019-07-31T19:14:18.828069Z",
            "created_by": "/users/58efeee9058e638329e1ecc99fe3f",
            "info_url": "https://example.com/sound1",
            "audio_url": "https://example.com/sound1/file.wav",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "First sound",
            "duration_seconds": 12.3,
            "tags": [
                "test"
            ]
        },
        {
            "id": "58efeee90594909b56ac1ff81e145",
            "date_created": "2019-07-31T19:14:18.828111Z",
            "created_by": "/users/58efeee9058e638329e1ecc99fe3f",
            "info_url": "https://example.com/sound2",
            "audio_url": "https://example.com/sound2/file.wav",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "Second sound",
            "duration_seconds": 1.3,
            "tags": [
                "test"
            ]
        },
        {
            "id": "58efeee9059729e2f97d34d41a869",
            "date_created": "2019-07-31T19:14:18.828152Z",
            "created_by": "/users/58efeee9058e638329e1ecc99fe3f",
            "info_url": "https://example.com/sound3",
            "audio_url": "https://example.com/sound3/file.wav",
            "license_type": "https://creativecommons.org/licenses/by/4.0",
            "title": "Third sound",
            "duration_seconds": 30.4,
            "tags": [
                "test"
            ]
        }
    ],
    "total_count": 100,
    "next": "/users/58efeee9058e638329e1ecc99fe3f/sounds?page_number=2&page_size=3"
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
            "id": "58efeee9063dafb2203850e073a7b",
            "date_created": "2019-07-31T19:14:18.830816Z",
            "created_by": "/users/58efeee90638221226276e5f774ed",
            "sound": "/sounds/58efeee9063bbeedba645e370a25b",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "58efeee9063f880a54c26a87f9974",
            "date_created": "2019-07-31T19:14:18.830845Z",
            "created_by": "/users/58efeee90638221226276e5f774ed",
            "sound": "/sounds/58efeee9063bbeedba645e370a25b",
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
    "next": "/users/58efeee90638221226276e5f774ed/annotations?page_size=2&page_number=2"
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
            "id": "58efeee906e02448bd658c6ab340a",
            "date_created": "2019-07-31T19:14:18.833416Z",
            "created_by": "/users/58efeee906d7e9878dad6baa744a2",
            "sound": "/sounds/58efeee906db77fb128c2374f9330",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efeee906e20e817bc20b527f980",
            "date_created": "2019-07-31T19:14:18.833446Z",
            "created_by": "/users/58efeee906d7e9878dad6baa744a2",
            "sound": "/sounds/58efeee906db77fb128c2374f9330",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efeee906e3dd9cbd71115385f64",
            "date_created": "2019-07-31T19:14:18.833475Z",
            "created_by": "/users/58efeee906d7e9878dad6baa744a2",
            "sound": "/sounds/58efeee906de3bb36158cbbab2620",
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
