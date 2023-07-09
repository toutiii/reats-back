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
COPY ../requirements.txt /usr/src/app/
RUN pip install -r /usr/src/app/requirements.txt

# copy project
COPY ./source /usr/src/app/source/

# copy manage.py
COPY ./manage.py /usr/src/app/

# Expose port
EXPOSE 8000
EXPOSE 8001

# copy env files
COPY config/.env /usr/src/app/

# copy entrypoint
COPY config/entrypoint.sh /usr/src/app/

# set work directory
WORKDIR /usr/src/app/

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]