import ee

ee.Initialize()
ee.Authenticate()

fc_risks           = ee.FeatureCollection('users/just1982/riskzones/porto_M3')
fc_edus_random     = ee.FeatureCollection('users/just1982/riskzones/porto_edus_random')
fc_edus_balanced   = ee.FeatureCollection('users/just1982/riskzones/porto_edus_balanced')
fc_edus_enhanced   = ee.FeatureCollection('users/just1982/riskzones/porto_edus_enhanced')
fc_edus_restricted = ee.FeatureCollection('users/just1982/riskzones/porto_edus_restricted')
fc_roads           = ee.FeatureCollection('users/just1982/riskzones/porto_roads')

porto = ee.Geometry.Polygon(
  [[[-8.69579653494699, 41.1870648684617],
    [-8.69579653494699, 41.13355998095961],
    [-8.550571010044646, 41.13355998095961],
    [-8.550571010044646, 41.1870648684617]]], None, False)
cloud_max  = 10
date_begin = '2020-01-01'
date_end   = '2022-12-31'
colecao = ee.ImageCollection("COPERNICUS/S2").filter(ee.Filter.lt('CLOUD_COVERAGE_ASSESSMENT', cloud_max)).filterDate(date_begin, date_end).filterBounds(porto).map(lambda image:
  image.clip(porto).select(['B2', 'B3', 'B4'])
)

img_median = colecao.reduce(ee.Reducer.median())
img_map = img_median.select(['B4_median', 'B3_median', 'B2_median']).rename(['vis-red', 'vis-green', 'vis-blue'])

img_class_1 = fc_risks.filter(ee.Filter.eq('class', 1)).draw({'color': '#00ff00',  'pointRadius': 1})
img_class_2 = fc_risks.filter(ee.Filter.eq('class', 2)).draw({'color': '#ffff00',  'pointRadius': 1})
img_class_3 = fc_risks.filter(ee.Filter.eq('class', 3)).draw({'color': '#ff0000',  'pointRadius': 1})
img_edus    = fc_edus_restricted.draw({'color': '#000000',  'pointRadius': 1})

img = ee.ImageCollection([
  img_map.visualize({'min': 0, 'max': 3000}),
  img_class_1.visualize({'opacity': 0.5}),
  img_class_2.visualize({'opacity': 0.5}),
  img_class_3.visualize({'opacity': 0.5})]).mosaic()

task = ee.batch.Export.image.toCloudStorage(img, 'teste_gee2', 'riskzones-maps', 'teste_gee2', 800, porto)
task.start()

print('Waiting...')

while True:
  status = task.status()
  if status['state'] != 'RUNNING':
    break

print('Done!')
