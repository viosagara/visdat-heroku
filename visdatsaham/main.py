# -*- coding: utf-8 -*-

##Interactive bokeh for cross location selection

## Updated with regression line on 29 Apr 18
import numpy as np
import pandas as pd
from bokeh.io import curdoc,show
from bokeh.layouts import row,column, widgetbox
from bokeh.models import ColumnDataSource,LabelSet,Div,Paragraph,PointDrawTool,PolyDrawTool,PolyEditTool,PolySelectTool,CustomJS
from bokeh.models.widgets import Slider, TextInput,Button,CheckboxGroup,CheckboxButtonGroup,RadioGroup,Select,DataTable, TableColumn
from bokeh.plotting import figure
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


import scipy.spatial as spatial

df = pd.read_csv('visdatsaham/data/crosses_updated.csv')
headers = ["cross_id", "x", "y","pass_end_x", "pass_end_y"]
crosses = pd.DataFrame(df, columns=headers)


dx=crosses.x
dy=crosses.y

rx=[]
ry=[]

source = ColumnDataSource({
    'x': [80], 'y': [9], 'color': ['dodgerblue']
})

ix = source.data['x']
iy = source.data['y']
points = np.array(crosses[['x','y']])

t1 = np.vstack((ix, iy)).T
t2=np.vstack((crosses.x,crosses.y)).T

point_tree = spatial.cKDTree(t2)

ax=(point_tree.query_ball_point(t1, 3)).tolist()

cx=crosses.pass_end_x[ax[0]]
cy=crosses.pass_end_y[ax[0]]
size=1

source2 = ColumnDataSource({
    'cx': [cx], 'cy': [cy]
})

source_reg = ColumnDataSource({
    'rx': [], 'ry': []
})

source2 = ColumnDataSource(data=dict(cx=cx,cy=cy))
source_reg = ColumnDataSource(data=dict(rx=rx,ry=ry))

# Set up plot

plot = figure(plot_height=500, plot_width=700,
              tools="save",
              x_range=[0,100], y_range=[0,100],toolbar_location="below")
plot.image_url(url=["visdatsaham/static/images/base.png"],x=0,y=0,w=100,h=100,anchor="bottom_left")


plot.hex('cx','cy',source=source2,size=15,fill_color='#95D7FF',line_color='#584189',line_width=2,alpha=1)

st=plot.scatter('x','y',source=source,size=15,fill_color='orangered',line_color='black',line_width=2)

plot.xgrid.grid_line_color = None
plot.ygrid.grid_line_color = None
plot.axis.visible=False

draw_tool = PointDrawTool(renderers=[st])
draw_tool.add=False
columns = [
    #TableColumn(field="x", title="x"),
   # TableColumn(field="y", title="y")
]

data_table = DataTable(
    source=source,
    #columns=columns,
    index_position=None,
    width=800,
    editable=False,
)


def linear_regression(cx,cy):
    """Calculate the linear regression and r2 score"""
    model = LinearRegression()
    model.fit(cx[:,np.newaxis],cy)
    #Get the x- and y-values for the best fit line
    x_plot = np.linspace(50,100)
    y_plot = model.predict(x_plot[:,np.newaxis])
    #Calculate the r2 score
    r2 = r2_score(cy,model.predict(cx[:,np.newaxis]))
    #Position for the r2 text annotation
    r2_x = [-cx + 0.1*cx]
    r2_y = [cx - 0.1*cx]
    text = ["R^2 = %02f" % r2]
    return x_plot,y_plot, r2, r2_x, r2_y, text

x_plot, y_plot, r2, r2_x, r2_y, text = linear_regression(cx,cy)
text_source = ColumnDataSource(dict(x=[52], y=[3], text=text)) #R2 value
line_source = ColumnDataSource(data=dict(x=x_plot, y=y_plot)) #Regression line

reg_line=plot.line('x', 'y', source = line_source, color = 'black',line_width=0,line_alpha=0,line_cap="round")
glyph = LabelSet(x="x", y="y", text="text", text_color="white",source=text_source)
plot.add_layout(glyph)

def on_change_data_source(attr, old, new):
    ix = source.data['x']
    iy = source.data['y']

    t1 = np.vstack((ix, iy)).T
    t2 = np.vstack((crosses.x, crosses.y)).T

    point_tree = spatial.cKDTree(t2)

    ax = (point_tree.query_ball_point(t1, 3)).tolist()
    cx = crosses.pass_end_x[ax[0]]
    cy = crosses.pass_end_y[ax[0]]
    x_plot, y_plot, r2, r2_x, r2_y, text = linear_regression(cx,cy)


    text_source.data = dict(x=[52], y=[3], text = text)

    line_source.data = dict(x=x_plot, y=y_plot)
    source2.data=dict(cx=cx,cy=cy)
    # plot.scatter('cx','cy',source=source2)

source.on_change('data', on_change_data_source)

checkbox=CheckboxButtonGroup(labels=["Show Regression Plot"],button_type = "danger")

checkbox.callback = CustomJS(args=dict(l0=reg_line,l1=glyph, checkbox=checkbox), code="""
l0.visible = 0 in checkbox.active;
l1.visible = 0 in checkbox.active;
l0.glyph.line_width = 3;
l0.glyph.line_alpha=1;
l1.text_color="black";
""")



plot.add_tools(draw_tool)
plot.toolbar.active_tap = draw_tool
div = Div(text="""<b><h>WHERE DO TEAMS CROSS?</b></h></br></br>Interactive tool to get cross end locations based on user input. The tool uses <a href="https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.htmlL">cKDTree</a> 
to calculate the nearest cross start locations and plots the corresponding end locations<br></br>
<br>Created by <b><a href="https://twitter.com/Samirak93">Samira Kumar</a></b> using bokeh</br>""",
width=550, height=110)

div_help = Div(text="""<b><h>INSTRUCTIONS</b></h></br></br>Click on the below icon, in the bottom of the viz, to enable the option to drag the red circle.<br></br>
<img src="https://bokeh.pydata.org/en/latest/_images/PointDraw.png" alt="Point Draw Tool">
<br></br> 
The crosses, which have started, from within 3 units of the red circle are collected and their corresponding end locations are plotted in blue 
<br><b><a href="https://samirak93.github.io/analytics/projects/proj-1.html">Blog Post</a></br>""",
width=400, height=100)




layout=(column(div,checkbox,row(plot,column(div_help)),data_table))
curdoc().add_root(layout)
curdoc().title = "Where do teams cross?"

