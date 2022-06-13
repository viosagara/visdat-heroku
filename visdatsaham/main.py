import numpy as np
import datetime as dt

from bokeh.plotting import figure, curdoc
from bokeh.models import HoverTool, CustomJSHover,TickFormatter
from bokeh.tile_providers import get_provider, Vendors
from bokeh.models.widgets import DataTable, TableColumn, HTMLTemplateFormatter, DateFormatter, Slider,DateSlider, DateRangeSlider, RangeSlider
from bokeh.models.callbacks import CustomJS
from bokeh.models.tickers import FixedTicker

from data import DataProvider
import config as cfg

TOOLTIP = """
<div class="plot-tooltip">
    <div>
        <span style="font-weight: bold;">Accident_Severity: </span>@Verbal_severity
    </div>
    <div>
        <span style="font-weight: bold;">Time: </span>@datetime{%Y-%m-%d %H:%M:%S}
    </div>
    <div>
        <span style="font-weight: bold;">Number_of_Vehicles: </span>@Number_of_Vehicles
    </div>    
    <div>
        <span style="font-weight: bold;">Number_of_Casualties: </span>@Number_of_Casualties
    </div>
    <div>
        <span style="font-weight: bold;">Nearest Hospital: </span>@closest_hospital_name
    </div>
    <div>
        <span style="font-weight: bold;">Distance to @closest_hospital_name: </span>@closest_hospital_distance km
    </div>   
</div>
"""

COL_TPL = """
<%= get_icon(type.toLowerCase()) %> <%= type %>
"""

data_provider = DataProvider()

data_scr = data_provider.data_ds
[start_date_str, end_date_str] = data_provider.get_boundary_dates()

max_casualties = data_provider.get_max_casualties()

fa_formatter =  HTMLTemplateFormatter(template=COL_TPL)
columns = [TableColumn(field="datetime", default_sort="descending", title="Time",
                       formatter=DateFormatter(format="%Y-%m-%d %H:%M:%S")),
           TableColumn(field="Verbal_severity", title="Accident_Severity", width=150),
           TableColumn(field="Number_of_Casualties", title="Number_of_Casualties", width=150),
           TableColumn(field="Number_of_Vehicles", title="Number_of_Vehicles", width=150)]

full_table = DataTable(columns=columns,
                       source=data_scr,
                       view=data_provider.data_view,
                       name="table",
                       index_position=None)

full_table_force_change = CustomJS(args=dict(source=data_scr), code="""
    source.change.emit()
""")
data_scr.js_on_change('data', full_table_force_change)


main_map = figure(x_axis_type="mercator", y_axis_type="mercator",
                     x_axis_location=None, y_axis_location=None,
                     tools=['wheel_zoom', "pan", "reset", "tap", "save"],
                     match_aspect=True,
                     name="main_plot")
main_map.add_tile(get_provider(Vendors.CARTODBPOSITRON))
accidents_points = main_map.circle(x="x", y="y", 
                    radius='Casualties3',
                    radius_units='screen',
                    color='color',
                    alpha=0.5,
                    source=data_scr, view=data_provider.data_view, legend_label="Accidents", muted_alpha=0)

hospital_points = main_map.asterisk(x="x", y="y", size=5, color="firebrick",
                    alpha=0.5,
                    legend_label="Hospitals",
                    muted_alpha=0,
                    source=data_provider.data_ds_hospitals, view=data_provider.data_view_hospitals)

hover = HoverTool(tooltips=TOOLTIP, formatters={'datetime': 'datetime'})
main_map.add_tools(hover)
main_map.legend.location = "top_left"
main_map.legend.click_policy="mute"


stats_plot = figure(x_range=data_provider.dispatch_types, plot_height=400, plot_width=400,
                    tools=["save"],
                    name="stats_plot")
stats_plot.vbar(x="Accident_Severity", top="counts", width=0.9, source=data_provider.type_stats_ds,color= "color")
#stats_plot.xaxis[0].ticker=FixedTicker(
 #       ticks=[data_provider.Severitymap[sevirty] for sevirty in data_provider.type_stats_ds['Accident_Severity']])

stats_plot.xaxis.major_label_orientation = np.pi/2


date_slider =  DateRangeSlider(start=start_date_str, end=end_date_str,
                value=(dt.datetime.strptime(start_date_str, '%d/%m/%Y').date(),dt.datetime.strptime(start_date_str, '%d/%m/%Y').date()), 
                step=1,name="date_slider", title="Days", callback_policy='mouseup')

casualties_slider = RangeSlider(start=0, end=max_casualties,
                value=(0,max_casualties), 
                step=1,name="casualties_slider", title="Casualties", callback_policy='mouseup')




def update_stats():
    stats_plot.x_range.factors = data_provider.dispatch_types


def update():
    """Periodic callback."""
    data_provider.fetch_data()
    update_stats()


def update_date(attr, old, new):
    if new != old:
        data_provider.set_date(new)
        update_stats()

def update_casualties(attr, old, new):
    if new != old:
        data_provider.set_casualties(new)
        update_stats()

date_slider.on_change("value_throttled", update_date)
casualties_slider.on_change("value_throttled", update_casualties)
curdoc().add_root(main_map)
curdoc().add_root(full_table)
curdoc().add_root(stats_plot)
curdoc().add_root(date_slider)
curdoc().add_root(casualties_slider)
#curdoc().add_periodic_callback(update, cfg.UPDATE_INTERVAL)