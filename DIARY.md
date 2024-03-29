# Noticeboard

An automation and news curation tool for busy organizers 

Also: an overengineered serverless/DDD/microservices test project for one bored
programmer


--------------------------------------------------------------------------------
_11 Sep 2019_

## Crash and burn

Isolating the domain core as described below ran into some snags. 

The biggest one was that I discovered that _in fact_, when dealing with
externally persisted state, monoidial updates are not necessarily the
most efficient or straightforward way to go. You don't necessarily want to
present the storage layer with the changed state. You want to present it
with _instructions_ to make the changes; a kind of lower-level list of 
Commands.

A second problem is that the storage layer should not determine what events
are published. Events belong in the domain. But (as we identified), you can't
construct the events until the storage layer has done its thing.

One approach to dealing with both of these is to introduce yet another phase, 
so

    fetch(command) -> 
    update(command, aggregate) -> 
    store(instructions) -> 
    create_events(command, aggregate) ->
    publish(events)


But... frankly, the process is already very broken up and hard to follow. We
already have way to much wrapping and unwrapping (commands, aggregates, 
instructions, events all wrap up bits of state in different ways).


### Conflicting concepts

(1) Monoidal, in-memory updates; each new state of the aggregate is synched to 
storage; which in practice might mean a lot of deletion + adds of sub-entities;
but the store function can be made generic over the state (aggregate) structure.

(2) Updates are pushed down to the store function; the core function really only
serves to validate (and perhaps modulate) the requested command. The updates
can be done as efficiently as possible; but the store function is *not* 
generic -- it is part of the domain layer. 

(3) Updates are pushed down to the store function, but the core function 
serves to translate domain commands into storage-layer commands. So the store
function can be made generic over this storage-layer command type.

I like the sound of (3), but the devil is in the details. It does introduce
storage-layer structures into the domain, in one way or another.

As for the publishing of domain events. I wonder about revisiting the idea of
the core function defining a `List (Id -> Event)`. If we make it a rule that
_domain events do not expose any id's except those of the aggregate root_. And
that the store function returns this id, which the shell then uses to construct
and publish the events defined by the core function.

So like this:

    def domain_shell(client, *, fetch, store, publish): 
        def _domain_shell(fn):
            @wraps(fn)
            def __domain_shell(command, user_roles=None):
                aggregate = fetch(client, command)
                store_commands, events = fn(command, aggregate, user_roles=user_roles)
                id = store(client, store_commands)
                for event in events:
                    publish( event(id).to_json() )

            return __domain_shell
        return _domain_shell


_10 Sep 2019_

## The core of the domain

So far my conception of the 'core' function has been impure, looking something
like:

    id = command.thing_id
    fields_to_update = command.data
    storage.update_something_in_thing(env.storage_client(), id=id, fields_to_update)
    env.publish( events.UpdatedSomethingInThing(thing_id=id) )

or perhaps with some dependence on the current state:

    id = command.thing_id
    fields_to_update = command.data
    with storage.transaction():
        thing = storage.get_thing(client, id=id)
        new_thing = update_something_in_thing(thing, fields_to_update)
        storage.store_thing(client, id=id, new_thing)
    env.publish( events.UpdatedSomethingInThing(thing_id=id) )
    

I think that's fine and all, but we can't claim to have a pure functional
core. The domain reaches into storage and pubsub. (Hence the need for mocking
in the tests.) 

The pure functional core starts to appear in the second example in the 
`update_something_in_thing` function which is a monoidal 
`model -> data -> model`. Can we extract it so the surrounding mess can be
a generic decorator around it?  We have been through this exercise before in
another context.

### Input and output

Not every command (1) concerns an existing entity, or (2) needs an entity's 
current state to be loaded in order perform the command, or (3) need the same
type of entity (the root aggregate so to speak; it could be a command modifying
some sub-entity of the root). 

Given this diversity, I feel we need a custom `fetch` function that fetches the
current state of the required entities (or fetches nothing), given the command; 
that will then serve as input to the `core` function. It is not feasible to 
write this generically without expressing the commands in something other than 
domain language.

But more than this, given the fact (3) above: the thing that gets fetched must
be able to be unified under a type. My proposal is to have this be the
subdomain's Aggregate type, under which all the entities can be composed, 
together with their id's; e.g. in this case 

    @dataclass
    class ArticleAggregate:
        id: Id
        url: str
        article: Article
        issues: Iterator[Tuple[Id,ArticleIssue]]
        notes: Iterator[str]

This means that a theoretical command like `IgnoreArticleIssue` would need to
load both `Article` and the underlying `ArticleIssues`. But would a command
like `CommentOnArticle` which has nothing to do with article issues, need to
load them? It seems less restrictive (although more verbose) to define a union
of different aggregate forms needed for the different updates.

    @dataclass
    class ArticleAgg:           # used for `CommentOnArticle` or `SaveFetchedArticle`
        id: Id
        url: str
        article: Article
        notes: Iterator[str]

    @dataclass
    class ArticleIssuesAgg:     # used for `IgnoreArticleIssue`
        id: Id
        issues: Iterator[Tuple[Id,ArticleIssue]]


    Aggregate = Union[ArticleAgg, ArticleIssuesAgg]


I *think* the same Aggregate structure could be used as "instructions" for 
*writing* to storage. For instance if we added a case for "new article", without
an `id`, we could model output of "constructor" commands like 
`SaveRequestedArticle`:

    @dataclass
    class NewArticleAgg:
        url: str
        article: Article
        notes: Iterator[str]


If so, then the core function signature could be

    Command -> Aggregate -> Aggregate

the input Aggregate being the result of the "pre-", `fetch` function:
    
    Command -> Aggregate


### And then what about events?

I have in mind this:

    Command -> Aggregate -> ( Aggregate, Iterator[Event] )

The thing is, for constructor events you don't have id's yet, so you can't
actually construct events. And let's say instead you return a 
`List (Id -> Event)`. it seems like a bit of a hard (verging on impossible) 
problem to determine generically from an Aggregate which id's are needed to 
construct which events in the list.

So... I think the post- function, the one that writes to storage,
also needs to be app-specific. 

    Command -> Aggregate -> Iterator[Event]

The list of events output from this can then generically be published.


### And what about user authorization?

I don't know what this will be yet, but let's assume for events where they are
needed, they get sent (from the UI, for example) in the "attributes" of the
pubsub message. They get dealt with in Core:


Fetch:

    datastore.Client -> Command -> Aggregate

Core:

    Optional[UserRoles] -> Command -> Aggregate -> Aggregate

Store:

    datastore.Client -> Command -> Aggregate -> Iterator[Event]


The remaining question is what about domain logic errors (validation, user
unauthorized, etc.) that happen in the Core function. Should these be
returned in a Union with the Aggregate (monadic Either style), or raised as
errors?  Raising them as errors makes the core function impure; but on the
other hand, it is more pythonic.  I think it is ok to raise them, especially
if they can derive from a base Exception class and be identified and handled 
accordingly.


### Draft implementation


    def domain_shell(client, *, fetch, store, publish): 
        def _domain_shell(fn):
            @wraps(fn)
            def __domain_shell(command, user_roles=None):
                existing = fetch(client, command)
                updated = fn(command, existing, user_roles=user_roles)
                events = store(client, command, updated)
                for event in events:
                    publish( event.to_json() )

            return __domain_shell
        return _domain_shell

### Critique

The main problem as I see it is `fetch`, `core`, and `store`, all have to
agree on the shape of the aggregate given the command. I wonder if to mitigate
this we could organize the modules by command instead of fetch/core/store.


--------------------------------------------------------------------------------
_2 Sep 2019_

## Some considerations for article fetch before moving on

- Instead of choosing the "first strategy that works", we could run through
  **all strategies** and choose the best (the one with the least validation
  errors and largest sized article html, or something);

- We could store "fetch rate per domain" somewhere and slow it down to prevent
  rate limiting; 

- But more than either of these I think the intractable ones are going to need
  a real browser and some scripting for login, if that's even feasible. That
  means standing up a Selenium instance and some kind of steps that can be
  turned into config, not to mention storage of login secrets.

- Another thing is media downloads, esp photos. I don't want to pass these
  over the pubsub wires, they should go directly into storage. Perhaps another
  service to do this that hangs off article.fetch.events ?

## Moving on to article storage (Core)

I think my working storage strategy has been to stick articles into Datastore,
as (a) they are not that large and (b) you get basic querying and fetching
without any work at all, and (c) I can't forsee any complex querying. From 
there if we want full-text search we can kick off a load into BigQuery or 
whatever.

I don't know if that's the right route, but it seems ok as a first attempt.

The main thing it seems like to work out in Datastore is what are the main
hierarchical relationships we want to query on and can we fit those into the
parent-child kind hierarchy, so that ancestor queries can be used effectively.

The rather odd part of how the data flows in in this case, is we have some
very limited user input at first (a url and a comment), then when the fetch
returns we have the full article, but without the initial comment, that needs
to be merged (in some way) with the initial user input; although in another 
sense it is a new state of the 'article'. 

Further, it's likely we will want to have multiple comments per article. So 
really that initial data structure should be stored as:

    RequestedArticle > Comment

That then gets transformed into

    FetchedArticle  > Comment

So 'RequestedArticle' and 'FetchedArticle' are states of Article (the datastore
_kind_).

All this to say, unfortunately yes I think we need some renaming in Fetch.

(Another hierarchy is that between the article and its media (images etc.), 
assuming we want to cache the media as well as the article markup; and the
media themselves we'd want to store in GCS.)








--------------------------------------------------------------------------------
_1 Sep 2019_

## Python logging, a dumpster fire

Is it any wonder so many people have tried to "rewrite logging in anger"?
I just spent the better portion of 2 1/2 days fighting it.


--------------------------------------------------------------------------------
_28 Aug 2019_

## A new proposal for DDD-style services, cleaned up

### Basic definitions

_Bounded contexts_ are the rules governing state changes for a given subdomain.

A given bounded context has one or more _aggregates_ whose state it manages.

_Services_ are the implementation of bounded contexts in the form of 
inter-communicating processes. Bounded contexts are implemented by one or
more services.

There are different kinds of services performing different roles within a
bounded context. There are also generic services that are used independently
of a bounded context, or by several bounded contexts.

### Implementation

Generally speaking, services have input and output streams, but these vary
by the role of the service. 

- Typically services that manage state (**"Core" services**) have _command 
input_ and _event output_. They also may have _event input_ from other 
services and convert that into command input. 

- **Support services** that do not manage state have _event input_ from 
other services and produce _event output_ of their own. 

- Services that send user input into core services (**"UI" or "Command" 
services**) have _external input_ (e.g. through an http endpoint) and send 
_command output_.

In this proposed implementation on top of GCP, _services_ are implemented
by Cloud Functions and/or App Engine instances (and potentially Cloud Run 
containers), communicating via Cloud PubSub.



_27 Aug 2019_

## Shared folders issues

Jamming the shared folders into a docker container for testing is one thing,
but deployment requires you get all the shared stuff together in the real file 
system, which means -- sorry to say -- a local build step. _Or_ we try git
submodules. But I really don't want to do that.

## The process

> The actual process we want is probably more like: write un-fetched link to
>  storage; kick off asynchronous fetch/clean; update model once fetched/cleaned.

It occurs to me another eventing mechanism is Cloud Storage, if we use that for
storage. I don't like being locked in to that; but on the other hand, then we
don't need that custom async messaging between Core -> Fetch -> Core. We just
need a function that listens for changes to storage and dispatches commands
to Core depending on current state. The direction is 

`UI -> Core -> Fetch -> storage -> Core`.  

The other thing is I don't think we actually need to store the thing until it's 
fetched. Or do we, because what do we do with the user-provided note?

`UI -> Core -> storage -> Core -> Fetch -> storage -> Core`.  

But the thing there is, both Core and Fetch write to storage. That's a faint
coupling smell in itself, but then you consider that Fetch actually needs to
write not just the article text, but the author, title, publish date, etc.
Which most likely do not belong in Cloud Storage. Or do they?

## How do we want to search?

Cloud Storage is of course not designed for search. You can do something like
store the searchable data indexed in Datastore but just store a key that points
to the article actually stored in Cloud Storage. _Or_ you can store everything
in Cloud Storage but sync it to BigQuery for search. 

In either case I'm wondering what exactly is the utility of Cloud Storage. We
are not talking about large files (although possibly if we download photos
from articles that would make sense for them). If we are just concerned with
the eventing mechanism, why not just use PubSub?

## A new proposal

    UI -> Core -> datastore
               -> pubsub     -> Fetch -> pubsub -> Core -> datastore
                                                        -> pubsub

It's not obvious from this primitive diagram, but essentially we have 

1. Core in charge of making changes to stored state (writing to datastore). 

2. Whenever Core updates state, it publishes an event to a pubsub topic.

3. Fetch and perhaps other services listen for events on this topic, and write 
back events to another topic.

4. Core listens for events on Fetch's (and other) topics, converts them to 
commands and sends them through its main function.

This is the same as before, except we reduce the coupling between Fetch and
Core. 

Also note that `Core` may have to listen to more than one pubsub topic,
(actually _will_ have to, assuming UI sends commands to Core via pubsub) -- 
which means that Cloud Functions are not going to be suitable. It's possible
to deploy them as different functions sharing the same codebase I suppose. 


### Naming conventions

    Publishing func          Pubsub topic            Subscribing func
    ----------------------------------------------------------------------------
    article_ui_main          -> article.core.command -> article_core_main

    article_core_main        -> article.core.event   -> article_fetch_from_core

    article_fetch_from_core  -> article.fetch.event  -> article_core_from_fetch

    article_core_from_fetch  -> article.core.event


Rules:

1. If nothing specified for a trigger, it's assumed to be 
   `<subdom>.<service>.command`.
2. Otherwise it can be specified like `--subscribe-subdomain`, 
   `--subscribe-service`, which if different than the subscribing func, assumes 
   the "topic type" is `event`.
3. If nothing specified for a publish topic, it's assumed to be 
   `<subdom>.<service>.event`. In fact, services should not publish to anything
   other than this. Regardless of entry point. **EXCEPT!** UI services get
   special privileges to send commands to other services -- typically to _core_. 

The underlying structure is, each service writes _events_ to a single topic; and 
receives _commands_ from a single topic, and _events_ from zero or more
topics from other services. Furthermore, usually only the "core" function in
a subdomain receives commands. Technical services that do not manage state 
themselves (such as fetch) act based on events from core and other services,
not commands.

Because Cloud Functions must be bound to one triggering topic, if we implement
services using Cloud Functions, they must be split up between different 
triggering topics.

Of course, all these names are also modulated by `ENV` and `APP_STATE`.



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


