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
            "id": "58efee4cfd14db2bad3705ed4347b",
            "date_created": "2019-07-31T19:11:35.215452Z",
            "user_name": "HalIncandenza",
            "user_type": "human",
            "email": "hal@eta.net",
            "about_me": "Tennis 4 Life",
            "info_url": "https://halation.com"
        },
        {
            "id": "58efee4cfd19307ee054c5287088c",
            "date_created": "2019-07-31T19:11:35.215515Z",
            "user_name": "MikePemulis",
            "user_type": "human",
            "about_me": "Tennis 4 Life",
            "info_url": "https://peemster.com"
        },
        {
            "id": "58efee4cfd1c989f4f8d6a4028d29",
            "date_created": "2019-07-31T19:11:35.215568Z",
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
    "id": "58efee4cfe6aeafd3dd940e8de21d",
    "date_created": "2019-07-31T19:11:35.220921Z",
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
            "id": "58efee4cffe50f3c25b90a878ac47",
            "date_created": "2019-07-31T19:11:35.226974Z",
            "created_by": "/users/58efee4cffde2dce442f34cee3279",
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
            "id": "58efee4cffeb5adabc24e7844e744",
            "date_created": "2019-07-31T19:11:35.227073Z",
            "created_by": "/users/58efee4cffde2dce442f34cee3279",
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
            "id": "58efee4cfff14f509eb4b2e6d677c",
            "date_created": "2019-07-31T19:11:35.227168Z",
            "created_by": "/users/58efee4cffde2dce442f34cee3279",
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
    "id": "58efee4d00cdab38c478291428d25",
    "date_created": "2019-07-31T19:11:35.230690Z",
    "created_by": "/users/58efee4d00c931311b59ede98486c",
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
            "id": "58efee4d01db10f0ed62dc9431749",
            "date_created": "2019-07-31T19:11:35.234999Z",
            "created_by": "/users/58efee4d01d2dc1e79a5bae772ee3",
            "sound": "/sounds/58efee4d01d90beac87a6f757b8bd",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "58efee4d01dd0c9cd2d424c6a779a",
            "date_created": "2019-07-31T19:11:35.235029Z",
            "created_by": "/users/58efee4d01d2dc1e79a5bae772ee3",
            "sound": "/sounds/58efee4d01d90beac87a6f757b8bd",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efee4d01e0ee11baa900c1104cb",
            "date_created": "2019-07-31T19:11:35.235092Z",
            "created_by": "/users/58efee4d01d5c724f19f05e0927e0",
            "sound": "/sounds/58efee4d01d90beac87a6f757b8bd",
            "start_seconds": 0.0,
            "duration_seconds": 12.3,
            "end_seconds": 12.3,
            "data_url": "https://s3/fft-data/file.dat",
            "tags": null
        }
    ],
    "total_count": 100,
    "next": "/sounds/58efee4d01d90beac87a6f757b8bd/annotations?page_size=3&page_number=2"
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
            "id": "58efee4d03427232b350228c6dd49",
            "date_created": "2019-07-31T19:11:35.240751Z",
            "created_by": "/users/58efee4d033ecd35601634872027a",
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
            "id": "58efee4d03453707a26ed29b5f877",
            "date_created": "2019-07-31T19:11:35.240793Z",
            "created_by": "/users/58efee4d033ecd35601634872027a",
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
            "id": "58efee4d0347c00a8f677169e9f9c",
            "date_created": "2019-07-31T19:11:35.240834Z",
            "created_by": "/users/58efee4d033ecd35601634872027a",
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
    "next": "/users/58efee4d033ecd35601634872027a/sounds?page_number=2&page_size=3"
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
            "id": "58efee4d0420831b8ff7fc7f3b940",
            "date_created": "2019-07-31T19:11:35.244302Z",
            "created_by": "/users/58efee4d041a34cae52800ee0b7c2",
            "sound": "/sounds/58efee4d041dd4aeaf58a30938a9a",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "58efee4d04227781a60308afb1aab",
            "date_created": "2019-07-31T19:11:35.244333Z",
            "created_by": "/users/58efee4d041a34cae52800ee0b7c2",
            "sound": "/sounds/58efee4d041dd4aeaf58a30938a9a",
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
    "next": "/users/58efee4d041a34cae52800ee0b7c2/annotations?page_size=2&page_number=2"
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
            "id": "58efee4d04beb4ae80f33ee3e6fd6",
            "date_created": "2019-07-31T19:11:35.246832Z",
            "created_by": "/users/58efee4d04b664fff7be442bb9112",
            "sound": "/sounds/58efee4d04ba052beb95a9750253b",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efee4d04c0999df0ab387267511",
            "date_created": "2019-07-31T19:11:35.246862Z",
            "created_by": "/users/58efee4d04b664fff7be442bb9112",
            "sound": "/sounds/58efee4d04ba052beb95a9750253b",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efee4d04c256ef176fe8fee1115",
            "date_created": "2019-07-31T19:11:35.246890Z",
            "created_by": "/users/58efee4d04b664fff7be442bb9112",
            "sound": "/sounds/58efee4d04bccb7865681a585eaf4",
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
