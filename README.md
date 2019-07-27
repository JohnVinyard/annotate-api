# Cochlea
Cochlea allows users to annotate audio files on the internet
## `DELETE /`

### Responses

## `GET /`
Return some high-level stats about users, sounds and annotations
### Responses

#### `200`

None
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

#### `200`

Successfully fetched a sound
#### `404`

Provided an unknown sound identifier
#### `401`

Unauthorized request
#### `403`

User is not permitted to access this sound
## `POST /users`
Create a new user
### Responses

#### `201`

Successful user creation
#### `400`

Input model validation error
## `DELETE /users/{user_id}`

### URL Parameters

|Name|Description|
|---|---|
|`user_id`|the identifier of the user to delete|

### Responses

#### `200`

The user was deleted
#### `404`

The user id does not exist
#### `401`

Unauthorized request
#### `403`

User is not permitted to delete this user
## `GET /users/{user_id}`

### URL Parameters

|Name|Description|
|---|---|
|`user_id`|the identifier of the user to fetch|

### Responses

#### `200`

Successfully fetched a user
##### Example Response

```json
{
    "id": "58e9f8c5b367e45ce4f5a42a7fd52",
    "date_created": "2019-07-27T01:26:29.285597Z",
    "user_name": "HalIncandenza",
    "user_type": "human",
    "email": "hal@enfield.com",
    "about_me": "Tennis 4 Life",
    "info_url": null
}
```
#### `404`

Provided an invalid user id
#### `401`

Unauthorized request
#### `403`

User is not permitted to access this user
## `HEAD /users/{user_id}`

### URL Parameters

|Name|Description|
|---|---|
|`user_id`|check if the user with `user_id` exists|

### Responses

#### `204`

The requested user exists
#### `404`

The requested user does not exist
#### `401`

Unauthorized request
#### `403`

User is not permitted to access this user
## `PATCH /users/{user_id}`

### URL Parameters

|Name|Description|
|---|---|
|`user_id`|the identifier of the user to update|

### Example Request Body

```json
null
```
### Responses

#### `204`

The user was successfully updated
#### `400`

Input model validation error
#### `401`

Unauthorized request
#### `403`

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

#### `200`

Successfully fetched a sound
#### `404`

Provided an unknown sound identifier
#### `401`

Unauthorized request
#### `403`

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

#### `201`

Successful sound creation
#### `400`

Input model validation error
#### `401`

Unauthorized request
#### `403`

User is not permitted to create sounds
## `GET /sounds/{sound_id}`

### URL Parameters

|Name|Description|
|---|---|
|`sound_id`|The identifier of the sound to fetch|

### Responses

#### `200`

Successfully fetched sound
##### Example Response

```json
{
    "id": "58e9f8c5c29a8e76800a4b4b36a02",
    "date_created": "2019-07-27T01:26:29.347808Z",
    "created_by": "/users/58e9f8c5c2768e612f3a45cf79e2f",
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
#### `404`

The sound identifier supplied does not exist
## `HEAD /sounds/{sound_id}`

### URL Parameters

|Name|Description|
|---|---|
|`sound_id`|The identifier of the sound to fetch|

### Responses

#### `204`

The sound identifier exists
#### `404`

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

#### `200`

Successfully fetched a list of annotations
#### `404`

Provided an unknown sound identifier
#### `401`

Unauthorized request
#### `403`

User is not permitted to access annotations for this sound
## `POST /sounds/{sound_id}/annotations`
Create a new sound
### URL Parameters

|Name|Description|
|---|---|
|`sound_id`|The identifier of the sound to annotate|

### Responses

#### `201`

Successful annotation creation
#### `400`

Input model validation error
#### `401`

Unauthorized request
#### `403`

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

#### `200`

Successfully fetched a list of sounds
#### `404`

Provided an unknown user identifier
#### `401`

Unauthorized request
#### `403`

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

#### `200`

Successfully fetched a list of annotations
##### Example Response

```json
{}
```
#### `404`

Provided an unknown user identifier
#### `401`

Unauthorized request
#### `403`

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

#### `200`

Successfully fetched an annotation
#### `404`

Provided an unknown annotation identifier
#### `401`

Unauthorized request
#### `403`

User is not permitted to access this annotation
