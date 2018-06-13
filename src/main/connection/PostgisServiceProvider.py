import psycopg2
import geopandas as gpd

from src.main.connection import AbstractGeojsonProvider
from src.main.util import getConfigurationProperties, GPD_CRS, FileActions, \
    dgl_timer


def executePostgisQueryReturningDataFrame(self, sql):
    """
    Given a PG_SQL execute the query and retrieve the attributes and its respective geometries.

    :param sql: Postgis SQL sentence.
    :return: Sentence query results.
    """

    con = self.getConnection()

    try:
        df = gpd.GeoDataFrame.from_postgis(sql, con, geom_col='geom', crs=GPD_CRS.PSEUDO_MERCATOR)
    finally:
        con.close()

    return df


class PostgisServiceProvider(AbstractGeojsonProvider):
    def __init__(self, epsgCode="EPSG:3857"):
        self.epsgCode = epsgCode
        self.fileActions = FileActions()

    def getConnection(self):
        """
        Creates a new connection to the pg_database

        :return: New connection.
        """
        config = getConfigurationProperties(section="DATABASE_CONFIG")
        con = psycopg2.connect(database=config["database_name"], user=config["user"], password=config["password"],
                               host=config["host"])

        return con

    @dgl_timer
    def execute(self, sql):
        """
        Given a PG_SQL execute the query and retrieve the attributes and its respective geometries.

        :param sql: Postgis SQL sentence.
        :return: Sentence query results.
        """

        con = self.getConnection()

        try:
            df = gpd.GeoDataFrame.from_postgis(sql, con, geom_col='geom', crs=GPD_CRS.PSEUDO_MERCATOR)
        finally:
            con.close()

        newJson = self.fileActions.convertToGeojson(df)

        return newJson

    def createTemporaryTable(self, con, tableName, columns):

        cursor = con.cursor()
        sqlCreateTemporalTable = "CREATE TEMPORARY TABLE %s(%s) ON COMMIT DELETE ROWS;"
        sqlColumns = ""
        for column in columns:
            sqlColumns = sqlColumns + column + " " + columns[column] + ", "

        if len(columns) > 0:
            sqlColumns = sqlColumns[:-2]

        sqlCreateTemporalTable = sqlCreateTemporalTable % (tableName, sqlColumns)

        cursor.execute(sqlCreateTemporalTable)
        # cursor.fetchall()
        con.commit()

    def getUUID(self, con):
        sql = "select uuid_generate_v4()"
        cursor = con.cursor()
        cursor.execute(sql)
        codes = cursor.fetchall()
        return codes[0][0]  # extracting from tuple

        # def getNearestVertexFromAPoint(self, coordinates):
        #     """
        #     From the Database retrieve the nearest vertex from a given point coordinates.
        #
        #     :param coordinates: Point coordinates. e.g [889213124.3123, 231234.2341]
        #     :return: Geojson (Geometry type: Point) with the nearest point coordinates.
        #     """
        #
        #     print("Start getNearestVertexFromAPoint")
        #
        #     epsgCode = coordinates.getEPSGCode().split(":")[1]
        #
        #     sql = "SELECT " \
        #           "v.id," \
        #           "ST_SnapToGrid(v.the_geom, 0.00000001) AS geom, " \
        #           "string_agg(distinct(e.old_id || ''),',') AS name " \
        #           "FROM " \
        #           "edges_vertices_pgr AS v," \
        #           "edges AS e " \
        #           "WHERE " \
        #           "v.id = (SELECT " \
        #           "id" \
        #           "FROM edges_vertices_pgr" \
        #           "AND ST_DWithin(ST_Transform(v.the_geom, 4326)," \
        #           "ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), %s), 4326)::geography," \
        #           "1000)" \
        #           "ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint(%s, %s), %s) LIMIT 1)" \
        #           "AND (e.source = v.id OR e.target = v.id)" \
        #           "GROUP BY v.id, v.the_geom" % (str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode,
        #                                          str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode)
        #
        #     geojson = self.execute(sql)
        #
        #     print("End getNearestVertexFromAPoint")
        #     return geojson
        #
        # def getNearestRoutableVertexFromAPoint(self, coordinates, radius=500):
        #     """
        #     From the Database retrieve the nearest routing vertex from a given point coordinates.
        #
        #     :param coordinates: Point coordinates. e.g [889213124.3123, 231234.2341]
        #     :return: Geojson (Geometry type: Point) with the nearest point coordinates.
        #     """
        #
        #     print("Start getNearestRoutableVertexFromAPoint")
        #
        #     epsgCode = coordinates.getEPSGCode().split(":")[1]
        #
        #     sql = self.getNearestRoutableVertexSQL(coordinates, epsgCode, radius)
        #
        #     geojson = self.execute(sql)
        #     maxTries = 5
        #     tries = 0
        #     while len(geojson["features"]) == 0 and tries < maxTries:
        #         tries += 1
        #         radius += 500
        #         sql = self.getNearestRoutableVertexSQL(coordinates, epsgCode, radius)
        #         geojson = self.execute(sql)
        #
        #     if len(geojson["features"]) > 0:
        #         print("Nearest Vertex found within the radius %s " % radius)
        #     else:
        #         print("Nearest Vertex NOT found within the radius %s " % radius)
        #
        #     print("End getNearestRoutableVertexFromAPoint")
        #     return geojson
        #
        # def getNearestRoutableVertexSQL(self, coordinates, epsgCode, radius):
        #     # return "SELECT " \
        #     #        "v.id," \
        #     #        "ST_SnapToGrid(v.the_geom, 0.00000001) AS geom, " \
        #     #        "string_agg(distinct(e.old_id || ''),',') AS name " \
        #     #        "FROM " \
        #     #        "edges_vertices_pgr AS v," \
        #     #        "edges AS e " \
        #     #        "WHERE " \
        #     #        "(e.source = v.id OR e.target = v.id) " \
        #     #        "AND e.TOIMINNALL <> 10 " \
        #     #        "AND ST_DWithin(ST_Transform(v.the_geom, 4326)," \
        #     #        "ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), %s), 4326)::geography," \
        #     #        "%s)" \
        #     #        "GROUP BY v.id, v.the_geom " \
        #     #        "ORDER BY v.the_geom <-> ST_SetSRID(ST_MakePoint(%s, %s), %s)" \
        #     #        "LIMIT 1" % (str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode,
        #     #                     str(radius),
        #     #                     str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode)
        #     return "SELECT " \
        #            "v.id," \
        #            "ST_SnapToGrid(v.the_geom, 0.00000001) AS geom, " \
        #            "string_agg(distinct(e.id || ''),',') AS name " \
        #            "FROM " \
        #            "edges_vertices_pgr AS v," \
        #            "edges AS e " \
        #            "WHERE " \
        #            "(e.source = v.id OR e.target = v.id) " \
        #            "AND e.TOIMINNALL <> 10 " \
        #            "AND ST_DWithin(ST_Transform(v.the_geom, 4326)," \
        #            "ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), %s), 4326)::geography," \
        #            "%s)" \
        #            "GROUP BY v.id, v.the_geom " \
        #            "ORDER BY v.the_geom <-> ST_SetSRID(ST_MakePoint(%s, %s), %s)" \
        #            "LIMIT 1" % (str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode,
        #                         str(radius),
        #                         str(coordinates.getLongitude()), str(coordinates.getLatitude()), epsgCode)
        #
        # def getShortestPath(self, startVertexId, endVertexId, cost):
        #     """
        #     From a pair of vertices (startVertexId, endVertexId) and based on the "cost" attribute,
        #     retrieve the shortest path by calling the WFS Service.
        #
        #     :param startVertexId: Start vertex from the requested path.
        #     :param endVertexId: End vertex from the requested path.
        #     :param cost: Attribute to calculate the cost of the shortest path
        #     :return: Geojson (Geometry type: LineString) containing the segment features of the shortest path.
        #     """
        #
        #     print("Start getShortestPath")
        #
        #     # sql = "SELECT " \
        #     #       "min(r.seq) AS seq, " \
        #     #       "e.old_id AS id," \
        #     #       "e.liikennevi::integer as direction," \
        #     #       "sum(e.pituus) AS distance," \
        #     #       "sum(e.digiroa_aa) AS speed_limit_time," \
        #     #       "sum(e.kokopva_aa) AS day_avg_delay_time," \
        #     #       "sum(e.keskpva_aa) AS midday_delay_time," \
        #     #       "sum(e.ruuhka_aa) AS rush_hour_delay_time," \
        #     #       "ST_SnapToGrid(ST_LineMerge(ST_Collect(e.the_geom)), 0.00000001) AS geom " \
        #     #       "FROM " \
        #     #       "pgr_dijkstra('SELECT " \
        #     #       "id::integer," \
        #     #       "source::integer," \
        #     #       "target::integer," \
        #     #       "(CASE  " \
        #     #       "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 4)  " \
        #     #       "THEN %s " \
        #     #       "ELSE -1 " \
        #     #       "END)::double precision AS cost," \
        #     #       "(CASE " \
        #     #       "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 3) THEN %s " \
        #     #       "ELSE -1 " \
        #     #       "END)::double precision AS reverse_cost " \
        #     #       "FROM edges', %s, %s, true, true) AS r, " \
        #     #       "edges AS e " \
        #     #       "WHERE " \
        #     #       "r.id2 = e.id " \
        #     #       "GROUP BY e.old_id, e.liikennevi" % (cost, cost, str(startVertexId), str(endVertexId))
        #     sql = "SELECT " \
        #           "min(r.seq) AS seq, " \
        #           "e.id AS id, " \
        #           "e.liikennevi::integer as direction," \
        #           "sum(e.pituus) AS distance," \
        #           "sum(e.digiroa_aa) AS speed_limit_time," \
        #           "sum(e.kokopva_aa) AS day_avg_delay_time," \
        #           "sum(e.keskpva_aa) AS midday_delay_time," \
        #           "sum(e.ruuhka_aa) AS rush_hour_delay_time," \
        #           "ST_SnapToGrid(e.the_geom, 0.00000001) AS geom " \
        #           "FROM " \
        #           "pgr_dijkstra('SELECT " \
        #           "id::integer," \
        #           "source::integer," \
        #           "target::integer," \
        #           "(CASE  " \
        #           "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 4)  " \
        #           "THEN %s " \
        #           "ELSE -1 " \
        #           "END)::double precision AS cost," \
        #           "(CASE " \
        #           "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 3) THEN %s " \
        #           "ELSE -1 " \
        #           "END)::double precision AS reverse_cost " \
        #           "FROM edges', %s, %s, true, true) AS r, " \
        #           "edges AS e " \
        #           "WHERE " \
        #           "r.id2 = e.id " \
        #           "GROUP BY e.id, e.liikennevi" % (cost, cost, str(startVertexId), str(endVertexId))
        #
        #     geojson = self.execute(sql)
        #     print("End getShortestPath")
        #     return geojson
        #
        # def getTotalShortestPathCostOneToOne(self, startVertexID, endVertexID, costAttribute):
        #     """
        #     Using the power of pgr_Dijsktra algorithm this function calculate the total routing cost for a pair of points.
        #
        #     :param startVertexID: Initial Vertex to calculate the shortest path.
        #     :param endVertexID: Last Vertex to calculate the shortest path.
        #     :param costAttribute: Impedance/cost to measure the weight of the route.
        #     :return: Shortest path summary json.
        #     """
        #
        #     print("Start getTotalShortestPathCostOneToOne")
        #
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
        #           "FROM edges\', %s, %s, true)) as r," \
        #           "edges_vertices_pgr AS s," \
        #           "edges_vertices_pgr AS e " \
        #           "WHERE " \
        #           "s.id = r.start_vid " \
        #           "and e.id = r.end_vid " \
        #           % (
        #               costAttribute, costAttribute, startVertexID, endVertexID)
        #     # "GROUP BY " \
        #     # "s.id, e.id, r.agg_cost" \
        #
        #
        #     geojson = self.execute(sql)
        #     print("End getTotalShortestPathCostOneToOne")
        #     return geojson
        #
        # def getTotalShortestPathCostManyToOne(self, startVerticesID=[], endVertexID=None, costAttribute=None):
        #     """
        #     Using the power of pgr_Dijsktra algorithm this function calculate the total routing cost from a set of point to a single point.
        #
        #     :param startVerticesID: Set of initial vertexes to calculate the shortest path.
        #     :param endVertexID: Last Vertex to calculate the shortest path.
        #     :param costAttribute: Impedance/cost to measure the weight of the route.
        #     :return: Shortest path summary json.
        #     """
        #
        #     print("Start getTotalShortestPathCostManyToOne")
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
        #           "FROM edges\', ARRAY[%s], %s, true)) as r," \
        #           "edges_vertices_pgr AS s," \
        #           "edges_vertices_pgr AS e " \
        #           "WHERE " \
        #           "s.id = r.start_vid " \
        #           "and e.id = r.end_vid " \
        #           % (
        #               costAttribute, costAttribute, ",".join(map(str, startVerticesID)), endVertexID)
        #     # "GROUP BY " \
        #     # "s.id, e.id, r.agg_cost" \
        #
        #
        #     geojson = self.execute(sql)
        #     print("End getTotalShortestPathCostManyToOne")
        #     return geojson
        #
        # def getTotalShortestPathCostOneToMany(self, startVertexID=None, endVerticesID=[], costAttribute=None):
        #     """
        #     Using the power of pgr_Dijsktra algorithm this function calculate the total routing cost from a set of point to a single point.
        #
        #     :param startVertexID: Initial vertexes to calculate the shortest path.
        #     :param endVerticesID: Set of ending vertexes to calculate the shortest path.
        #     :param costAttribute: Impedance/cost to measure the weight of the route.
        #     :return: Shortest path summary json.
        #     """
        #
        #     print("Start getTotalShortestPathCostOneToMany")
        #
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
        #           "FROM edges\', %s, ARRAY[%s], true)) as r," \
        #           "edges_vertices_pgr AS s," \
        #           "edges_vertices_pgr AS e " \
        #           "WHERE " \
        #           "s.id = r.start_vid " \
        #           "and e.id = r.end_vid " \
        #           % (
        #               costAttribute, costAttribute, startVertexID, ",".join(map(str, endVerticesID)))
        #     # "GROUP BY " \
        #     # "s.id, e.id, r.agg_cost" \
        #
        #
        #     geojson = self.execute(sql)
        #     print("End getTotalShortestPathCostOneToMany")
        #     return geojson
        #
        # # def getTotalShortestPathCostManyToMany(self, startVerticesID=[], endVerticesID=[], costAttribute=None):
        # #     """
        # #     Using the power of pgr_Dijsktra algorithm this function calculate the total routing cost from a set of point to a single point.
        # #
        # #     :param startVerticesID: Set of initial vertexes to calculate the shortest path.
        # #     :param endVerticesID: Set of ending vertexes to calculate the shortest path.
        # #     :param costAttribute: Impedance/cost to measure the weight of the route.
        # #     :return: Shortest path summary json.
        # #     """
        # #
        # #     # (CASE
        # #     # WHEN liikennevi = 2 OR liikennevi = 3
        # #     # THEN %s
        # #     # ELSE -1
        # #     # END)::double precision AS cost,
        # #     # (CASE
        # #     # WHEN liikennevi = 2 OR liikennevi = 4
        # #     # THEN %s
        # #     # ELSE -1
        # #     # END)
        # #
        # #     print("Start getTotalShortestPathCostManyToMany")
        # #     sql = "SELECT " \
        # #           "s.id AS start_vertex_id," \
        # #           "e.id  AS end_vertex_id," \
        # #           "r.agg_cost as total_cost," \
        # #           "ST_MakeLine(s.the_geom, e.the_geom) AS geom " \
        # #           "FROM(" \
        # #           "SELECT * " \
        # #           "FROM pgr_dijkstraCost(" \
        # #           "\'SELECT id::integer, source::integer, target::integer, " \
        # #           "(CASE  " \
        # #           "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 4)  " \
        # #           "THEN %s " \
        # #           "ELSE -1 " \
        # #           "END)::double precision AS cost, " \
        # #           "(CASE  " \
        # #           "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 3)  " \
        # #           "THEN %s " \
        # #           "ELSE -1 " \
        # #           "END)::double precision AS reverse_cost " \
        # #           "FROM edges\', ARRAY[%s], ARRAY[%s], true)) as r," \
        # #           "edges_vertices_pgr AS s," \
        # #           "edges_vertices_pgr AS e " \
        # #           "WHERE " \
        # #           "s.id = r.start_vid " \
        # #           "and e.id = r.end_vid " \
        # #           % (costAttribute, costAttribute, ",".join(map(str, startVerticesID)), ",".join(map(str, endVerticesID)))
        # #     # "GROUP BY " \
        # #     # "s.id, e.id, r.agg_cost" \
        # #
        # #
        # #     geojson = self.executePostgisQuery(sql)
        # #     print("End getTotalShortestPathCostManyToMany")
        # #     return geojson
        #
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
        #     startTime = time.time()
        #     print("getTotalShortestPathCostManyToMany Start Time: %s" % getFormattedDatetime(timemilis=startTime))
        #
        #     startVerticesCounter = 0
        #     startJump = int(getConfigurationProperties(section="PARALLELIZATION")["max_vertices_blocks"])
        #
        #     sqlExecutionList = []
        #
        #     while startVerticesCounter < len(startVerticesID):
        #         if startVerticesCounter + startJump > len(startVerticesID):
        #             startJump = len(startVerticesID) % startJump
        #
        #         startBottomLimit = startVerticesCounter
        #         startUpperLimit = startVerticesCounter + startJump
        #
        #         startVerticesCounter = startVerticesCounter + startJump
        #
        #         endVerticesCounter = 0
        #         endJump = int(getConfigurationProperties(section="PARALLELIZATION")["max_vertices_blocks"])
        #
        #         while endVerticesCounter < len(endVerticesID):
        #             if endVerticesCounter + endJump > len(endVerticesID):
        #                 endJump = len(endVerticesID) % endJump
        #
        #             endBottomLimit = endVerticesCounter
        #             endUpperLimit = endVerticesCounter + endJump
        #
        #             endVerticesCounter = endVerticesCounter + endJump
        #
        #             sql = "SELECT " \
        #                   "s.id AS start_vertex_id," \
        #                   "e.id  AS end_vertex_id," \
        #                   "r.agg_cost as total_cost," \
        #                   "ST_MakeLine(s.the_geom, e.the_geom) AS geom " \
        #                   "FROM(" \
        #                   "SELECT * " \
        #                   "FROM pgr_dijkstraCost(" \
        #                   "\'SELECT id::integer, source::integer, target::integer, " \
        #                   "(CASE  " \
        #                   "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 4)  " \
        #                   "THEN %s " \
        #                   "ELSE -1 " \
        #                   "END)::double precision AS cost, " \
        #                   "(CASE  " \
        #                   "WHEN toiminnall <> 10 AND (liikennevi = 2 OR liikennevi = 3)  " \
        #                   "THEN %s " \
        #                   "ELSE -1 " \
        #                   "END)::double precision AS reverse_cost " \
        #                   "FROM edges\', ARRAY[%s], ARRAY[%s], true)) as r," \
        #                   "edges_vertices_pgr AS s," \
        #                   "edges_vertices_pgr AS e " \
        #                   "WHERE " \
        #                   "s.id = r.start_vid " \
        #                   "and e.id = r.end_vid " \
        #                   % (costAttribute, costAttribute,
        #                      ",".join(map(str, startVerticesID[startBottomLimit:startUpperLimit])),
        #                      ",".join(map(str, endVerticesID[endBottomLimit:endUpperLimit]))
        #                      )
        #             # "GROUP BY " \
        #             # "s.id, e.id, r.agg_cost" \
        #
        #             sqlExecutionList.append(sql)
        #
        #     dataFrame = None
        #
        #     with Parallel(n_jobs=int(getConfigurationProperties(section="PARALLELIZATION")["jobs"]),
        #                   backend="threading",
        #                   verbose=int(getConfigurationProperties(section="PARALLELIZATION")["verbose"])) as parallel:
        #         parallel._print = parallel_job_print
        #         returns = parallel(delayed(executePostgisQueryReturningDataFrame)(self, sql)
        #                            for sql in sqlExecutionList)
        #
        #         for newDataFrame in returns:
        #             if dataFrame is not None:
        #                 dataFrame = dataFrame.append(newDataFrame, ignore_index=True)
        #             else:
        #                 dataFrame = newDataFrame
        #
        #     geojson = self.fileActions.convertToGeojson(dataFrame)
        #
        #     endTime = time.time()
        #     print("getTotalShortestPathCostManyToMany End Time: %s" % getFormattedDatetime(timemilis=endTime))
        #
        #     totalTime = timeDifference(startTime, endTime)
        #     print("getTotalShortestPathCostManyToMany Total Time: %s m" % totalTime)
        #
        #     return geojson
        #
        # def getEPSGCode(self):
        #     return self.epsgCode
        #
        # def createTemporaryTable(self, con, tableName, columns):
        #
        #     cursor = con.cursor()
        #     sqlCreateTemporalTable = "CREATE TEMPORARY TABLE %s(%s) ON COMMIT DELETE ROWS;"
        #     sqlColumns = ""
        #     for column in columns:
        #         sqlColumns = sqlColumns + column + " " + columns[column] + ", "
        #
        #     if len(columns) > 0:
        #         sqlColumns = sqlColumns[:-2]
        #
        #     sqlCreateTemporalTable = sqlCreateTemporalTable % (tableName, sqlColumns)
        #
        #     cursor.execute(sqlCreateTemporalTable)
        #     # cursor.fetchall()
        #     con.commit()
        #
        # def getUUID(self, con):
        #     sql = "select uuid_generate_v4()"
        #     cursor = con.cursor()
        #     cursor.execute(sql)
        #     codes = cursor.fetchall()
        #     return codes[0][0]  # extracting from tuple
