from joblib import Parallel, delayed
from src.main.connection.PostgisServiceProvider import executePostgisQueryReturningDataFrame
from src.main.util import getConfigurationProperties, FileActions, dgl_timer, parallel_job_print, Logger

from src.main.transportMode import AbstractTransportMode


class BicycleTransportMode(AbstractTransportMode):
    def __init__(self, geojsonServiceProvider, epsgCode="EPSG:3857"):
        self.epsgCode = epsgCode
        self.fileActions = FileActions()
        self.serviceProvider = geojsonServiceProvider
        config = getConfigurationProperties(section="DATABASE_CONFIG")
        self.tableName = config["table_name"]

    def getNearestVertexFromAPoint(self, coordinates):
        """
        From the Database retrieve the nearest vertex from a given point coordinates.

        :param coordinates: Point coordinates. e.g [889213124.3123, 231234.2341]
        :return: Geojson (Geometry type: Point) with the nearest point coordinates.
        """

        # print("Start getNearestVertexFromAPoint")

        epsgCode = coordinates.getEPSGCode().split(":")[1]

        sql = "SELECT " \
              "v.id," \
              "ST_SnapToGrid(v.the_geom, 0.00000001) AS geom, " \
              "string_agg(distinct(e.old_id || ''),',') AS name " \
              "FROM " \
              "table_name_vertices_pgr AS v," \
              "table_name AS e " \
              "WHERE " \
              "v.id = (SELECT " \
              "id" \
              "FROM table_name_vertices_pgr" \
              "AND ST_DWithin(ST_Transform(v.the_geom, 4326)," \
              "ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), %s), 4326)::geography," \
              "1000)" \
              "ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint(%s, %s), %s) LIMIT 1)" \
              "AND (e.source = v.id OR e.target = v.id)" \
              "GROUP BY v.id, v.the_geom".replace("table_name", self.tableName) % (
                  str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode,
                  str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode)

        geojson = self.serviceProvider.execute(sql)

        # print("End getNearestVertexFromAPoint")
        return geojson

    def getNearestRoutableVertexFromAPoint(self, coordinates, radius=500):
        """
        From the Database retrieve the nearest routing vertex from a given point coordinates.

        :param coordinates: Point coordinates. e.g [889213124.3123, 231234.2341]
        :return: Geojson (Geometry type: Point) with the nearest point coordinates.
        """

        # print("Start getNearestRoutableVertexFromAPoint")

        epsgCode = coordinates.getEPSGCode().split(":")[1]

        sql = self.getNearestRoutableVertexSQL(coordinates, epsgCode, radius)

        geojson = self.serviceProvider.execute(sql)
        maxTries = 5
        tries = 0
        while len(geojson["features"]) == 0 and tries < maxTries:
            tries += 1
            radius += 500
            sql = self.getNearestRoutableVertexSQL(coordinates, epsgCode, radius)
            geojson = self.serviceProvider.execute(sql)

        # if len(geojson["features"]) > 0:
        #     print("Nearest Vertex found within the radius %s " % radius)
        # else:
        #     print("Nearest Vertex NOT found within the radius %s " % radius)
        #
        # print("End getNearestRoutableVertexFromAPoint")
        return geojson

    def getNearestRoutableVertexSQL(self, coordinates, epsgCode, radius):
        # return "SELECT " \
        #        "v.id," \
        #        "ST_SnapToGrid(v.the_geom, 0.00000001) AS geom, " \
        #        "string_agg(distinct(e.old_id || ''),',') AS name " \
        #        "FROM " \
        #        "table_name_vertices_pgr AS v," \
        #        "table_name AS e " \
        #        "WHERE " \
        #        "(e.source = v.id OR e.target = v.id) " \
        #        "AND e.TOIMINNALL <> 10 " \
        #        "AND ST_DWithin(ST_Transform(v.the_geom, 4326)," \
        #        "ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), %s), 4326)::geography," \
        #        "%s)" \
        #        "GROUP BY v.id, v.the_geom " \
        #        "ORDER BY v.the_geom <-> ST_SetSRID(ST_MakePoint(%s, %s), %s)" \
        #        "LIMIT 1" % (str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode,
        #                     str(radius),
        #                     str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode)
        return "SELECT " \
               "v.id," \
               "ST_SnapToGrid(v.the_geom, 0.00000001) AS geom, " \
               "string_agg(distinct(e.id || ''),',') AS name " \
               "FROM " \
               "table_name_vertices_pgr AS v," \
               "table_name AS e " \
               "WHERE " \
               "(e.source = v.id OR e.target = v.id) " \
               "AND e.luokka <> 0  " \
               "AND ST_DWithin(ST_Transform(v.the_geom, 4326)," \
               "ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), %s), 4326)::geography," \
               "%s)" \
               "GROUP BY v.id, v.the_geom " \
               "ORDER BY v.the_geom <-> ST_SetSRID(ST_MakePoint(%s, %s), %s)" \
               "LIMIT 1".replace("table_name", self.tableName) % (
                   str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode,
                   str(radius),
                   str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode)

    def getShortestPath(self, startVertexId, endVertexId, cost):
        """
        From a pair of vertices (startVertexId, endVertexId) and based on the "cost" attribute,
        retrieve the shortest path by calling the WFS Service.

        :param startVertexId: Start vertex from the requested path.
        :param endVertexId: End vertex from the requested path.
        :param cost: Attribute to calculate the cost of the shortest path
        :return: Geojson (Geometry type: LineString) containing the segment features of the shortest path.
        """

        # print("Start getShortestPath")

        # sql = "SELECT " \
        #       "min(r.seq) AS seq, " \
        #       "e.old_id AS id," \
        #       "e.liikennevi::integer as direction," \
        #       "sum(e.pituus) AS distance," \
        #       "sum(e.digiroa_aa) AS speed_limit_time," \
        #       "sum(e.kokopva_aa) AS day_avg_delay_time," \
        #       "sum(e.keskpva_aa) AS midday_delay_time," \
        #       "sum(e.ruuhka_aa) AS rush_hour_delay_time," \
        #       "ST_SnapToGrid(ST_LineMerge(ST_Collect(e.the_geom)), 0.00000001) AS geom " \
        #       "FROM " \
        #       "pgr_dijkstra('SELECT " \
        #       "id::integer," \
        #       "source::integer," \
        #       "target::integer," \
        #       "(CASE  " \
        #       "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 4)  " \
        #       "THEN %s " \
        #       "ELSE -1 " \
        #       "END)::double precision AS cost," \
        #       "(CASE " \
        #       "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 3) THEN %s " \
        #       "ELSE -1 " \
        #       "END)::double precision AS reverse_cost " \
        #       "FROM table_name', %s, %s, true, true) AS r, " \
        #       "table_name AS e " \
        #       "WHERE " \
        #       "r.id2 = e.id " \
        #       "GROUP BY e.old_id, e.liikennevi" % (cost, cost, str(startVertexId), str(endVertexId))
        sql = "SELECT " \
              "min(r.seq) AS seq, " \
              "e.id AS id, " \
              "e.liikennevi::integer as direction," \
              "sum(e.pituus) AS distance," \
              "sum(e.fast_time) AS fast_time," \
              "sum(e.slow_time) AS slow_time," \
              "ST_SnapToGrid(e.the_geom, 0.00000001) AS geom " \
              "FROM " \
              "pgr_dijkstra('SELECT " \
              "id::integer," \
              "source::integer," \
              "target::integer," \
              "(CASE  " \
              "WHEN luokka <> 0 AND (liikennevi = 0 OR liikennevi = 2 OR liikennevi = 5 OR liikennevi = 4)  " \
              "THEN %s " \
              "ELSE -1 " \
              "END)::double precision AS cost, " \
              "(CASE " \
              "WHEN luokka <> 0 AND (liikennevi = 0 OR liikennevi = 2 OR liikennevi = 5 OR liikennevi = 3) " \
              "THEN %s " \
              "ELSE -1 " \
              "END)::double precision AS reverse_cost " \
              "FROM table_name', %s, %s, true, true) AS r, " \
              "table_name AS e " \
              "WHERE " \
              "r.id2 = e.id " \
              "GROUP BY e.id, e.liikennevi".replace("table_name", self.tableName) % (
                  cost, cost, str(startVertexId), str(endVertexId))

        geojson = self.serviceProvider.execute(sql)
        # print("End getShortestPath")
        return geojson

    def getTotalShortestPathCostOneToOne(self, startVertexID, endVertexID, costAttribute):
        """
        Using the power of pgr_Dijsktra algorithm this function calculate the total routing cost for a pair of points.

        :param startVertexID: Initial Vertex to calculate the shortest path.
        :param endVertexID: Last Vertex to calculate the shortest path.
        :param costAttribute: Impedance/cost to measure the weight of the route.
        :return: Shortest path summary json.
        """

        Logger.getInstance().info("Start getTotalShortestPathCostOneToOne")

        sql = "SELECT " \
              "s.id AS start_vertex_id," \
              "e.id  AS end_vertex_id," \
              "r.agg_cost as total_cost," \
              "ST_MakeLine(s.the_geom, e.the_geom) AS geom " \
              "FROM(" \
              "SELECT * " \
              "FROM pgr_dijkstraCost(" \
              "\'SELECT " \
              "id::integer," \
              "source::integer," \
              "target::integer," \
              "(CASE  " \
              "WHEN luokka <> 0 AND (liikennevi = 0 OR liikennevi = 2 OR liikennevi = 5 OR liikennevi = 4)  " \
              "THEN %s " \
              "ELSE -1 " \
              "END)::double precision AS cost," \
              "(CASE " \
              "WHEN luokka <> 0 AND (liikennevi = 0 OR liikennevi = 2 OR liikennevi = 5 OR liikennevi = 3) " \
              "THEN %s " \
              "ELSE -1 " \
              "END)::double precision AS reverse_cost " \
              "FROM table_name', %s, %s, true)) as r," \
              "table_name_vertices_pgr AS s," \
              "table_name_vertices_pgr AS e " \
              "WHERE " \
              "s.id = r.start_vid " \
              "and e.id = r.end_vid ".replace("table_name", self.tableName) \
              % (costAttribute, costAttribute, startVertexID, endVertexID)
        # "GROUP BY " \
        # "s.id, e.id, r.agg_cost" \

        geojson = self.serviceProvider.execute(sql)
        Logger.getInstance().info("End getTotalShortestPathCostOneToOne")
        return geojson

    def getTotalShortestPathCostManyToOne(self, startVerticesID=[], endVertexID=None, costAttribute=None):
        """
        Using the power of pgr_Dijsktra algorithm this function calculate the total routing cost from a set of point to a single point.

        :param startVerticesID: Set of initial vertexes to calculate the shortest path.
        :param endVertexID: Last Vertex to calculate the shortest path.
        :param costAttribute: Impedance/cost to measure the weight of the route.
        :return: Shortest path summary json.
        """

        Logger.getInstance().info("Start getTotalShortestPathCostManyToOne")
        sql = "SELECT " \
              "s.id AS start_vertex_id," \
              "e.id  AS end_vertex_id," \
              "r.agg_cost as total_cost," \
              "ST_MakeLine(s.the_geom, e.the_geom) AS geom " \
              "FROM(" \
              "SELECT * " \
              "FROM pgr_dijkstraCost(" \
              "\'SELECT " \
              "id::integer," \
              "source::integer," \
              "target::integer," \
              "(CASE  " \
              "WHEN luokka <> 0 AND (liikennevi = 0 OR liikennevi = 2 OR liikennevi = 5 OR liikennevi = 4)  " \
              "THEN %s " \
              "ELSE -1 " \
              "END)::double precision AS cost," \
              "(CASE " \
              "WHEN luokka <> 0 AND (liikennevi = 0 OR liikennevi = 2 OR liikennevi = 5 OR liikennevi = 3) " \
              "THEN %s " \
              "ELSE -1 " \
              "END)::double precision AS reverse_cost " \
              "FROM table_name', ARRAY[%s], %s, true)) as r," \
              "table_name_vertices_pgr AS s," \
              "table_name_vertices_pgr AS e " \
              "WHERE " \
              "s.id = r.start_vid " \
              "and e.id = r.end_vid ".replace("table_name", self.tableName) \
              % (costAttribute, costAttribute, ",".join(map(str, startVerticesID)), endVertexID)
        # "GROUP BY " \
        # "s.id, e.id, r.agg_cost" \


        geojson = self.serviceProvider.execute(sql)
        Logger.getInstance().info("End getTotalShortestPathCostManyToOne")
        return geojson

    def getTotalShortestPathCostOneToMany(self, startVertexID=None, endVerticesID=[], costAttribute=None):
        """
        Using the power of pgr_Dijsktra algorithm this function calculate the total routing cost from a set of point to a single point.

        :param startVertexID: Initial vertexes to calculate the shortest path.
        :param endVerticesID: Set of ending vertexes to calculate the shortest path.
        :param costAttribute: Impedance/cost to measure the weight of the route.
        :return: Shortest path summary json.
        """

        Logger.getInstance().info("Start getTotalShortestPathCostOneToMany")

        sql = "SELECT " \
              "s.id AS start_vertex_id," \
              "e.id  AS end_vertex_id," \
              "r.agg_cost as total_cost," \
              "ST_MakeLine(s.the_geom, e.the_geom) AS geom " \
              "FROM(" \
              "SELECT * " \
              "FROM pgr_dijkstraCost(" \
              "\'SELECT " \
              "id::integer," \
              "source::integer," \
              "target::integer," \
              "(CASE  " \
              "WHEN luokka <> 0 AND (liikennevi = 0 OR liikennevi = 2 OR liikennevi = 5 OR liikennevi = 4)  " \
              "THEN %s " \
              "ELSE -1 " \
              "END)::double precision AS cost," \
              "(CASE " \
              "WHEN luokka <> 0 AND (liikennevi = 0 OR liikennevi = 2 OR liikennevi = 5 OR liikennevi = 3) " \
              "THEN %s " \
              "ELSE -1 " \
              "END)::double precision AS reverse_cost " \
              "FROM table_name', %s, ARRAY[%s], true)) as r," \
              "table_name_vertices_pgr AS s," \
              "table_name_vertices_pgr AS e " \
              "WHERE " \
              "s.id = r.start_vid " \
              "and e.id = r.end_vid ".replace("table_name", self.tableName) \
              % (costAttribute, costAttribute, startVertexID, ",".join(map(str, endVerticesID)))
        # "GROUP BY " \
        # "s.id, e.id, r.agg_cost" \


        geojson = self.serviceProvider.execute(sql)
        Logger.getInstance().info("End getTotalShortestPathCostOneToMany")
        return geojson

    # def getTotalShortestPathCostManyToMany(self, startVerticesID=[], endVerticesID=[], costAttribute=None):
    #     """
    #     Using the power of pgr_Dijsktra algorithm this function calculate the total routing cost from a set of point to a single point.
    #
    #     :param startVerticesID: Set of initial vertexes to calculate the shortest path.
    #     :param endVerticesID: Set of ending vertexes to calculate the shortest path.
    #     :param costAttribute: Impedance/cost to measure the weight of the route.
    #     :return: Shortest path summary json.
    #     """
    #
    #     # (CASE
    #     # WHEN liikennevi = 2 OR liikennevi = 3
    #     # THEN %s
    #     # ELSE -1
    #     # END)::double precision AS cost,
    #     # (CASE
    #     # WHEN liikennevi = 2 OR liikennevi = 4
    #     # THEN %s
    #     # ELSE -1
    #     # END)
    #
    #     print("Start getTotalShortestPathCostManyToMany")
    #     sql = "SELECT " \
    #           "s.id AS start_vertex_id," \
    #           "e.id  AS end_vertex_id," \
    #           "r.agg_cost as total_cost," \
    #           "ST_MakeLine(s.the_geom, e.the_geom) AS geom " \
    #           "FROM(" \
    #           "SELECT * " \
    #           "FROM pgr_dijkstraCost(" \
    #           "\'SELECT id::integer, source::integer, target::integer, " \
    #           "(CASE  " \
    #           "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 4)  " \
    #           "THEN %s " \
    #           "ELSE -1 " \
    #           "END)::double precision AS cost, " \
    #           "(CASE  " \
    #           "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 3)  " \
    #           "THEN %s " \
    #           "ELSE -1 " \
    #           "END)::double precision AS reverse_cost " \
    #           "FROM table_name\', ARRAY[%s], ARRAY[%s], true)) as r," \
    #           "table_name_vertices_pgr AS s," \
    #           "table_name_vertices_pgr AS e " \
    #           "WHERE " \
    #           "s.id = r.start_vid " \
    #           "and e.id = r.end_vid " \
    #           % (costAttribute, costAttribute, ",".join(map(str, startVerticesID)), ",".join(map(str, endVerticesID)))
    #     # "GROUP BY " \
    #     # "s.id, e.id, r.agg_cost" \
    #
    #
    #     geojson = self.serviceProvider.executePostgisQuery(sql)
    #     print("End getTotalShortestPathCostManyToMany")
    #     return geojson

    @dgl_timer
    def getTotalShortestPathCostManyToMany(self, startVerticesID=[], endVerticesID=[], costAttribute=None):
        """
        Using the power of pgr_Dijsktra algorithm this function calculate the total routing cost from a set of point to a single point.

        :param startVerticesID: Set of initial vertexes to calculate the shortest path.
        :param endVerticesID: Set of ending vertexes to calculate the shortest path.
        :param costAttribute: Impedance/cost to measure the weight of the route.
        :return: Shortest path summary json.
        """

        startVerticesCounter = 0
        startJump = int(getConfigurationProperties(section="PARALLELIZATION")["max_vertices_blocks"])

        sqlExecutionList = []

        while startVerticesCounter < len(startVerticesID):
            if startVerticesCounter + startJump > len(startVerticesID):
                startJump = len(startVerticesID) % startJump

            startBottomLimit = startVerticesCounter
            startUpperLimit = startVerticesCounter + startJump

            startVerticesCounter = startVerticesCounter + startJump

            endVerticesCounter = 0
            endJump = int(getConfigurationProperties(section="PARALLELIZATION")["max_vertices_blocks"])

            while endVerticesCounter < len(endVerticesID):
                if endVerticesCounter + endJump > len(endVerticesID):
                    endJump = len(endVerticesID) % endJump

                endBottomLimit = endVerticesCounter
                endUpperLimit = endVerticesCounter + endJump

                endVerticesCounter = endVerticesCounter + endJump

                sql = "SELECT " \
                      "s.id AS start_vertex_id," \
                      "e.id  AS end_vertex_id," \
                      "r.agg_cost as total_cost," \
                      "ST_MakeLine(s.the_geom, e.the_geom) AS geom " \
                      "FROM(" \
                      "SELECT * " \
                      "FROM pgr_dijkstraCost(" \
                      "\'SELECT " \
                      "id::integer," \
                      "source::integer," \
                      "target::integer," \
                      "(CASE  " \
                      "WHEN luokka <> 0 AND (liikennevi = 0 OR liikennevi = 2 OR liikennevi = 5 OR liikennevi = 4)  " \
                      "THEN %s " \
                      "ELSE -1 " \
                      "END)::double precision AS cost," \
                      "(CASE " \
                      "WHEN luokka <> 0 AND (liikennevi = 0 OR liikennevi = 2 OR liikennevi = 5 OR liikennevi = 3) " \
                      "THEN %s " \
                      "ELSE -1 " \
                      "END)::double precision AS reverse_cost " \
                      "FROM table_name', ARRAY[%s], ARRAY[%s], true)) as r," \
                      "table_name_vertices_pgr AS s," \
                      "table_name_vertices_pgr AS e " \
                      "WHERE " \
                      "s.id = r.start_vid " \
                      "and e.id = r.end_vid ".replace("table_name", self.tableName) \
                      % (costAttribute, costAttribute,
                         ",".join(map(str, startVerticesID[startBottomLimit:startUpperLimit])),
                         ",".join(map(str, endVerticesID[endBottomLimit:endUpperLimit]))
                         )
                # "GROUP BY " \
                # "s.id, e.id, r.agg_cost" \

                sqlExecutionList.append(sql)

        dataFrame = None

        with Parallel(n_jobs=int(getConfigurationProperties(section="PARALLELIZATION")["jobs"]),
                      backend="threading",
                      verbose=int(getConfigurationProperties(section="PARALLELIZATION")["verbose"])) as parallel:
            parallel._print = parallel_job_print
            returns = parallel(delayed(executePostgisQueryReturningDataFrame)(self.serviceProvider, sql)
                               for sql in sqlExecutionList)

            for newDataFrame in returns:
                if dataFrame is not None:
                    dataFrame = dataFrame.append(newDataFrame, ignore_index=True)
                else:
                    dataFrame = newDataFrame

        geojson = self.fileActions.convertToGeojson(dataFrame)

        return geojson

    def getEPSGCode(self):
        return self.epsgCode
