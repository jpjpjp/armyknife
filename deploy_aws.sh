#!/usr/bin/env bash
docker build -t armyknife-fargate-dev .
docker tag armyknife-fargate-dev:latest 473852420549.dkr.ecr.us-west-2.amazonaws.com/armyknife-fargate-dev:latest
docker push 473852420549.dkr.ecr.us-west-2.amazonaws.com/armyknife-fargate-dev:latest
