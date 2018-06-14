# Door-to-door Routing Analyst - DORA

DORA is a data analysis tool for measuring accessibility, able to read any road network setup in a database with pgRouting (v2.3.2) extension. It is based in the door-to-door approach to retrieve more realistic travel times either for private car or bicycle transport modes.   

## Installation

```
    $ git clone git@github.com:DigitalGeographyLab/DORA.git
    $ cd DORA
```

Add the system path where the project is located in the module [__main__.py].

````python
sys.path.append('/dgl/codes/DORA/')
````

### Libraries required

* OWSLib
```
    $ cd /opt/anaconda3/bin/
    $ ./conda install -c conda-forge owslib
    $ source ./activate
    $ pip install --upgrade owslib
```

  For windows, also required: Microsoft Visual C++ 9.0 is required. Get it from [here][microsoft-vistual-c++].
* nvector (not available in conda repositories)

```
    $ pip install nvector
```
* pyproj
```
    $ conda install -c conda-forge pyproj
```
* psycopg2
```
    $ conda install -c conda-forge psycopg2
```

* geopandas
```
    $ conda install -c conda-forge geopandas
```
* joblib
```
    $ conda install -c anaconda joblib
```
* psutil
```
    $ conda install -c anaconda psutil
```

## Run

startPointsFolder: Folder containing a set of geojson files with the origin/start Point geometries.
endPointsFolder: Folder containing a set of geojson files with the destination/target Point geometries.
 
```{r, engine='sh', count_lines}
    user@/dgl/codes/DORA$$ python -m src.main -s <../startPointsFolder> -e src\test\data\geojson\Subsets\subset1\subset1_1 -o digiroad\test\data\outputFolder -t BICYCLE -c BICYCLE_FAST_TIME --summary --is_entry_list
```

```-s```: Path to the Geojson file containing the set of __origin__ points (or the directory containing a set of Geojsons).

```-e```: Path to the Geojson file containing the set of __target__ points (or the directory containing a set of Geojsons).

```-o```: Path where store the output data.

```-t```: Flag to choose the transport mode for the data analysis [PRIVATE_CAR, BICYCLE].

```-c```: The impedance/cost attribute to calculate the shortest path.

```--route```: Store in the output folder the geojson files with the fastest route LineString features.

```--summary```: Store in the output folder the csv files containing the fastest travel time summary per each pair of entry points.

```--is_entry_list```: Define if the ```-s``` and ```-e``` are folders paths and not file paths.


Impedance/Cost ```-c``` attribute accepted values:
* DISTANCE
* SPEED_LIMIT_TIME
* DAY_AVG_DELAY_TIME (PRIVATE_CAR only)
* MIDDAY_DELAY_TIME (PRIVATE_CAR only)
* RUSH_HOUR_DELAY (PRIVATE_CAR only)
* BICYCLE_FAST_TIME (BICYCLE only)
* BICYCLE_SLOW_TIME (BICYCLE only)

Input testPoints.geojson is in the format:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "MultiPoint",
        "coordinates": [
          [8443150.541380882, 2770625.5047027366],
          [8436436.62334174, 2776131.3593964037]
        ]
      },
      "properties": {
        "title": "Pair 1",
        "icon": "monument"
      }
    },
    .
    .
    .
    {
      "type": "Feature",
      "geometry": {
        "type": "MultiPoint",
        "coordinates": [
          [8452765.483509162, 2783396.1614870545],
          [8445529.046721973, 2778867.5661432995]
        ]
      },
      "properties": {
        "title": "Pair 2",
        "icon": "monument"
      }
    }
  ]
}
```

## Additonal Layers 

You are allowed to add new attributes coming from a polygon layer and attach them to the selected points (start and end point to calculate the shortpath).

See: [Additional Layers Operations][additional-layers]

## Modifying or extending transport modes

The tool uses a hierarchical structure to support different travel modes. By default, the supported travel modes are Private Car and Bicycle. To extend the functionality it is needed either to modify the existing transport modes specificiations or adding a new specification of the abstraction [AbstractTransportMode] and call it from [doraInit.py].



[microsoft-vistual-c++]: https://www.microsoft.com/en-us/download/details.aspx?id=44266
[additional-layers]: src/main/additionalOperations/ADDITIONAL_LAYERS.md
[__main__.py]: src/main/__main__.py
[AbstractTransportMode]: src/main/transportMode/AbstractTransportMode.py
[doraInit.py]: src/main/doraInit.py