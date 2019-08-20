# Noticeboard

An automation and news curation tool for busy organizers 

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


