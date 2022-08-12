#!/bin/env python3

from jinja2 import Environment, FileSystemLoader
from wetterdienst import Wetterdienst
from wetterdienst.provider.dwd.mosmix import DwdMosmixType
from wetterdienst.util.cli import setup_logging
import locale


locale.setlocale(locale.LC_TIME, 'de_DE')


def print_stations():
    API = Wetterdienst(provider="dwd", network="mosmix")
    stations = API(parameter="small", mosmix_type=DwdMosmixType.SMALL)
    print(stations.all().df.to_string())


def load_data(station_ids):
    API = Wetterdienst(provider="dwd", network="mosmix")
    stations = API(parameter="small", mosmix_type=DwdMosmixType.SMALL).filter_by_station_id(
        station_id=station_ids)
    return stations.values.all()


def ms_to_bft(ms):
    if ms <= 0.2:
        return 0
    if ms <= 1.5:
        return 1
    if ms <= 3.3:
        return 2
    if ms <= 5.4:
        return 3
    if ms <= 7.9:
        return 4
    if ms <= 10.7:
        return 5
    if ms <= 13.8:
        return 6
    if ms <= 17.1:
        return 7
    if ms <= 20.7:
        return 8
    if ms <= 24.4:
        return 9
    if ms <= 28.4:
        return 10
    if ms <= 32.6:
        return 11
    return 12


def weather_iter(weather):
    for row in weather.itertuples():
        ts = row.Index[1].astimezone("Europe/Berlin")
        yield (ts, row)


def render(weather=[]):
    weather = weather.df.sort_values(by=["station_id", "date"]).pivot_table(
        index=["station_id", "date"], columns="parameter", values="value")
    weather.interpolate(inplace=True)

    print(weather.head())
    file_loader = FileSystemLoader("templates")
    env = Environment(loader=file_loader)
    env.filters["ms_to_bft"] = ms_to_bft
    template = env.get_template("index.html.jinja")

    output = template.render(weather=weather_iter(weather))

    f = open("dist/index.html", "w")
    f.write(output)
    f.close()


def main(stations=""):
    setup_logging()
    if stations == "":
        print_stations()
    else:
        station_ids = stations.split(",")
        weather = load_data(station_ids)
        render(weather)


if __name__ == '__main__':
    import plac
    plac.call(main)
