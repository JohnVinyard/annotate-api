# Cochlea API

The cochlea API is a very simple set of resources that allow users to annotate sounds on the internet

## Sounds
Resources that represent individual audio files on the internet

### `POST /sounds`
Create a new pointer to a sound on the internet

#### Sample Input
```json
{
    
}
```

### `GET /sounds`
Get a paged list of sounds, ordered from oldest to newest

#### Query Parameters

| name | description |
|------|-------------|
| page_size | number of results per page |
| page_number | page number, which will skip the first `page_size * page_number` records |
| low_id | When streaming sounds, this is last id seen by the client.  Only records created after this one should be returned |

#### Sample Output
```json
{
    
}
```

### `GET /sounds/{sound_id}`
Fetch data about a sound on the internet

#### Sample Output
```json
{
    
}
```
### `GET /users/{user_id}/sounds`
Get a paged list of sounds created by a user, ordered from oldest to newest

#### Sample Output
```json
{
    
}
```

## Annotations
Resources that represent tags, text or dense numerical features that describe a time interval or segment of a sound

### `POST /sounds/{sound_id}/annotations`
Create one or more annotations for a sound

### `GET /sounds/{sound_id}/annotations`
Get a paged list of all annotations for a sound

### `GET /users/{user_id}/annotations`
Get all annotations created by a particular user

## Users

### `POST /users`
### `GET /users`
### `GET /users/{user_id}`

