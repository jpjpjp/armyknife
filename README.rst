===============
Getting Started
===============

This actingwebdemo application is a full ActingWeb demo that uses the python
library actingweb.

The actingweb library supports both AWS Dynamodb and Google Datastore as database
backends, but this application is deployed to AWS as an Elastic Beanstalk
application and can be found at https://actingwebdemo.greger.io

Basically, the application.py uses the webapp2 framework to map all the endpoints
required by an ActingWeb app and set up handlers (/aw_handlers) for each.
Each handler takes the requests, copies into an actingweb request and calls
the correct endpoint handler from the actingweb library.

There is some boilerplate code, but it is fairly simple to replace webapp2 with
flask or any other web app framework.

Running locally
---------------

You don't have to deploy to AWS to test the app. There is a docker-compose.yml file in the repo that brings up
both a local version of dynamodb and the actingwebdemo app.

1. `docker-compose up -d`

2. Go to http://localhost:5000

You can also use ngrok.io or similar to expose the app on a public URL, remember to change the app URL in
docker-compose.yml.

Running tests
-------------
If you use ngrok.io (or deploy to AWS), you can use the Runscope tests found in the tests directory. Just sign-up at
runscope.com and import the test suites. The Basic test suite tests all actor creation and properties functionality,
while the trust suite also tests trust relationships between actors, and finally the subscription suite tests
subscriptions between actors with trust relationships. Thus, if basic test suite fails, all will fail, and if trust
test suite fails, subscription test suite will also fail.

AWS Elastic Beanstalk
---------------------

1. Install `Elastic Beanstalk CLI <http://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-install.html>`_

2. Edit .ebextensions/options.config to set the hostname you are going to deploy to, region that matches, and the
protocol (default http://, but https:// if you choose to set up that later)

2. Run `eb init`, set region and AWS credentials, create a new app (your new app), and select Docker, latest version

3. Run `eb create` to create an environment (e.g. dev, prod etc of your app). Remember to match the CNAME prefix with
the prefix of the hostname in options.config (the rest is based on region)

4. Deploy with `eb deploy`

5. Run `eb open` to open the app in the browser

Use the library for your own projects
-------------------------------------

For how to use and extend the library, see the `ActingWeb repository <https://bitbucket.org/gregerw/actingweb>`_

