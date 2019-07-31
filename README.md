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
            "id": "58efe883656f36c9575b768037f7b",
            "date_created": "2019-07-31T18:45:41.653257Z",
            "user_name": "HalIncandenza",
            "user_type": "human",
            "email": "hal@eta.net",
            "about_me": "Tennis 4 Life",
            "info_url": "https://halation.com"
        },
        {
            "id": "58efe883657454adaa7c4e440f067",
            "date_created": "2019-07-31T18:45:41.653325Z",
            "user_name": "MikePemulis",
            "user_type": "human",
            "about_me": "Tennis 4 Life",
            "info_url": "https://peemster.com"
        },
        {
            "id": "58efe8836577ef1bfa6dac66b1ad1",
            "date_created": "2019-07-31T18:45:41.653382Z",
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
    "id": "58efe88366c259d10efa136439f53",
    "date_created": "2019-07-31T18:45:41.658672Z",
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
            "id": "58efe883683cf021bdd29e3976db4",
            "date_created": "2019-07-31T18:45:41.664727Z",
            "created_by": "/users/58efe883683819f0e1437cc47d3da",
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
            "id": "58efe883684078a5e1e97f9bf3013",
            "date_created": "2019-07-31T18:45:41.664781Z",
            "created_by": "/users/58efe883683819f0e1437cc47d3da",
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
            "id": "58efe88368439130b690f61b12580",
            "date_created": "2019-07-31T18:45:41.664832Z",
            "created_by": "/users/58efe883683819f0e1437cc47d3da",
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
    "id": "58efe8836917b1f2282aa88026b52",
    "date_created": "2019-07-31T18:45:41.668228Z",
    "created_by": "/users/58efe8836912d41e88b7348bb02f7",
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
            "id": "58efe8836a23dc411fad3598e5b10",
            "date_created": "2019-07-31T18:45:41.672521Z",
            "created_by": "/users/58efe8836a1ba78ab8b16861c4c6c",
            "sound": "/sounds/58efe8836a21df36a50cd9bc1d552",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "58efe8836a26380c29e4a1d485f8b",
            "date_created": "2019-07-31T18:45:41.672552Z",
            "created_by": "/users/58efe8836a1ba78ab8b16861c4c6c",
            "sound": "/sounds/58efe8836a21df36a50cd9bc1d552",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efe8836a28d0372218d39befb86",
            "date_created": "2019-07-31T18:45:41.672596Z",
            "created_by": "/users/58efe8836a1e95a4915ab257c9b4f",
            "sound": "/sounds/58efe8836a21df36a50cd9bc1d552",
            "start_seconds": 0.0,
            "duration_seconds": 12.3,
            "end_seconds": 12.3,
            "data_url": "https://s3/fft-data/file.dat",
            "tags": null
        }
    ],
    "total_count": 100,
    "next": "/sounds/58efe8836a21df36a50cd9bc1d552/annotations?page_size=3&page_number=2"
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
            "id": "58efe8836b8c2a07048d27243be7e",
            "date_created": "2019-07-31T18:45:41.678282Z",
            "created_by": "/users/58efe8836b8680f6c246ba7738d35",
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
            "id": "58efe8836b8f7761498749e122cf1",
            "date_created": "2019-07-31T18:45:41.678333Z",
            "created_by": "/users/58efe8836b8680f6c246ba7738d35",
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
            "id": "58efe8836b91f7b2f92937941609f",
            "date_created": "2019-07-31T18:45:41.678373Z",
            "created_by": "/users/58efe8836b8680f6c246ba7738d35",
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
    "next": "/users/58efe8836b8680f6c246ba7738d35/sounds?page_number=2&page_size=3"
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
            "id": "58efe8836c452f4c8a8970a819d72",
            "date_created": "2019-07-31T18:45:41.681240Z",
            "created_by": "/users/58efe8836c3fa1416b7de9b6d203c",
            "sound": "/sounds/58efe8836c433f9c88a06f938c694",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "kick"
            ]
        },
        {
            "id": "58efe8836c471622484a32f4a9615",
            "date_created": "2019-07-31T18:45:41.681270Z",
            "created_by": "/users/58efe8836c3fa1416b7de9b6d203c",
            "sound": "/sounds/58efe8836c433f9c88a06f938c694",
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
    "next": "/users/58efe8836c3fa1416b7de9b6d203c/annotations?page_size=2&page_number=2"
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
            "id": "58efe8836ce11acd237c747b530b7",
            "date_created": "2019-07-31T18:45:41.683735Z",
            "created_by": "/users/58efe8836cd911b4fd05b62fbc41e",
            "sound": "/sounds/58efe8836cdca0b2c95db4cd9af55",
            "start_seconds": 1.0,
            "duration_seconds": 1.0,
            "end_seconds": 2.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efe8836ce2fe51e6491a4361092",
            "date_created": "2019-07-31T18:45:41.683764Z",
            "created_by": "/users/58efe8836cd911b4fd05b62fbc41e",
            "sound": "/sounds/58efe8836cdca0b2c95db4cd9af55",
            "start_seconds": 2.0,
            "duration_seconds": 1.0,
            "end_seconds": 3.0,
            "data_url": null,
            "tags": [
                "snare"
            ]
        },
        {
            "id": "58efe8836ce4ba6e99f56d44f39b3",
            "date_created": "2019-07-31T18:45:41.683792Z",
            "created_by": "/users/58efe8836cd911b4fd05b62fbc41e",
            "sound": "/sounds/58efe8836cdf43d750375d75255fc",
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
