# pull official base image
FROM python:3.10-slim

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# get some useful python lib for dev
RUN apt-get -y update \
    && apt-get -y upgrade \
    && apt-get install -y python3-dev postgresql-server-dev-all gcc musl-dev

# create needed dirs
RUN mkdir -p /usr/src/app/source

# install dependencies
RUN pip3 install --upgrade pip
COPY reats/requirements.txt /usr/src/app/
RUN pip install -r /usr/src/app/requirements.txt

# copy project
COPY reats/client_app /usr/src/app/client_app/
COPY reats/cooker_app /usr/src/app/cooker_app/
COPY reats/custom_renderers /usr/src/app/custom_renderers/
COPY reats/delivery_app /usr/src/app/delivery_app/
COPY reats/source /usr/src/app/source/
COPY reats/tests /usr/src/app/tests/
COPY reats/utils /usr/src/app/utils/


# copy manage.py
COPY reats/manage.py /usr/src/app/

# Expose port
EXPOSE 8000
EXPOSE 8001

# copy env files
COPY reats/config/.env /usr/src/app/

# copy wait-for-it.sh
COPY reats/config/wait-for-it.sh /usr/src/app/

RUN chmod +x /usr/src/app/wait-for-it.sh

# copy entrypoint
COPY reats/config/entrypoint.sh /usr/src/app/

RUN chmod +x /usr/src/app/entrypoint.sh

# copy tox.ini
COPY tox.ini /usr/src/app/tox.ini

# set work directory
WORKDIR /usr/src/app/

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]