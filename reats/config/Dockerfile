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
RUN mkdir -p /usr/src/app/customer_app \
    /usr/src/app/cooker_app \
    /usr/src/app/custom_renderers \
    /usr/src/app/delivery_app \
    /usr/src/app/source \
    /usr/src/app/tests \
    /usr/src/app/utils

# set work directory
WORKDIR /usr/src/app/

# install dependencies
COPY requirements.txt /usr/src/app/
RUN pip3 install --upgrade pip \
    && pip install -r requirements.txt

# copy project files
COPY customer_app /usr/src/app/customer_app/
COPY cooker_app /usr/src/app/cooker_app/
COPY custom_renderers /usr/src/app/custom_renderers/
COPY delivery_app /usr/src/app/delivery_app/
COPY source /usr/src/app/source/
COPY tests /usr/src/app/tests/
COPY utils /usr/src/app/utils/

# copy manage.py
COPY manage.py /usr/src/app/

# copy config files
COPY config/.env /usr/src/app/
COPY config/wait-for-it.sh /usr/src/app/
COPY config/entrypoint.sh /usr/src/app/
COPY tox.ini /usr/src/app/tox.ini

# set permissions
RUN chmod +x /usr/src/app/wait-for-it.sh \
    && chmod +x /usr/src/app/entrypoint.sh

# Expose ports
EXPOSE 8000
EXPOSE 8001

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
