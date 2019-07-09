"""
Let's focus on each of the four types of examples I've built thus far:

Datasets
==============
I think this one is safe to ignore for now, and just run from a local machine,
as each is a one-time process that could easily be run from a home machine, or
provisioned to run on an EC2 instance and then shut down.

These do need to provision S3 buckets and set them up with correct CORS headers,
however

Featurebots that listen for sounds
=====================================
These should run/listen forever, but also be cheap.  They need a few components

- a place to persist the last seen id for each bot
- a lambda function that checks for new sounds and pushes them to a second lambda
- a scheduled event to trigger the above lambda
- a lambda function that processes batches of sounds

https://markhneedham.com/blog/2017/04/05/aws-lambda-programatically-scheduling-a-cloudwatchevent/

Featurebots that listen for other annotations/features
=======================================================

These should run/listen forever, but also be cheap.  They need a few compoonents

- a place to persist the last seen id for each bot
- a lambda function that checks for new annotations and pushes them to a second lambda
- a scheduled event to trigger the above lambda
- a lambda function that processes batches of annotations

Indexers
==========
These are a little more tricky, and occur in three distinct phases.
Implementation and deployment could depend a lot on where indexes are stored,
but let's just go with a simple example that hosts an in-memory data store

- Learn the model locally, and push the model data to an s3 bucket
- provision an EC2 instance that will listen for sounds, build an index, and
  serve an HTTP interface to the index

"""