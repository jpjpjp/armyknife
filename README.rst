===============
Getting Started
===============

This application is a full ActingWeb app that uses the python library actingweb.

It implements both a bot and an integration for Army Knife. This is the code running the official
Army Knife Army Knife.

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

Serverless
----------
In order to use serverless, you need awscli, pip, pipenv, Docker, node.js, and serverless.
Also, you need to install the serverless plugins: serverless-python-requirements, serverless-pseudo-parameters, and serverless-wsgi.

You can then update the serverless.yml file with details for your environment and do `serverless deploy`.

AWS Lambda
----------
You can deploy the app to AWS Lamda in three simple steps. There is a serverless.yml file with the config you need.

1. `Install Serverless <https://serverless.com/framework/docs/providers/aws/guide/installation/>`_

2. Edit serverless.yml environment variables, including APP_HOST_FQDN to use your domain (or AWS domain, see 4.) and region if you prefer another

3. Run `sls deploy`

4. (if using AWS allocated domain) Use the long domain name AWS assigns the lambda and go to #2 above

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

