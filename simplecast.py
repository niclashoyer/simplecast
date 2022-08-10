#!/bin/env python3

from jinja2 import Environment, FileSystemLoader
from wetterdienst import Wetterdienst
from wetterdienst.provider.dwd.mosmix import DwdMosmixType
from wetterdienst.util.cli import setup_logging


def print_stations():
    API = Wetterdienst(provider="dwd", network="mosmix")
    stations = API(parameter="small", mosmix_type=DwdMosmixType.SMALL)
    print(stations.all().df.to_string())


def load_data(station_ids):
    API = Wetterdienst(provider="dwd", network="mosmix")
    stations = API(parameter="small", mosmix_type=DwdMosmixType.SMALL).filter_by_station_id(
        station_id=station_ids)
    return stations.values.all()


def render(weather=[]):
    weather = weather.df.sort_values(by=["station_id", "date"]).pivot_table(
        index=["station_id", "date"], columns="parameter", values="value")
    weather.interpolate(inplace=True)

    print(weather.head())
    file_loader = FileSystemLoader("templates")
    env = Environment(loader=file_loader)
    template = env.get_template("index.html")

    output = template.render(weather=weather.itertuples())

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
