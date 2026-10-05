"""Run from QGIS Python with this project open. Does not change canvas visibility."""
from pathlib import Path
from qgis.core import (QgsProject, QgsMapSettings, QgsMapRendererParallelJob,
                       QgsCoordinateReferenceSystem, QgsRectangle)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
target = root / 'docs'
target.mkdir(exist_ok=True)
project = QgsProject.instance()
layer = project.mapLayersByName('NDVI medio sin caminos - escala 0.30 a 0.95')[0]
settings = QgsMapSettings()
settings.setLayers([layer])
settings.setDestinationCrs(layer.crs())
extent = QgsRectangle(layer.extent()); extent.scale(1.08)
settings.setExtent(extent)
settings.setOutputSize(QSize(1200, 800))
settings.setBackgroundColor(QColor('white'))
job = QgsMapRendererParallelJob(settings)
job.start(); job.waitForFinished()
map_path = target / '_ndvi_map.png'
job.renderedImage().save(str(map_path))
try:
    font = ImageFont.truetype('arial.ttf', 22)
    small = ImageFont.truetype('arial.ttf', 17)
except OSError:
    font = small = ImageFont.load_default()
canvas = Image.new('RGB', (1500, 930), 'white')
draw = ImageDraw.Draw(canvas)
draw.text((30, 22), 'NDVI medio sin caminos · escala 0,30–0,95', fill='#182c38', font=font)
canvas.paste(Image.open(map_path).convert('RGB'), (0, 70))
draw.text((1210, 110), 'Media por celda', fill='black', font=small)
stops = [(215,25,28),(253,174,97),(255,255,192),(166,217,106),(26,150,65)]
for dy in range(301):
    t = dy/300*4
    index = min(int(t),3); fraction = t-index
    color = tuple(round(stops[index][c]*(1-fraction)+stops[index+1][c]*fraction) for c in range(3))
    draw.line((1210,155+dy,1240,155+dy),fill=color)
for i,value in enumerate([.30,.4625,.625,.7875,.95]):
    draw.text((1250,145+i*75),f'{value:.4f}',fill='black',font=small)
draw.text((1210,495),'Color continuo',fill='black',font=small)
draw.text((1210,522),'Extremos saturados',fill='black',font=small)
draw.text((30, 880), 'NDVI calculado de bandas multiespectrales; media excluyendo caminos. No representa dosis ni diagnóstico nutricional.', fill='#384c58', font=small)
canvas.save(target / 'ndvi_mean.png')
source = root.parent / 'revision_multiespectral/validacion_flores/sector_05.png'
rgb = Image.open(source).convert('RGB').resize((840, 840), Image.Resampling.NEAREST)
panel = Image.new('RGB', (900, 960), 'white'); panel.paste(rgb, (30, 70)); d = ImageDraw.Draw(panel)
d.text((30, 22), 'RGB · sector S05 · flores visibles', fill='#182c38', font=font)
d.text((30, 927), 'Recorte de ortomosaico. Ampliación sin añadir detalle.', fill='#384c58', font=small)
panel.save(target / 'rgb_flowers.png')
print('Figures exported:', target)
