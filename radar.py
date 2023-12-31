import logging
import os

import matplotlib.pyplot as plt
import matplotlib.colors as mplcolors
import xarray as xr
from datetime import datetime, timedelta
from pytz import timezone
import warnings
import webp

from wetterdienst.provider.dwd.radar import (
    DwdRadarDate,
    DwdRadarParameter,
    DwdRadarValues,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def plot(ds: xr.Dataset, product_type: str):
    import wradlib as wrl

    # set up projections
    proj_radolan = wrl.georef.create_osr("dwd-radolan-sphere")
    proj_mercator = wrl.georef.epsg_to_osr(3857)
    proj_wgs84 = wrl.georef.epsg_to_osr(4326)

    proj_src = proj_radolan
    #proj_target = proj_wgs84
    proj_target = proj_mercator

    # start a new figure
    fig = plt.figure(figsize=(15, 16))
    ax = fig.add_subplot(111, aspect="equal")

    # plot Germany
    filename = "countries/ne_10m_admin_0_countries_lakes.shp"
    dataset, inLayer = wrl.io.open_vector(filename)
    fattr = "name = 'Germany'"
    inLayer.SetAttributeFilter(fattr)
    
    patches, keys = wrl.georef.get_vector_coordinates(inLayer, trg_crs=proj_target, key="name")
    wrl.vis.add_patches(ax, patches, facecolor=mplcolors.to_rgba("gray", 0.25))

    # plot rain fall
    colors = [
        (0.0,  mplcolors.to_rgba("deepskyblue", 0.0)),
        (0.05,  mplcolors.to_rgba("deepskyblue", 1.0)),
        (0.2, mplcolors.to_rgba("dodgerblue", 1.0)),
        (1.0, mplcolors.to_rgba("mediumpurple", 1.0)),
    ]
    cmap = mplcolors.LinearSegmentedColormap.from_list("rainfall", colors)
    cmap.set_over("red", 1.0)
    norm = mplcolors.PowerNorm(gamma=1.0, vmin=0.0, vmax=50.0)
    

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        da_projected = wrl.georef.reproject(ds[product_type], coords=dict(x="x", y="y"), src_crs=proj_radolan, trg_crs=proj_target)
    da_projected.plot(ax=ax, cmap=cmap, norm=norm)

    # set title and limits
    ts_str = datetime.fromtimestamp(ds.time.min().values.item() / 10**9) \
        .astimezone(timezone("Europe/Berlin")) \
        .strftime("%d.%m.%Y %H:%M")
    plt.title(f"{product_type} RADOLAN \n{ts_str}")
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    plt.tight_layout(pad=5.0)

    # set boundaries around Germany
    [[x1, x2], [y1, y2]] = wrl.georef.reproject([4.0, 16.0], [46.0, 56.0], src_crs=proj_wgs84, trg_crs=proj_target)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)


def radolan_ry_example():
    """Retrieve RADOLAN ry reflectivity data by DWD."""
    log.info("Acquiring RADOLAN RY composite data")
    now = datetime.now()
    #start = now - timedelta(minutes=30)
    start = now - timedelta(hours=3)
    end = now
    radolan = DwdRadarValues(
        parameter=DwdRadarParameter.RY_REFLECTIVITY,
        start_date=start,
        end_date=end
    )

    imgs = []

    for item in radolan.query():
        # Decode data using wradlib.
        log.info("Parsing RADOLAN RY composite data for %s", item.timestamp)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ds = xr.open_dataset(item.data, engine="radolan")

        product_type = list(ds.data_vars.keys())[0]

        # Plot and display data.
        plot(ds, product_type)

        ts = datetime.timestamp(item.timestamp)
        
        plt.gcf().canvas.draw()
        imgs.append(plt.gcf().canvas.renderer.buffer_rgba())
        plt.close()

    webp.mimwrite(file_path="radar.webp", arrs=imgs, fps=8.0)

def main():
    """Run example."""
    radolan_ry_example()


if __name__ == "__main__":
    main()
