"""Colour-based sunflower candidates in an RGB orthomosaic. Requires GDAL."""
import argparse
import json
from pathlib import Path

import numpy as np
from matplotlib.colors import rgb_to_hsv
from scipy import ndimage
from scipy.spatial import cKDTree
from osgeo import gdal, ogr, osr


def detect(rgb_path, boundary_path, output, block=1000, halo=40, separation=.20):
    gdal.UseExceptions()
    ds = gdal.Open(str(rgb_path))
    if ds.RasterCount < 3:
        raise ValueError('Expected RGB bands 1, 2, 3, with optional alpha band 4')
    if ds.GetRasterBand(1).DataType != gdal.GDT_Byte:
        raise ValueError('This detector expects 8-bit RGB')
    gt = ds.GetGeoTransform()
    if gt[2] or gt[4]:
        raise ValueError('Rotated grids are not supported')
    crs = osr.SpatialReference(wkt=ds.GetProjection())
    crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    if not crs.IsProjected() or abs(crs.GetLinearUnits()-1) > 1e-6:
        raise ValueError('Use a projected CRS in metres')
    bounds_ds = ogr.Open(str(boundary_path))
    if bounds_ds is None:
        raise ValueError('Cannot open boundary')
    boundary_layer = bounds_ds.GetLayer(0)
    source_crs = boundary_layer.GetSpatialRef().Clone()
    source_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(source_crs, crs)
    boundaries = []
    for f in boundary_layer:
        geom = f.GetGeometryRef().Clone()
        geom.Transform(transform)
        boundaries.append(geom)
    candidates = []
    for top in range(0, ds.RasterYSize, block):
        for left in range(0, ds.RasterXSize, block):
            x0, y0 = max(0, left-halo), max(0, top-halo)
            x1, y1 = min(ds.RasterXSize, left+block+halo), min(ds.RasterYSize, top+block+halo)
            raw = ds.ReadAsArray(x0, y0, x1-x0, y1-y0)
            rgb = raw[:3].transpose(1, 2, 0).astype(np.float32)/255
            hsv = rgb_to_hsv(rgb)
            mask = ((hsv[:,:,0] > .10) & (hsv[:,:,0] < .19) &
                    (hsv[:,:,1] > .48) & (hsv[:,:,2] > .52) &
                    (rgb[:,:,0] > 1.6*rgb[:,:,2]))
            if ds.RasterCount >= 4:
                mask &= raw[3] > 0
            labels, count = ndimage.label(ndimage.binary_closing(mask, iterations=1))
            sizes = np.bincount(labels.ravel())
            for label, sl in enumerate(ndimage.find_objects(labels), start=1):
                if sl is None or not 5 <= sizes[label] <= 250:
                    continue
                if max(s.stop-s.start for s in sl) > 35:
                    continue
                yy, xx = np.nonzero(labels[sl] == label)
                px = float(xx.mean()+sl[1].start+x0)
                py = float(yy.mean()+sl[0].start+y0)
                if not (left <= px < min(left+block, ds.RasterXSize) and top <= py < min(top+block, ds.RasterYSize)):
                    continue
                x, y = gt[0]+(px+.5)*gt[1], gt[3]+(py+.5)*gt[5]
                point = ogr.Geometry(ogr.wkbPoint)
                point.AddPoint_2D(x, y)
                if any(b.Contains(point) for b in boundaries):
                    candidates.append((x, y, int(sizes[label])))
        print(f'Processed rows {top}–{min(top+block, ds.RasterYSize)}', flush=True)
    coords = np.asarray([(x,y) for x,y,_ in candidates]).reshape(-1,2)
    suppressed, keep = set(), []
    if len(coords):
        tree = cKDTree(coords)
        for i in sorted(range(len(candidates)), key=lambda i: (-candidates[i][2], i)):
            if i in suppressed:
                continue
            keep.append(i)
            suppressed.update(tree.query_ball_point(coords[i], separation))
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = ogr.GetDriverByName('GPKG').CreateDataSource(str(output))
    for name, indices in [('candidates', range(len(candidates))), ('filtered', keep)]:
        layer = result.CreateLayer(name, crs, ogr.wkbPoint)
        layer.CreateField(ogr.FieldDefn('candidate_id', ogr.OFTInteger))
        layer.CreateField(ogr.FieldDefn('yellow_pixels', ogr.OFTInteger))
        for i in indices:
            x,y,size = candidates[i]
            f = ogr.Feature(layer.GetLayerDefn())
            f.SetField('candidate_id', i+1)
            f.SetField('yellow_pixels', size)
            geom = ogr.Geometry(ogr.wkbPoint); geom.AddPoint_2D(x,y)
            f.SetGeometry(geom)
            if layer.CreateFeature(f) != 0:
                raise RuntimeError('Failed to write candidate')
    result = None
    summary = dict(candidates=len(candidates), filtered=len(keep), separation_m=separation,
                   block=block, halo=halo, gdal_version=gdal.VersionInfo(),
                   method='HSV thresholds; connected components; greedy spatial suppression')
    output.with_suffix('.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rgb', required=True)
    parser.add_argument('--boundary', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(detect(args.rgb, args.boundary, args.output), indent=2))


if __name__ == '__main__':
    main()
