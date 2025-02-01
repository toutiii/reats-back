# pull official base image
FROM python:3.10-slim

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# get some useful python lib for dev
RUN apt-get -y update \
    && apt-get -y upgrade \
    && apt-get install -y python3-dev postgresql-server-dev-all gcc musl-dev git vim

# create needed dirs
RUN mkdir -p /usr/src/app/reats

# set work directory
WORKDIR /usr/src/app/reats/

# install dependencies
COPY reats/requirements.txt /usr/src/app/reats/requirements.txt
RUN pip3 install --upgrade pip \
    && pip install -r requirements.txt

# copy project files
COPY reats/customer_app /usr/src/app/reats/customer_app/
COPY reats/cooker_app /usr/src/app/reats/cooker_app/
COPY reats/custom_renderers /usr/src/app/reats/custom_renderers/
COPY reats/delivery_app /usr/src/app/reats/delivery_app/
COPY reats/core_app /usr/src/app/reats/core_app/
COPY reats/source /usr/src/app/reats/source/
COPY reats/tests /usr/src/app/reats/tests/
COPY reats/utils /usr/src/app/reats/utils/

# copy manage.py
COPY reats/manage.py /usr/src/app/reats/manage.py

# copy .pre-commit-config.yaml
COPY .pre-commit-config.yaml /usr/src/app/.pre-commit-config.yaml

# copy config files
COPY reats/config/.env /usr/src/app/reats/.env
COPY reats/config/wait-for-it.sh /usr/src/app/reats/wait-for-it.sh
COPY reats/config/entrypoint.sh /usr/src/app/reats/entrypoint.sh
COPY reats/tox.ini /usr/src/app/reats/tox.ini

# set permissions
RUN chmod +x /usr/src/app/reats/wait-for-it.sh \
    && chmod +x /usr/src/app/reats/entrypoint.sh

# Expose ports
EXPOSE 8000
EXPOSE 8001

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/reats/entrypoint.sh"]
