"""
Package for parsing the Yandex station data and filling the DB with it.

The entry point is fill_db module. It triggers the DB population process
and contains the actual logic for the DB population.

First of all, the initial data is obtained - either downloaded from the Yandex API,
or loaded from a JSON file (the latter is for testing purposes). This is handled by
the parse module which structures the initial data into pydantic models by calling
the parse_file or parse_obj methods of the pydantic parent World model.

The pydantic World model is located in the schema module. It contains a pydantic schema
for the initial data. It represents the "World" from the point of view of
the Yandex JSON: it gets the information about the countries, regions, settlements,
stations etc from the JSON and packages them into pydantic objects that are easy
to manipulate with.

After the initial data has been structured, the process of converting it into
SQLAlchemy models begins. This process is complicated by the fact that the
relations between the different entities need to be maintained: e.g. a station
shall have a foreign key to a settlement, which shall have a foreign key to a region,
etc etc. This is handled by introducing connecting pydantic models (RegionsByCountry,
PointsByRegion, etc) that have a parent entity in the form of an ORM model and the list
of child entities as pydantic models.

The ORM models with all the necessary relations are then added to sessions,
and the sessions are committed. All of this is handled by fill_db module.

---------- !!! NOTE ON DATABASE SCHEMA !!! ----------

Before starting to fill the DB, the DB schema has to be created. This can be done
in two ways:
  - by running the db.stations.models.create_db_schema() function
  - by running alembic migrations (alembic upgrade head)

---------- !!! NOTE ON RAM !!! ----------

The operations described above require at least 4 GB of RAM: the initial stations
data from Yandex is a 40 MB JSON file. Then all of this is passed through various
models several times, so these operations require large amount of memory.

If the RAM on the deployment server is not enough, it is recommended to run the
DB population operations on a PC with enough RAM and then transfer DB data to the
deployment server.
"""
