//Not yet asynchronous, run in stages
// 1
fetch('https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js')
    .then(response => response.text())
    .then(text => eval(text))


fetch('https://npmcdn.com/@turf/turf/turf.min.js')
    .then(response => response.text())
    .then(text => eval(text))

// 2
function loadData(filename, branch) {
  return $.ajax({
    url:"https://raw.githubusercontent.com/mahkah/dc_stop_and_frisk/" + branch + "/" + filename,
    dataType: "json",
    success: console.log(filename + " successfully loaded."),
    error: function (xhr) {
      alert(xhr.statusText)
    }
  });
}

var psaGEOJSON = loadData("original_data/Police_Service_Areas.geojson", 'master');
var censusTractGEOJSON = loadData("original_data/Census_Tracts_in_2010.geojson", 'master');
var neighborhoodGEOJSON = loadData("original_data/Neighborhood_Clusters.geojson", 'master');
var policeSectorGEOJSON = loadData("original_data/Police_Sectors.geojson", 'master');
var wardGEOJSON = loadData("original_data/Ward_from_2012.geojson", 'master');
var sffcGEOJSON = loadData("transformed_data/SF_Field_Contact_locations.geojson", 'mahkah-update-2017-data');

// 3
/** Appends an array of attributes on all the incidents that occured in each polygon. */
function collectProperties(polygonGEOJSON, incidentGEOJSON, filterArray) {
  var collectedGEOJSON = turf.collect(polygonGEOJSON, incidentGEOJSON, filterArray[0], filterArray[0]);
  for (var i = 1; i < filterArray.length; i++) {
    collectedGEOJSON = turf.collect(collectedGEOJSON, incidentGEOJSON, filterArray[i], filterArray[i]);
  }
  return collectedGEOJSON;
}

var filterAttributes = ['race', 'gen', 'age', 'date', 'force'];

var psaProp = collectProperties(psaGEOJSON.responseJSON, sffcGEOJSON.responseJSON, filterAttributes);
var censusTractProp = collectProperties(censusTractGEOJSON.responseJSON, sffcGEOJSON.responseJSON, filterAttributes);
var neighborhoodProp = collectProperties(neighborhoodGEOJSON.responseJSON, sffcGEOJSON.responseJSON, filterAttributes);
var policeSectorProp = collectProperties(policeSectorGEOJSON.responseJSON, sffcGEOJSON.responseJSON, filterAttributes);
var wardProp = collectProperties(wardGEOJSON.responseJSON, sffcGEOJSON.responseJSON, filterAttributes);


Object.keys(psaProp.features).forEach(function(key, i) {
  psaProp.features[i].properties.polygonName = "Police Service Area " + psaProp.features[i].properties.name;
});
Object.keys(censusTractProp.features).forEach(function(key, i) {
  censusTractProp.features[i].properties.polygonName = "Census Tract " + censusTractProp.features[i].properties.TRACT;
});
Object.keys(neighborhoodProp.features).forEach(function(key, i) {
  neighborhoodProp.features[i].properties.polygonName = neighborhoodProp.features[i].properties.NBH_NAMES;
});
Object.keys(policeSectorProp.features).forEach(function(key, i) {
  policeSectorProp.features[i].properties.polygonName = "Police Sector " + policeSectorProp.features[i].properties.name;
});
Object.keys(wardProp.features).forEach(function(key, i) {
  wardProp.features[i].properties.polygonName = wardProp.features[i].properties.name;
});
console.log("Done collecting features");


// 4
(function(console){

    console.save = function(data, filename){

        if(!data) {
            console.error('Console.save: No data')
            return;
        }

        if(!filename) filename = 'console.json'

        if(typeof data === "object"){
            data = JSON.stringify(data, undefined)
        }

        var blob = new Blob([data], {type: 'text/json'}),
            e    = document.createEvent('MouseEvents'),
            a    = document.createElement('a')

        a.download = filename
        a.href = window.URL.createObjectURL(blob)
        a.dataset.downloadurl =  ['text/json', a.download, a.href].join(':')
        e.initMouseEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null)
        a.dispatchEvent(e)
    }
})(console)

console.save(psaProp, "Police_Service_Areas_collected.geojson")
console.save(censusTractProp, "Census_Tracts_in_2010_collected.geojson")
console.save(neighborhoodProp, "Neighborhood_Clusters_collected.geojson")
console.save(policeSectorProp, "Police_Sectors_collected.geojson")
console.save(wardProp, "Ward_from_2012_collected.geojson")
