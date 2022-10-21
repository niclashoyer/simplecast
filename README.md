
A simple static site generator for weather forecasts based on
[wetterdienst](https://github.com/earthobservations/wetterdienst)

![Preview](preview.png?raw=true)

## Installation

```
npm install
poetry install
```

## Build assets

```
npm run build
```

## Generating forecasts

```bash
poetry run ./simplecast.py // list all available stations
poetry run ./simplecast.py 10384 // generate forecasts for "BERLIN-TEMPELHOF"
```
