from __future__ import annotations
import matplotlib.pyplot as plt
import contextily as cx
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from typing import TYPE_CHECKING
from core.layer import Layer as BaseLayer

if TYPE_CHECKING:
    from core.process import Process
    from core.base_object import BaseObject
    from core.event_bus import EventBus
    from utils import FrameBuffer


class MapRenderLayer(BaseLayer):
    """
    Renders the map based on events and puts the resulting frame into a shared buffer.
    """
    def __init__(self, event_bus: EventBus, cities: dict, capital_city_name: str,
                 shared_frame_buffer: FrameBuffer, fig_size=(10, 8), dpi=100, initial_zoom=5):
        self.event_bus = event_bus
        self.cities = cities
        self.capital_city_name = capital_city_name
        self.frame_buffer = shared_frame_buffer
        
        self.fig, self.ax = plt.subplots(figsize=fig_size, dpi=dpi)
        self.fig.tight_layout()
        
        self.camera_lat, self.camera_lon = cities[capital_city_name]["lat"], cities[capital_city_name]["lng"]
        self.zoom = initial_zoom
        
        self.cities_gdf = None
        self.ax.set_axis_off()

    def on_attach(self, process: Process) -> None:
        self.event_bus.subscribe("camera_view_updated", self._on_camera_view_update)
        
        # Prepare GeoDataFrame from the settlements data
        points = [Point(data["lng"], data["lat"]) for name, data in self.cities.items() if data["lat"] is not None]
        names = [name for name, data in self.cities.items() if data["lat"] is not None]
        self.cities_gdf = gpd.GeoDataFrame(
            {'city': names},
            geometry=points,
            crs="EPSG:4326"
        ).to_crs(epsg=3857)
        
        # Perform an initial render
        self.set_camera_view(self.camera_lat, self.camera_lon, self.zoom)

    def _on_camera_view_update(self, lat: float, lon: float, zoom: int):
        self.set_camera_view(lat, lon, zoom)

    def set_camera_view(self, lat: float, lon: float, zoom: int):
        """Sets the camera view, re-renders the map, and updates the frame buffer."""
        self.camera_lat = lat
        self.camera_lon = lon
        self.zoom = int(round(zoom))

        point_gdf = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857)
        center_x, center_y = point_gdf.geometry.x.iloc[0], point_gdf.geometry.y.iloc[0]

        # Scale factor for zoom, adjusted for smaller region
        if self.zoom <= 8: scale_factor = 100000 / (2**(self.zoom-8))
        else: scale_factor = 10000 / (2**(self.zoom-11))


        minx, maxx = center_x - scale_factor, center_x + scale_factor
        miny, maxy = center_y - scale_factor, center_y + scale_factor * 0.7
        
        self.ax.clear()
        self.ax.set_aspect('equal')
        self.ax.set_axis_off()

        try:
            cx.add_basemap(self.ax, crs="EPSG:3857", source=cx.providers.OpenStreetMap.Mapnik, zoom=self.zoom)
            self.ax.set_xlim(minx, maxx)
            self.ax.set_ylim(miny, maxy)
        except Exception as e:
            pass

        if self.cities_gdf is not None:
            self.cities_gdf.plot(ax=self.ax, marker='o', color='red', markersize=20, zorder=5)

        self.fig.canvas.draw()
        frame_rgba = np.array(self.fig.canvas.buffer_rgba())
        self.frame_buffer.set_frame(frame_rgba)

    def on_detach(self, process: Process) -> None:
        plt.close(self.fig)
        self.event_bus.unsubscribe("camera_view_updated", self._on_camera_view_update)
