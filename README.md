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
            "id": "58efdf105e0d05bc1e43cdaeaa4cb",
            "date_created": "2019-07-31T18:03:25.117663Z",
            "user_name": "HalIncandenza",
            "user_type": "human",
            "email": "hal@eta.net",
            "about_me": "Tennis 4 Life",
            "info_url": "https://halation.com"
        },
        {
            "id": "58efdf105e116c79bfb3fec0a1b5f",
            "date_created": "2019-07-31T18:03:25.117726Z",
            "user_name": "MikePemulis",
            "user_type": "human",
            "about_me": "Tennis 4 Life",
            "info_url": "https://peemster.com"
        },
        {
            "id": "58efdf105e14c7d9daa5f4bbf3a98",
            "date_created": "2019-07-31T18:03:25.117779Z",
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
    "id": "58efdf105f5a89b4fd1423a94f6b8",
    "date_created": "2019-07-31T18:03:25.122995Z",
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

Successfully fetched a sound
##### Example Response

```json
{
    "items": [
        {
            "id": "58efdf106101161aa67ab962fa487",
            "date_created": "2019-07-31T18:03:25.129761Z",
            "created_by": "/users/58efdf1060f8b2b40437b03206a0e",
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
            "id": "58efdf106105b42a337339375de58",
            "date_created": "2019-07-31T18:03:25.129827Z",
            "created_by": "/users/58efdf1060f8b2b40437b03206a0e",
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
            "id": "58efdf106109295ce2f0d0ab1cb43",
            "date_created": "2019-07-31T18:03:25.129880Z",
            "created_by": "/users/58efdf1060f8b2b40437b03206a0e",
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
    "next": "/sounds?page_number=1&page_size=3"
}
```
#### `404 Not Found`

Provided an unknown sound identifier
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access this sound
## `POST /sounds`
Create a new sound
### Example Request Body

```json
{
    "example": 10
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
    "id": "58efdf1061d3ffa48aea9fcd4d65e",
    "date_created": "2019-07-31T18:03:25.133127Z",
    "created_by": "/users/58efdf1061cf9a9cf73d4c456affc",
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
Get a list of annotations
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
#### `404 Not Found`

Provided an unknown sound identifier
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access annotations for this sound
## `POST /sounds/{sound_id}/annotations`
Create a new sound
### URL Parameters

|Name|Description|
|---|---|
|`sound_id`|The identifier of the sound to annotate|

### Responses

#### `201 Created`

Successful annotation creation
#### `400 Bad Request`

Input model validation error
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to create annotations
## `GET /users/{user_id}/sounds`
Get a list of sounds belonging to a user
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
#### `404 Not Found`

Provided an unknown user identifier
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access sounds from this user
## `GET /users/{user_id}/annotations`
List annotations created by a user
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
{}
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
#### `404 Not Found`

Provided an unknown annotation identifier
#### `401 Unauthorized`

Unauthorized request
#### `403 Forbidden`

User is not permitted to access this annotation
