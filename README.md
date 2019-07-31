# Cochlea
Cochlea allows users to annotate audio files on the internet.  Segments or time intervals of audio can be annotated with text tags or arbitrary structured data hosted on another server.
Basic Auth is currently the only form of authentication supported. Requests for most resources will return a `401 Unauthorized` response if the `Authorization` header is missing.
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
            "id": "58efe7fd75cc5d8cf5463a3e94440",
            "date_created": "2019-07-31T18:43:21.211092Z",
            "user_name": "HalIncandenza",
            "user_type": "human",
            "email": "hal@eta.net",
            "about_me": "Tennis 4 Life",
            "info_url": "https://halation.com"
        },
        {
            "id": "58efe7fd75d10a9214ed7bbe07fb6",
            "date_created": "2019-07-31T18:43:21.211161Z",
            "user_name": "MikePemulis",
            "user_type": "human",
            "about_me": "Tennis 4 Life",
            "info_url": "https://peemster.com"
        },
        {
            "id": "58efe7fd75d4cf788840d9d150128",
            "date_created": "2019-07-31T18:43:21.211220Z",
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
    "id": "58efe7fd77155871c256bf01a8577",
    "date_created": "2019-07-31T18:43:21.216352Z",
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
            "id": "58efe7fd78a2dec61b42cb5191ccb",
            "date_created": "2019-07-31T18:43:21.222710Z",
            "created_by": "/users/58efe7fd789d99a8476c80e212e56",
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
            "id": "58efe7fd78a6a87597f4a45c5f635",
            "date_created": "2019-07-31T18:43:21.222769Z",
            "created_by": "/users/58efe7fd789d99a8476c80e212e56",
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
            "id": "58efe7fd78aa3da6b1c186c2050ca",
            "date_created": "2019-07-31T18:43:21.222826Z",
            "created_by": "/users/58efe7fd789d99a8476c80e212e56",
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
    "id": "58efe7fd798282aa09ad6a196896c",
    "date_created": "2019-07-31T18:43:21.226288Z",
    "created_by": "/users/58efe7fd797b9006537d5e626b935",
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
            "id": "58efe7fd7a978483511a89fc02d11",
            "date_created": "2019-07-31T18:43:21.230717Z",
            "created_by": "/users/58efe7fd7a8f88fffe27b40ca4afd",
            "sound": "/sounds/58efe7fd7a958ebdddb153e0aa34e",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "58efe7fd7a9966b02696fc09d8824",
            "date_created": "2019-07-31T18:43:21.230748Z",
            "created_by": "/users/58efe7fd7a8f88fffe27b40ca4afd",
            "sound": "/sounds/58efe7fd7a958ebdddb153e0aa34e",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efe7fd7a9c0ffafa9aa6fcbc15f",
            "date_created": "2019-07-31T18:43:21.230790Z",
            "created_by": "/users/58efe7fd7a925b0019bf870678330",
            "sound": "/sounds/58efe7fd7a958ebdddb153e0aa34e",
            "start_seconds": 0.0,
            "duration_seconds": 12.3,
            "end_seconds": 12.3,
            "data_url": "https://s3/fft-data/file.dat",
            "tags": null
        }
    ],
    "total_count": 100,
    "next": "/sounds/58efe7fd7a958ebdddb153e0aa34e/annotations?page_size=3&page_number=2"
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
            "id": "58efe7fd7bfa3d8a2263a95bfc4b1",
            "date_created": "2019-07-31T18:43:21.236394Z",
            "created_by": "/users/58efe7fd7bf69f367a4c25f32c842",
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
            "id": "58efe7fd7bfcf70c5a78cf48b79b2",
            "date_created": "2019-07-31T18:43:21.236437Z",
            "created_by": "/users/58efe7fd7bf69f367a4c25f32c842",
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
            "id": "58efe7fd7bff85f039b936042f63f",
            "date_created": "2019-07-31T18:43:21.236477Z",
            "created_by": "/users/58efe7fd7bf69f367a4c25f32c842",
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
    "next": "/users/58efe7fd7bf69f367a4c25f32c842/sounds?page_number=2&page_size=3"
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
            "id": "58efe7fd7ca9ca4547522e8a6c231",
            "date_created": "2019-07-31T18:43:21.239213Z",
            "created_by": "/users/58efe7fd7ca3846d71e54243b08ca",
            "sound": "/sounds/58efe7fd7ca726d37abc8ee43311e",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "58efe7fd7cacf72affa843783a66a",
            "date_created": "2019-07-31T18:43:21.239253Z",
            "created_by": "/users/58efe7fd7ca3846d71e54243b08ca",
            "sound": "/sounds/58efe7fd7ca726d37abc8ee43311e",
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
    "next": "/users/58efe7fd7ca3846d71e54243b08ca/annotations?page_size=2&page_number=2"
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
            "id": "58efe7fd7d5b61b4ae304522ed3d0",
            "date_created": "2019-07-31T18:43:21.242044Z",
            "created_by": "/users/58efe7fd7d5358f92ec78bb4a21b8",
            "sound": "/sounds/58efe7fd7d56e4c3a874cfd8b7c60",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "58efe7fd7d5d4fffee9591a73231c",
            "date_created": "2019-07-31T18:43:21.242073Z",
            "created_by": "/users/58efe7fd7d5358f92ec78bb4a21b8",
            "sound": "/sounds/58efe7fd7d56e4c3a874cfd8b7c60",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efe7fd7d5f0fc8a5a12e73cd712",
            "date_created": "2019-07-31T18:43:21.242101Z",
            "created_by": "/users/58efe7fd7d5358f92ec78bb4a21b8",
            "sound": "/sounds/58efe7fd7d5991ea72d5da7c7a1e2",
            "start_seconds": 10.0,
            "duration_seconds": 5.0,
            "end_seconds": 15.0,
            "data_url": null,
            "tags": [
                "crash-cymbal"
            ]
        }
    ],
    "total_count": 100,
    "next": "/annotations?page_size=3&page_number=2"
}
```
#### `404 Not Found`

Provided an unknown annotation identifier
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access this annotation
