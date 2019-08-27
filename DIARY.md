# Noticeboard

An automation and news curation tool for busy organizers 

--------------------------------------------------------------------------------
_27 Aug 2019_

## Shared folders issues

Jamming the shared folders into a docker container for testing is one thing,
but deployment requires you get all the shared stuff together in the real file 
system, which means -- sorry to say -- a local build step. _Or_ we try git
submodules. But I really don't want to do that.

--------------------------------------------------------------------------------
_24 Aug 2019_

## Code (re)organization

The point is to allow _multiple deployments of functions and services per
bounded context_.

Here is the basic GCP deployment stuff:

    api-test
      |---- images
      |---- test
    bin
    images
    secrets
    secrets.enc
    cloudbuild-deploy.yaml
    cloudbuild-test.yaml

Then instead of 'functions', 'services':

    domain
      |---- Article
              |---- adapter               # shared external interfaces
                      |---- pubsub.py
                      |---- datastore.py
                      |---- wsgi.py
              |---- env                   # environment bindings per component
                      |---- app.py
                      |---- core.py
                      |---- fetch.py
              |---- model                 # shared models
                      |---- command.py
                      |---- article.py
              |---- test                  # tests per component
                      |---- app
                      |---- core
                      |---- fetch
              |---- util                  # shared utils

              |---- app.py                # UI (GAE service)
              |---- app.yaml              # GAE deployment config for UI
              |---- core.py               # core article update (function)
              |---- fetch.py              # fetch/clean (domain service)


And `app`, `core`, `fetch` could have their own code under `app/`, `core/`, 
`fetch/` etc.

This *almost* works, having multiple deployment targets - multiple entrypoints -
within the same directory. With one problem: the requirements.txt file. Yes,
you could have one requirements.txt that covers everything, but it seems
wasteful to e.g. install gunicorn for the functions, or conversely to install
newspaper and markdown for anything except `fetch`. And that waste adds time
every time you test.

Trying again:

    domain
      |---- Article
              |---- shared
                      |---- adapter               # shared external interfaces
                              |---- pubsub.py
                              |---- datastore.py
                              |---- wsgi.py
                      |---- model                 # shared models
                              |---- command.py
                              |---- article.py
                      |---- util                  # shared utils
              |---- Core
                      |---- images
                              |---- test
                      |---- src
                      |---- test
                              |---- requirements.txt
                      |---- env.py
                      |---- main.py
                      |---- requirements.txt
              |---- Fetch
                      |---- images
                              |---- test
                      |---- src
                      |---- test
                              |---- requirements.txt
                      |---- env.py
                      |---- main.py
                      |---- requirements.txt
              |---- UI
                      |---- images
                              |---- test
                      |---- frontend
                      |---- src
                      |---- test
                              |---- requirements.txt
                      |---- env.py
                      |---- main.py
                      |---- app.yaml
                      |---- requirements.txt


This has the advantage of being very similar to the current structure, but
with the additional layer of the 'bounded context' (e.g., Article) to which the
functions and apps belong.

The key question though is how to make the shared code accessible to each
component (under src/ of each)? 

1. **Git submodules.** This is probably the "preferred professional method"
at the moment. It means easy editing and syncing from within each component.
But comes with some complexity, including when you deploy.

2. **Package as a library.** Clunkier for editing, and same complexity when
you deploy and have to deal with private repos.

3. **Copy folders on test and deploy.** You could copy in the shared code
when building the test containers, and during Cloud Build prior to deploy. 
This means no local testing outside of containers. And editing may be slightly
cumbersome since you have to pop out of the component.

If we went with #3, we'd probably want to move out the container images for
testing like so:

    domain
      |---- Article
              |---- images
                      |---- Core
                              |---- test
                      |---- Fetch
                              |---- test
                      |---- UI
                              |---- test


Then something like this for their content (assuming it will be run from
`domain/Article`):

    FROM gcr.io/my-project/python-test

    COPY Core/ /

    COPY shared/ /Core/src/

    ... etc.

Or actually maybe move the images to the very top level:

    images
      |---- domain
              |---- Article
                      |---- Core
                              |---- test
                      |---- Fetch
                              |---- test
                      |---- UI
                              |---- test


Then we could deal with the secrets copying at the same time:

    FROM gcr.io/my-project/python-test

    COPY domain/Article/Core/ /

    COPY domain/Article/shared/ /src/

    COPY secrets/test/ /secrets/

    ... etc.


Note we likely will want to have secrets organized per bounded context rather
than per function/service.



_21-23 Aug 2019_

## Back from the serverless frontier... what is this thing again?

Basically the idea is to automate a process now carried out manually. Someone
sends a link to an article on email, perhaps with some excerpts or a comment.
These links, or some curated set of them, are gathered together each week and
formatted to go out in a "Noticeboard" email, to a selected group. One issue is 
that many mainstream news sources are paywalled so to make it accessible, key 
articles have to be copy-pasted into email and sent around by those who do have 
access.  (None of this violates terms of service BTW.)

The automation deals with both the gathering process and the paywall issue. 
The email is polled (IMAP), parsed into links and comments/excerpts, sent
through the 'fetch' function (which I have drafted) to download and clean the
article, and into the 'write' function to save it somewhere. A website serves
this content as a weekly list of links and/or RSS feed, with the ability to
curate i.e. filter. Another scheduled task gathers these weekly lists into a
formatted email to send to a list of recipients.

## Next steps

As always the focal point is - what would make the system immediately more 
useful than it is now? In this case, considering I can be the "first user",
I think the most likely candidate is the frontend for displaying article lists. 
We have a way (clunky, it's true) to publish. If we have a way of rendering
saved article links, we can copy-paste into an email just like that, and that
will be a big step forward from manual formatting.

From a devops perspective, this will also flesh out service (i.e. GAE app)
deployment and interaction with PubSub.

But first we need to deal with storage, i.e. the write function. 

## The write function is not actually a good thing to isolate, is it?

Right off the bat there are a few, likely interconnected, weaknesses that 
indicate the conceptual organization is a bit ... myopic:

1. Difficult to share models between the write and the read sides, when there
is no obvious need for the storage to be split CQRS style;

2. Unclear why we can't just store the article in-process after we fetch it; 
what is the aim of putting a queue abstraction here?

3. The actual process we want is probably more like: write un-fetched link to
storage; kick off asynchronous fetch/clean; update model once fetched/cleaned.

From the point of view of code organization, we really want all the models 
and storage adapters etc. used within a bounded context to be together - to use 
the DDD jargon. Right now the code is oriented towards the platform instead, 
i.e. encapsulated within individual functions or services. 

In this case we are talking about the bounded context of the 
_requested article_. It's quite basic, so difficult to see what the 
"constraints" of this context are that we are "protecting", but it seems there
are two or possibly three states: requested, fetched, and cleaned, or maybe
fetched and cleaned are the same state. If we center the code then around 
updating article state, we can see that there is not just one "write" operation,
but at least 2 and maybe 3. There may be more operations in the future. 

Implementation-wise, let's say this core bounded context is a GCP function.
Then the pubsub queue that it's listening to (and there can only be one) has
to "mux" the update operations: in other (DDD) words, it has to be _commands_ 
coming in, not just entities. The fetch/clean function I think is best concept-
ualized as what DDD calls a _domain_ service: it shares the domain models. 

It's an interesting question whether or not it itself writes back commands
(e.g. "store fetched article") to the core function input queue. If we think
about the Elm architecture here, it's still the application's responsibility
to `Sub.map` subscription results back into `Msg` -- not the external service
writing data back to the incoming port.  But here, to accomplish that mapping
we'd need a separate function listening on a separate pubsub queue coming in
from the fetch/clean service, whose only job is to insert the payload into a
command structure to send along into the core function. All this seems very
wasteful and unnecessary. My vote is to have domain services know about 
constructing commands themselves, so they can just write directly back to the
command queue.

An alternative is to consider the fetch/clean function as an external service.
It does not after all require any domain logic - it is purely technical from
the point of view of the users. This is kind of where I was headed with it
so far. But the problem is what I just raised: you then need a piece of code
(perhaps an http callback instead of a pubsub subscription) to deal with 
translating its results back into domain commands. Code is not cheap in a 
distributed system.


--------------------------------------------------------------------------------
_17 Aug 2019_

## One obvious thing is missing from both Functions and Run

There is no control over versioning, making things like rollbacks and canary
releases difficult. I've opened a ticket on it. But meanwhile, there is a 
basic problem with versioning Functions: each function is immutably tied to
(a) a URL, (b) a pubsub topic, or (c) a storage bucket, depending on the 
trigger. You can't just go off and say "make this the active version" of the
function, without also changing these bits of infrastructure. With Run you have
a little more control, but it still means redeploying to make a change to the
connected infrastructure.

## Stepping back

The application can be considered a graph of function nodes and pubsub topic-
subscription edges, with some nodes (http- or storage- triggered) providing
'entrypoints' into the graph.

Keeping this in mind, what if we deploy the *entire graph* on every deployment,
with functions and pubsub topics and storage buckets (and whatever other
infrastructure, e.g. datastore namespace, MySQL db, etc.) named with the 
SHA-hash of the commit? Then we have a self-contained application that does not
interact with code from a previous commit.

Because of the superior tooling available for GAE, traffic splits etc., I would
say the user-facing part of the application, which is an entrypoint into the
graph, may be better implemented in GAE. But be that as it may, whatever the
entrypoint apps are implemented in, they need to know *which application 
version, i.e. which SHA* is the one they publish to.

A typical scenario: you have deployed an application and tested it and are
ready now to promote it to staging/UAT, or production. What does this look like?

_If_ the application had no persistent storage, it would simply be a matter of
redeploying the entrypoint services to a public endpoint (myapp.appspot.com or
myproject.cloudfunctions.net/myfunction) rather than a SHA-hash identified one.
But persistent storage means, *in addition*, that any services/functions that
access this storage need to be redeployed to point to the appropriately-
identified locations rather than SHA-hash identified ones.

So fundamentally there are two variables. I don't know if these should be passed
into the functions/services as env vars or just used in the cloudbuild.

    APPLICATION_VERSION = $SHORT_SHA  
    APPLICATION_STAGE   = test | staging | production

If `APPLICATION_STAGE` is `test`, then all the infrastructure, i.e. temporary as
well as persistent storage, should be identified with `APPLICATION_VERSION`.

If `APPLICATION_STAGE` is `staging` or `production`, then temporary storage
should be identified with `APPLICATION_VERSION`, but persistent storage should
be identified with `APPLICATION_STAGE` itself.

## What does this mean for build config?

It seems like, given these variants, there should be two cloudbuild.yaml config
files: let's call them cloudbuild.yaml and cloudbuild-promote.yaml. 

Regular cloudbuild.yaml is triggered by a push to the `test` branch. This 
unit tests and deploys each function/service under the SHA hash with the 
`APPLICATION_STATE` as `test`, creating infrastructure as needed using the SHA 
hash, and then runs system tests on it.

Then cloudbuild-promote.yaml is triggered by a push to the `staging` or 
`production` branch. This redeploys each entrypoint function/service to a
fixed URL (no SHA hash) but pointing its internal (pubsub topic) references
to names *with* SHA hashes. And it redeploys any function/service that deals
with persistent data to point to fixed references (no SHA hash). No unit 
or system tests are run. It's only a change to config of existing functions/
services.

## A complication

This attempt to reconfig previously deployed functions in the 'promote' deploys 
is going to lead to trouble, because now what happens if you go back and try
to run tests on a given SHA version? Some of those components are now configured
to mess with actual (staging or production) infrastructure. 

Mutability kills us every time...

So I think the promote deploy is going to have to redeploy *every* function/
service under fixed names and be reconfigured to use fixed references to 
infrastructure. This of course kills the idea of 'clean cutover', and we might
as well go back to not using SHA-hash naming.

The simple option for clean cutover is to have two production environments 
that point to the same persistent infrastructure. Assuming the entrypoint app
is GAE, you can use its promote mechanism to point `myapp.appspot.com` to
either `prod-blue-dot-myapp.appspot.com` or `prod-green-dot-myapp.appspot.com`. 
And alternate between production deploys to either blue or green. The devil is 
in the details for database schema migrations though, you really have to be
careful.

You also have to look at any other entrypoints, e.g. cron targets. I think 
you'd have separate Cloud Scheduler jobs per environment, but you need to
disable the non-active one during the cutover. Looks like `pause` might 
be all we need to do.



--------------------------------------------------------------------------------
_16 Aug 2019_

## Functions vs Run

In terms of effect on the code base, there's not much difference between 
Functions and Run. You can easily wrap functions in a generic WSGI interface,
that could be used to re-deploy them from Functions to Run if needed.

Isolating the app in a docker container and running tests against it from the 
outside, *before* deploy, sounds nice and all, but when you really think about
it, that's a very expensive test rig, considering it doesn't test much more
than the unit test does. I think the main principle of tests run before deploy, 
whether locally or in Cloud Build, should be: the faster the better. They
should ideally not hit infrastructure, and should mock out adapters if they do.

This also means that a lot of the questions about injecting environment 
variables into the test rig go away.

## Cloud Build steps

Assuming Cloud Functions, with the following directory structure:

    .gitignore
    bin
        |--- kms
    secrets.enc
        |--- ${_ENV}
                 |--- service_account.json.enc 
    cloudbuild.yaml
    functions
        |--- ${_FUNCTION_NAME}
                 |--- config
                        |--- ${_ENV}.yaml
                 |--- secrets
                 |--- test
                        |--- unit
                               |--- requirements.txt
                        |--- api
                               |--- requirements.txt
                 |--- main.py
                 |--- requirements.txt
                 |--- tox.ini
                 |--- .gcloudignore
        


Then these might be the steps in cloudbuild.yaml:


    - name: 'gcr.io/cloud-builders/gcloud'   
      entrypoint: './bin/kms'
      args:
      - decrypt 
      - 'secrets.enc/${_ENV}'
      - 'functions/${_FUNCTION_NAME}/secrets'

    - name: 'python:3.7-alpine'
      dir: 'functions/${_FUNCTION_NAME}'
      entrypoint: '/bin/sh'
      args: 
      - -c
      - 'pip install -r test/unit/requirements.txt && tox -e unit'

    - name: 'gcr.io/cloud-builders/gcloud'
      dir: 'functions/${_FUNCTION_NAME}'
      args: 
      - functions 
      - deploy 
      - ${_FUNCTION_NAME}_${_ENV} 
      - --env-vars-file
      - 'config/${_ENV}.yaml'

    - name: 'python:3.7-alpine'
      dir: 'functions/${_FUNCTION_NAME}'
      entrypoint: '/bin/sh'
      args: 
      - -c
      - 'pip install -r test/api/requirements.txt && tox -e api'


Note `_ENV` and `_FUNCTION_NAME` are determined by Cloud Build triggers.
`_ENV` comes from the branch name. And `_FUNCTION_NAME` comes from the 
"include files" filter.  But you can specify these manually too in 
`gcloud builds`.



--------------------------------------------------------------------------------
_14 Aug 2019_

## Rethinking the platform

Cloud Functions seems a decent 'fit', at least for the basic fetching and 
processing of webpages that's required here. But I have some concerns:

1. Vendor lock-in
2. Is Cloud Functions going to be supported long-term

Especially in light of Cloud Run, which is Google's newest serverless option,
which I can see displacing Cloud Functions. It's "bring your own runtime" but
also with easy integration with Google services, so what is the advantage of
GCF? Caching global connections?

Of course the KNative infrastructure is not exactly vendor-neutral. But it is 
less closed-source than the GCF runtimes. You'd have your containerized app as
a set of webservers. You'd then just need to work out the means of communication
between them (i.e. replace pubsub, storage triggers, cron, etc.) on some new
infrastructure. And I think KNative has some kind of standards around these
things (although I don't see that Cloud Run really uses them).


## Rethinking 'init'

Pubsub topic creation I think is better thought of as an infrastructure concern
instead of an application concern. It's a one-off. Note with Cloud Run you also
have to handle hooking up the subscription to the service endpoint. This can
also be done via gcloud: and in fact *can be done as a deployment step*.


## Rethinking the pubsub (and other) adapter

It's a pain the ass to have to do stuff like this everywhere:

    pubsub_client = pubsub.publisher_client(env.service_account_credentials())
    pubsub.publish(pubsub_client, env.pubsub_topic(), ... )

It's enough to make you resort to OOP !

I don't have a better suggestion for now though. I suppose you could hide away
everything in `env` and do:

    env.publish(thing)


The bigger issue of course is the need to have environment variables available
at various stages, e.g. during build time, run time, and during testing, 
particularly API testing.

The problem is more or less solved for remote builds: the single source of 
truth is the `.cloudbuild.yaml` (well, and the env vars injected from Cloud 
Build triggers). But if we want to be able to do API testing both locally and 
during build, how do we get those env vars into e.g. tox.ini ?


## Stepping back 

The question is complicated somewhat by what do we mean by local API testing.
It's possible, unlike with GCF, to `docker run` locally on localhost:8080.
But of course that's just a single container; we can't do a pubsub subscription
that forwards to a localhost endpoint. So this local API testing is really a
kind of _integration testing_ I would say; it doesn't exercise the API through
pubsub but building up requests _as if called into from pubsub_ (base64-encoded
payloads and all). In this way I think it's a fundamentally different kind of 
test that what we were looking at with GCF API tests.

Thinking through this, the API testing we really want to be doing against 
_actually deployed_ services **should not** be about publishing messages to
pubsub to trigger private service endpoints. It **should** be about hitting 
public service (http) endpoints, that in turn publish to pubsub, and trigger
private endpoints. These are _system tests_ after all: they should exercise
the public API only.

It now occurs to me this is another great advantage of Run over Functions: 
you can do this kind of single-service integration testing without deploying,
since the services are just webserver containers.

In fact, with the `cloud-build-local` tool, we can build/test locally using 
the same cloudbuild config file. 


## Back to environment variables

Basically for the kind of services we're talking about that subscribe to a 
pubsub topic and then publish to another pubsub topic, the integration tests
just need to know the `project_id` and output `topic`, from environment 
variables. And I suppose the `port` running on localhost, but we can probably
assume 8080.

_If_ we're able to use `cloud-build-local` to run a test cloudbuild config file
(that doesn't actually push an image or deploy), then we'd need to insert the
env vars via _substitutions_ on the command line. 


--------------------------------------------------------------------------------
_12 Aug 2019_

## Devops considerations

I propose the following workflow:

1. Create from cookiecutter template.
2. As a post-gen cookiecutter hook, install build tools:

    virtualenv .env
    . .env/bin/activate && pip install black tox
    git init .
    git add -A && git commit -m "initial commit"
    git branch template
    cp .git-hooks/* .git/hooks/   # run black as pre-commit hook ?
    rm -fr .git-hooks

3. To test locally, `tox`, which runs `flake8` and then 
   `envrun -e config/test.yaml pytest`. Setting up tox.ini for non-package 
   testing.

4. Pre-deploy, `gcloud kms encrypt ...` the secrets files.

5. To deploy, push to production/staging/test branch. This triggers Cloud Build
   to run using a cloudbuild.yaml file or files.  I think perhaps the
   production/staging config files can be parameterized; but the test config
   may need to be a separate file, since it runs integration tests.

  The test deploy looks like:

  1. decrypt secrets
  2. install tox
  3. run tox (which runs linter and tests using the `config/{env}.yaml` env vars)
  4. deploy the init and actual functions with `config/{env}.yaml` env vars. 
     This will automatically install requirements.txt for each of them on 
     Google infrastructure, etc.
  5. hit the init function to trigger pubsub topic creation, etc.
  6. run tox again for an "integration" test environment, which tests hit the 
     actual deployed API (e.g. http endpoint or pubsub), and verify logs and/or
     persisted data.

  So something like this:

    - (gcloud)   gcloud kms decrypt ... --plaintext-file=secrets/service_account.json"
    - (python37) bash -c "virtualenv .env"
    - (python37) bash -c ". .env/bin/activate && pip install tox"
    - (python37) bash -c ". .env/bin/activate && tox -e unit"
    - (gcloud)   gcloud functions deploy my_function_init_$_ENV --env-vars-file=config/$_ENV.yaml
    - (gcloud)   gcloud functions deploy my_function_$_ENV --env-vars-file=config/$_ENV.yaml
    - (gcloud)   gcloud functions call my_function_init_$_ENV
    - (python37) bash -c ". .env/bin/activate && tox -e integration"


## Why tox + virtualenv instead of docker?

One word: speed. Yes it would be nice to get rid of the virtualenv layer and
simply test in isolated docker containers, whether in Cloud Build or locally.
But I tried that, and building the docker containers (as you would have to do
each time you changed your code or tests) is pretty sluggish. 

The other thing that docker shines in for testing is the ability to mount a
network of isolated containers that can talk to each other and the outside 
world (docker compose). But in this case we are building on Google 
infrastructure, not raw containers, so there is no advantage to mounting a
bunch of containers with e.g. no pubsub between them. At least not without some
kind of pubsub emulation layer (which I gather the Cloud Functions nodejs people 
are working on).

## Next steps

Getting set up on Cloud Build feels a bit daunting and not entirely necessary
at the beginning. We can always `gcloud functions deploy` manually. I think
the next thing is to deploy and then write the integration tests. Which perhaps
to be more precise should be called API tests.

I think the manual steps can be implemented as `bin/` shell scripts. Then when
we move to Cloud Build these can just be ignored, or used as a backup.


