import os
import pandas as pd

try:
    import plotly.express as px
except ModuleNotFoundError:
    print("plotly is not installed; skipping geo_plot.py example.")
    raise SystemExit(0)

geofile = "~/Downloads/Sustainability_and_Transformation_Partnerships__April_2019__EN_BUC-shp/Sustainability_and_Transformation_Partnerships__April_2019__EN_BUC.shp"

if not os.path.exists("temp.csv"):
    print("temp.csv not found; skipping geo_plot.py example.")
    raise SystemExit(0)

data = pd.read_csv( "temp.csv", sep = ",")

t = data[ data["stp"] == "E54000007"] 
fig = px.scatter(data_frame = t, x="time", y="total_infected")
fig.write_image("fig1.png")

print(t)
