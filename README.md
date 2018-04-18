# dogatrest

A RESTful Watchdog Service.

## Usecase

You manage different instruments somewhere in the internet.
An instrument is not a service that you can check from the outside but it is rather some program running in an infinite loop, saving some files somewehre eventually.
If one instrument fails to work, you would like to know that and get notified via slack or fleep or whatever.
But simply pinging the instruments is not enough, as it can still be reachable but maybe the main thread failed due to an unexpected error.
So, you start the dogatrest service somewhere and configure an endpoint for the instrument.
The instrument must then POST to this endpoint within a specified interval.
If no request has been recorded for a time bigger than the specified interval, the service makes a POST request to the specified hook.
Typically this hook would be a slak or fleep or whatever endpoint.

## Usage

    git clone https://github.com/jonas-hagen/dogatrest.git && cd dogatrest
    docker build -t dogatrest .
    docker run --rm --name mydogatrest -p 8000:8000

Now the service is up and running on port 8000, use the docker option `-d` if the container should run in the background.

The configuration file contains an example endpoint, that you can use to test the service:

Get the current status of the dog:

    $ curl -X GET localhost:8000/dog/test-1bce5bad2b91 -H "Content-Type:application/json"
    {"interval": 1, "hook": "https://fleep.io/hook/xxxxxxxxxxxxxx", "name": "Test"}

 Keep it alive:

    $ curl -X POST localhost:8000/dog/test-1bce5bad2b91 -H "Content-Type:application/json"
    {
      "interval": 1,
      "hook": "https://fleep.io/hook/xxxxxxxxxxxxxx",
      "name": "Test",
      "last_time": 1524043271.353736,
      "last_time_str": "2018-04-18T09:21:11.353736",
      "last_data": {}
    }

If data is provided in the POST body, it is recorded as `last_data`.
If the dog has never been pinged, it is just ignored and no hooks will be executed.

## Cofiguration

Mount a local configuration folder into the docker container:

    docker run --rm --name mydogatrest -v "$(pwd)"/data:/app/data -p 8000:8000

Now edit the `"$(pwd)"/target:/app/dogs.json` file. Every entry in the root array has a key, that uniquely identifies the dog.
If you are concerned about security, you should choose a key with high entropy (and of course use https).
The configuration of one dog can contain the following elements:

 - *name*: A human readable name of the dog.
 - *interval*: Interval to of the watchdog in minutes.
 - *hook*: A webhook URL to send POST requests to upon status change.
 - *template_dead*: A dictionary containing the payload to be sent to the webhook in case of a dead dog. Default is `{'message': 'I am probably dead. Could anyone check?', 'user': '{name}'}`. (The strings will get interpolated using `.format(**dog)`)
 - *template_alive*: As above but for status change from dead to alive. Default: `{'message': 'Back to life! Thanks.', 'user': '{name}'}`
 
 
 ## Funny stuff
 
 You can install a dog like this and install the webhook in your git repository:
 
     "gitrepo-xxxxxxxx": {
       "hook": "https://team.slack.com/xxxxxx",
       "interval": 600,
       "template_dead": {
         "text": "Get back to work! There has been no activity on the repo since {last_time_str}!"
       },
       "template_alive": {
         "text": "Ok, now we are talking! Thanks!"
       }
     }
     

Yeah, let the bots dictate your life! You won't regret it!

