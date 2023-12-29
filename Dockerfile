FROM alpine:latest as build

RUN apk add --update --no-cache --virtual .build-deps \
nodejs \
npm

COPY . /project
WORKDIR /project

RUN npm install
RUN npm run build

FROM alpine:latest
RUN apk add --update --no-cache --virtual .build-deps \
poetry
COPY --from=build /project /project
WORKDIR /project

RUN poetry install

VOLUME /project/dist
CMD poetry run ./simplecast.py
