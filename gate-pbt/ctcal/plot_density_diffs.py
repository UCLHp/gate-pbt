# -*- coding: utf-8 -*-
"""
Created on Thu Nov 21 12:28:32 2019
@author: SCOURT01

Bokeh plot showing the % change in density of each WW tissue
performed during the HU-RSP calibration procedure.
"""

import pandas as pd
from bokeh.plotting import figure, output_file, show, ColumnDataSource
from bokeh.models import HoverTool


output_file("DensityDifferences.html")

df = pd.read_csv("calibrated_densities.csv")

print("Mean diff = {}%".format( round(df["Density diff (%)"].mean(),2) ) )
print("Median diff = {}%".format( round(df["Density diff (%)"].median(),2) ) )
print("Min = {}%".format( round(df["Density diff (%)"].min(),2) ) )
print("Max diff = {}%".format( round(df["Density diff (%)"].max(),2) ) )

source = ColumnDataSource(data=dict(
        #x=list(df["HU"]),
        x=range(len(df["Density diff (%)"])),
        y=list(df["Density diff (%)"]),
        desc=list(df["Tissue"])
))


hover = HoverTool(tooltips=[
        ("Tissue","@desc"),
        ("% change","@y"),
])


p = figure( plot_width=600, plot_height=300, 
           tools=[hover, "pan,wheel_zoom,box_zoom,reset"] ,
           y_axis_label="Change (%)",
)
p.circle( 'x', 'y', size=5, source=source )
p.line( [0,70], [0,0] )
#p.line( [-800,1600], [0,0] )

show(p)
