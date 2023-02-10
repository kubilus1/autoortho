#!/bin/bash

apt-get update
apt-get install software-properties-common -y
add-apt-repository ppa:deadsnakes/ppa -y
apt-get update
apt-get install -y make curl patchelf python3.10 python3.10-tk zlib1g-dev \
    ccache python3.10-distutils python3.10-dev libjpeg-dev build-essential

curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

python3.10 -m pip install -U pip
python3.10 -m pip install setuptools
python3.10 -m pip install -r requirements-build.txt
python3.10 -m pip install -r requirements.txt
