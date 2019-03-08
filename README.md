## Data Creation

- User `MusicNet` registers with `type=dataset` and begins creating `/sound` resoruces, as well as the following annotations:
    - full-duration annotation with tagged composer name
    - full-duration annotation with tagged ensemble type
    - short duration tags with instrument tags
    - short duration tags with pitch names
- User `NSynth` registers with `type=dataset` and begins creating `/sounds` resources, as well as the following annotations:
    - full-duration annotation with instrument name, source, family, pitch, and note qualities
- User `PhatDrumLoops` registers with `type = dataset` and begins creating `/sounds/` resources, as well as the following annotations:
    - full-duration annotation with text descriptions

## Text-Based Search
- User `John` registers as `type=human` and searches for annotations with the tag `piano` or `organ` using the search resource `/annotations?query=piano&query=organ`

## Manual Annotation
- User `John` uses a webapp to add some text tags and onsets manually

## Feature Computation
- User `spectrogrambot` registers as `type=featurebot` and begins polling against the `/sounds` resource and creates the following annotations:
    - full-duration binary representations of spectorgrams from each sound.  The data is stored to an S3 bucket, and the `binaryUrl` property of each annotation points to this bucket
- User `mfccbot` registers as `type=featurebot` and begins polling against the `/users/spectrogrambot/annotations` resource and creates the following annotations:
    - full-duration binary representations of MFCC features for each sound
- User `onsetbot` registers as `type=featurebot` and begins polling against the `/sounds` resource and computes the following annotations:
    - annotations that are empty of tags, but delineate onset/offset pairs

## Feature Indexing
- User `mfccindex` registers as `type=featurebot` and draws a large sample of MFCC frames from `/users/mfccbot/annotations`, learns K-Means clusters for MFCC frames, and then polls against the `/users/mfccbot/annotations` resource, creating short, fixed-length annotations that include the cluster centers or "words" belonging to each segment
- Whoever registered user `mfccindex` also starts polling against the `/users/mfccindex/annotations` resource and builds an index, which is searchable via `https://3rdparty.io/mfccindex?word=10&word=1&word=11




# Cochlea Platform

## Sounds

### `/sounds?earliestDate=timestamp`
This returns a paged list of sounds sorted by date created descending.  Sounds will begin at the `earliestDate` timestamp (exclusive) if provided.  This should be an UNIX timestamp in UTC.

### `/sounds/{sound_id}`

Provides high-level metadata about a sound. Identifiers are a [version 1 uuid](https://en.wikipedia.org/wiki/Universally_unique_identifier#Version_1_(date-time_and_MAC_address))

```json
{
    "createdDate": "2019-01-05T19:40:31+0000",
    "createdBy": "/users/12345",
    "infoUrl": "https://phatdrumloops.com/loops",
    "webUrl": "https://phatdrumloops.com/loops/blah.wav",
    "audioUrl": "https://s3-us-west-1.amazonaws.com/cochlea-audio/00322e435c2444384343ab781c1444f1",
    "id": "851f8da0-3909-11e9-b210-d663bd873d93",
    "license": "https://creativecommons.org/licenses/MIT/",
    title: "",
    durationSeconds: ""
}
```

### `/sounds/{sound_id}/audio?start=0&duration=10s`

Returns a high-quality ogg vorbis or mp3 version of the audio.  `start` and `duration` query parameters can be provided, which will return only a slice or segment of the sound.


## Annotations

Annotation ids are version 1 uuids.

### `/annotations?earliestDate=timestamp&durationMin=0&durationMax=0&query=blah`
This returns a paged list of annotations, sorted by date created descending. Annotations will begin at the `earliestDate` timestamp (exclusive) if provided.  This should be an UNIX timestamp in UTC.

Query parameters include:

| name | description |
|------|-------------|
| earliestDate | annotations were created on or after this date |
| durationMin | annotation is no shorter than this |
| durationMax | annotation is no longer than this |
| query | a text-based query to search over tags |

See `/users/{user_id}/annotations` for a way to search for annotations from a specific user

### `/annotations/{annotation_id}`

```json
{
    "createdBy": "/users/1234",
    "createdDate": 2019-01-05T19:40:31+0000",
    "sound": "/sounds/9876",
    "start": 0.01,
    "duration": 1.23,
    "tags": [],
    "binaryUrl": ""
}
```

| name | description |
|------|-------------|
| binaryUrl | A link to an s3 bucket, CDN, or someplace else where the annotation data can be fetched |

## Sound Annotations

### `/sounds/{sound_id}/annotations?durationMin=0&durationMax=0&query=blah&userName=blah`
Fetches a paged list of all the annotations for a sound

Query parameters include:

| name | description |
|------|-------------|
| durationMin | annotation is no shorter than this |
| durationMax | annotation is no longer than this |
| query | a text-based query to search over tags |
| userName | only return annotations from this user |


See `/users/{user_id}/annotations` for a way to search for annotations from a specific user

## Users

### `/users?userType=featurebot&userName=namequery`

Fetch a paged list of all users, sorted by date created descending.  Optionally filter by the type of user and the earliest creation date.

| name | description |
|------|-------------|
| userType | The type of user to filter by |
| userName | a fuzzy user name query |

Users can be one of three types:

- **humans** who can create segments and optionally add tags or text descriptions
- **datasets** (e.g. MusicNet, NSynth, etc), which can create sounds and annotations.  These must be registered with approval from an admin
- **bots** who can create annotations, generally of a single type of feature (e.g., chromabot).  These must be registered with approval from an admin

### `/users/{user_id}`

Returns data about a single user.

```json
{
    "userType": "human"|"dataset"|"featurebot",
    "userName": "MusicNet"|"ChromaBot"|"John",
    "dateCreated": "",
    "aboutMe": ""
}
```

| name | description |
|------|-------------|
| aboutMe | Detailed information about the user, dataset, format of data created by the bot, or the index being created |

### `/users/{user_id}/sounds`
Paged list of all the sounds created by a single user.

### `/users/{user_id}/annotations?earliestDate=timestamp`
Paged list all the annotations from a user, sorted by date created descending.

## Authentication

All authentication is done via basic auth with username/password pairs for now.  API key/secret pairs will probably be supported in the near future.

## Cors

CORS will be supported for all API endpoints

## Clients

Example clients for JavaScript and Python will be published