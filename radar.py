import logging
import os

import matplotlib.pyplot as plt
import matplotlib.colors as mplcolors
from mpl_toolkits.axes_grid1 import make_axes_locatable
import xarray as xr
from datetime import datetime, timedelta
from pytz import timezone
import warnings
import webp
import glob
from ffmpeg import FFmpeg

from wetterdienst.provider.dwd.radar import (
    DwdRadarDate,
    DwdRadarParameter,
    DwdRadarValues,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

def bounds_around(lat: float, lon: float, zoom: float, ratio: float):
    ratio = ratio * 1.5 # leave room for figure padding
    width = 360.0 / pow(2, zoom)
    width2 = width / 2.0
    lon1 = lon - width2
    lon2 = lon + width2
    height2 = width2 / ratio
    lat1 = lat - height2
    lat2 = lat + height2    
    
    return [[lat1, lat2], [lon1, lon2]]

def plot(ds: xr.Dataset, product_type: str, timestamp: datetime):
    import wradlib as wrl

    # start a new figure
    scale = 2.0 # scale 2x for hidpi displays
    fig_w = 4.0
    fig_h = 5.4
    dpi = 100.0 * scale
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    ax = fig.add_subplot(111, aspect="equal")

    dot = []

    #[bounds_lat, bounds_lon] = bounds_around(51.1638175, 10.4478313, 5.2, fig_w / fig_h) # Germany
    [bounds_lat, bounds_lon] = bounds_around(54.1853998, 9.8220089, 7.0, fig_w / fig_h) # Schleswig-Holstein

    marker = None
    marker = [54.1853998, 9.8220089]
    
    # set up projections
    proj_radolan = wrl.georef.create_osr("dwd-radolan-sphere")
    proj_mercator = wrl.georef.epsg_to_osr(3857)
    proj_wgs84 = wrl.georef.epsg_to_osr(4326)

    proj_src = proj_radolan
    proj_target = proj_mercator
    
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
        (0.05, mplcolors.to_rgba("deepskyblue", 1.0)),
        (0.1,  mplcolors.to_rgba("dodgerblue", 1.0)),
        (0.2,  mplcolors.to_rgba("mediumpurple", 1.0)),
        (0.4,  mplcolors.to_rgba("darkviolet", 1.0)),
        (0.65, mplcolors.to_rgba("coral", 1.0)),
        (1.0,  mplcolors.to_rgba("red", 1.0)),
    ]
    cmap = mplcolors.LinearSegmentedColormap.from_list("rainfall", colors)
    cmap.set_over(mplcolors.to_rgba("orangered", 1.0))
    norm = mplcolors.PowerNorm(gamma=1.0, vmin=0.0, vmax=50.0, clip=True)
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        da_projected = wrl.georef.reproject(ds[product_type], coords=dict(x="x", y="y"), src_crs=proj_radolan, trg_crs=proj_target)
    pc = da_projected.plot(ax=ax, cmap=cmap, norm=norm, add_colorbar=False)
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    cb = fig.colorbar(pc, extend='max', cax=cax)
    cb.set_label("mm in 60 Minuten")

    # set title and limits
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    color_back = mplcolors.to_rgba("white", 1.0)
    fig.set_facecolor(color_back)
    ax.patch.set_facecolor(color_back)
    ax.set_facecolor(color_back)
    plt.tight_layout(pad=0.5)
    ts_str = timestamp.strftime("%d.%m.%Y %H:%M")
    ax.set_title(ts_str)
    border_color = mplcolors.to_rgba("gray", 1.0)
    ax.tick_params(color=border_color, labelcolor=border_color)
    for spine in ax.spines.values():
        spine.set_edgecolor(border_color)

    # add marker
    if marker is not None:    
        [[mx], [my]] = wrl.georef.reproject([marker[1]], [marker[0]], src_crs=proj_wgs84, trg_crs=proj_target)
        ax.plot(mx, my, color=mplcolors.to_rgba("coral", 1.0), marker='o', markeredgecolor="black", markeredgewidth=1.0)

    # set boundaries
    [[x1, x2], [y1, y2]] = wrl.georef.reproject(bounds_lon, bounds_lat, src_crs=proj_wgs84, trg_crs=proj_target)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)

    # add source
    plt.figtext(0.99, 0.01, "Quelle: Deutscher Wetterdienst", horizontalalignment='right')


def radolan_ry_example():
    """Retrieve RADOLAN rv reflectivity data by DWD."""
    log.info("Acquiring RADOLAN RV composite data")
    now = datetime.now()
    #start = now - timedelta(minutes=30)
    start = now - timedelta(hours=4)
    end = now
    radolan = DwdRadarValues(
        parameter=DwdRadarParameter.RV_REFLECTIVITY,
        start_date=start,
        end_date=end
    )

    cache = False
    file_prefix = "radar"
    file_quality = 50
    lossless = False

    imgs_path = []

    for item in radolan.query():
        timestamp = item.timestamp.astimezone(timezone("Europe/Berlin"))
        timestr = timestamp.strftime("%Y%m%d_%H%M")
        file_path = "{}_{}.webp".format(file_prefix, timestr)

        if not os.path.exists(file_path) or cache is False:
            # Decode data using wradlib.
            log.info("Parsing RADOLAN RV composite data for %s", item.timestamp)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ds = xr.open_dataset(item.data, engine="radolan")

            #ds = ds.drop_isel(prediction_time = 0)
            product_type = list(ds.data_vars.keys())[0]

            print(ds[product_type])

            # plotting the actual data
            plot(ds, product_type, timestamp)

            # write webp image
            plt.gcf().canvas.draw()            
            log.info("Writing webp file %s", file_path)
            img = plt.gcf().canvas.renderer.buffer_rgba()
            webp.imwrite(arr=img, file_path=file_path, quality=file_quality, lossless=lossless)
        else:            
            log.info("Skipping RADOLAN RV composite data for %s", item.timestamp)

        imgs_path.append(file_path)
        plt.close()
    
    # remove old files
    for f in glob.glob("{}_*.webp".format(file_prefix)):
        if not f in imgs_path:
            log.info("Removing old webp image %s", f)
            os.remove(f)

    # run ffmpeg
    file_vid = file_prefix + ".webm"
    log.info("Rendering new video file %s", file_vid)
    ffmpeg = (
        FFmpeg()
        .option("y")
        .option("pattern_type", "glob")
        .option("framerate", "8")
        .input(file_prefix + "_*.webp")
        .output(
            file_vid, {
                "c:v": "libvpx-vp9",
                "b:v": "250K"
            },
        )
    )
    ffmpeg.execute()


def main():
    """Run example."""
    radolan_ry_example()


if __name__ == "__main__":
    main()
