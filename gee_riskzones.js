/**
 * Risk Zones classification for Google Earth Engine
 * 
 * To use this script on GEE, first run riskzones.py to export a
 * FeatureCollection CSV file. Then import that file as an asset
 * into your GEE assets folder and load it as demonstrated below.
 */

// Risk classes file (exported from riskzones.py)
var fc_risks = ee.FeatureCollection('users/just1982/riskzones/porto');
var fc_edus  = ee.FeatureCollection('users/just1982/riskzones/porto_edus');

// Centralizes the map on FeatureCollection
Map.centerObject(fc_risks, 0);

// Add risk levels layers
Map.addLayer(fc_risks.filter(ee.Filter.eq('class', 1)).draw({color: 'green',  pointRadius: 1}), {opacity: 0.5}, 'Risk Level 1');
Map.addLayer(fc_risks.filter(ee.Filter.eq('class', 2)).draw({color: 'yellow', pointRadius: 1}), {opacity: 0.5}, 'Risk Level 2');
Map.addLayer(fc_risks.filter(ee.Filter.eq('class', 3)).draw({color: 'red',    pointRadius: 1}), {opacity: 0.5}, 'Risk Level 3');

// Add EDUs positioning layer
Map.addLayer(fc_edus, {opacity: 1.0}, 'EDUs');
