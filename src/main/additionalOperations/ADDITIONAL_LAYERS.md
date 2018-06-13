# Additional Layers

You can add the location of any geojson containing polygon features with specific data by updating the [configuration.properties][conf-prop] file. This data will be merged with the selected points attributes that intersect a polygon.

![alt text][layers-img]

```
[GEOJSON_LAYERS]
walking_distance=/any/geojson/helsinki-walking-distance-areas.geojson
parking_time=/any/geojson/helsinki-parking-time-areas.geojson
```

In the example above you can see two additional layers `walking_distance` and `parking_time`. Each of them containing specific areas (polygons) with specific values for the walking distance and the parking time respectively.

Additionally, you must setup the attributes names to be merged with the points attributes that fall within the polygons.

```
[GEOJSON_LAYERS_ATTRIBUTES]
walking_distance_attributes=walking_distance
parking_time_attributes=parking_time,datetime
```

Notice that the properties prefixes of each set of attributes starts always with the name of the layer. For instance, the attributes name of the layer `walking_distance` is called `walking_distance_attributes` and the values are separated by `,`.

Finally you can add new operations that will use the new attributes by creating new specifications from the abstract class `AbstractAdditionalLayerOperation` in the module `src.main.additionalOperations`.

You must override the function:

```python
def runOperation(self, featureJson, prefix=""):
    # add your own operation here
    return {
        prefix + "your_result_1": <any_result>,
        prefix + "your_result_2": <any_result>
    } 
```

Once the operation specification was defined, then must be added to the linked list of operation execution in the function `getLinkedAbstractAdditionalLayerOperation` that can be found in the class `Reflection` ([here][reflection]) from the module `src.main.reflection`.

Your results (string, int, float, boolean or collections of any of the previous attributes type) will add/overwrite the attributes in the original features properties so they will be available for future uses.

___

The parameter `walkingSpeed` define the walking speed that will be used to calculate the walking time, taking into account the euclidean and average walking distance from the selected point to the nearest routable vertex, by default is `70` m/m (meters/minute). 

[conf-prop]: ../../resources/configuration.properties
[layers-img]: ../../../img/additional-layers.png
[reflection]: ../../../src/main/reflection/__init__.py