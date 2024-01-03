import logging
import os

import matplotlib.pyplot as plt
import matplotlib.colors as mplcolors
import xarray as xr
from datetime import datetime, timedelta
from pytz import timezone
import warnings
import webp
import glob

from wetterdienst.provider.dwd.radar import (
    DwdRadarDate,
    DwdRadarParameter,
    DwdRadarValues,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def plot(ds: xr.Dataset, product_type: str, timestamp: datetime):
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
    cb = fig.colorbar(pc, extend='max')
    cb.set_label("mm in 60 Minuten")

    # set title and limits
    ts_str = timestamp.strftime("%d.%m.%Y %H:%M")
    plt.title(f"{product_type} RADOLAN \n{ts_str}")
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    color_back = mplcolors.to_rgba("white", 1.0)
    fig.set_facecolor(color_back)
    ax.patch.set_facecolor(color_back)
    ax.set_facecolor(color_back)
    plt.tight_layout(pad=5.0)

    # set boundaries around Germany
    [[x1, x2], [y1, y2]] = wrl.georef.reproject([4.0, 16.0], [46.0, 56.0], src_crs=proj_wgs84, trg_crs=proj_target)
    ax.set_xlim(x1, x2)
    ax.set_ylim(y1, y2)

    # add source
    plt.figtext(0.99, 0.01, "Quelle: Deutscher Wetterdienst", horizontalalignment='right')


def radolan_ry_example():
    """Retrieve RADOLAN ry reflectivity data by DWD."""
    log.info("Acquiring RADOLAN RY composite data")
    now = datetime.now()
    #start = now - timedelta(minutes=30)
    start = now - timedelta(hours=12)
    end = now
    radolan = DwdRadarValues(
        parameter=DwdRadarParameter.RY_REFLECTIVITY,
        start_date=start,
        end_date=end
    )

    file_prefix = "radar"
    file_quality = 70
    imgs = []
    imgs_path = []

    for item in radolan.query():
        timestamp = item.timestamp.astimezone(timezone("Europe/Berlin"))
        timestr = timestamp.strftime("%Y%m%d_%H%M")
        file_path = "{}_{}.webp".format(file_prefix, timestr)

        if not os.path.exists(file_path):
            # Decode data using wradlib.
            log.info("Parsing RADOLAN RY composite data for %s", item.timestamp)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ds = xr.open_dataset(item.data, engine="radolan")

            product_type = list(ds.data_vars.keys())[0]

            # plotting the actual data
            plot(ds, product_type, item.timestamp)

            # write webp image
            plt.gcf().canvas.draw()            
            log.info("Writing webp file %s", file_path)
            img = plt.gcf().canvas.renderer.buffer_rgba()
            webp.imwrite(arr=img, file_path=file_path, quality=file_quality)
        else:            
            log.info("Skipping RADOLAN RY composite data for %s", item.timestamp)

        imgs.append(webp.load_image(file_path))
        imgs_path.append(file_path)
        plt.close()
    
    # write animation
    file_anim = "{}.webp".format(file_prefix)
    log.info("Writing webp animation to %s", file_anim)
    webp.save_images(imgs, file_anim, fps=8.0, quality=file_quality)

    # remove old files
    for f in glob.glob("{}_*.webp".format(file_prefix)):
        if not f in imgs_path:
            log.info("Removing old webp image %s", f)
            os.remove(f)

def main():
    """Run example."""
    radolan_ry_example()


if __name__ == "__main__":
    main()
