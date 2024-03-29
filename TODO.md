# Restricted positioning algorithm

In restricted positioning algorithm the EDUs can be deployed only in permitted zones (only roads for now). If the EDU is placed in a not permitted zone, it must be moved to the nearest permitted zone only if the current zone will still be covered by it.

If all permitted zones within the covering radius of the EDU is already occupied by another EDU, the current zone can be cleared and the EDU removed.

# Delete worker temp files

Files generated by the worker must be deleted after sending.

# Reading the map files for classification

Data can be stored in a binary format so riskzones can read it sequencially and classify the zones. The multiprocessing pool can send the position of the zone in the file instead of the zone data, so the pool worker can read the file in the correct position.

# Default values in .env

The programs should check if all the required values are present in .env file. Optional values should get a default if not present.

# Filter extract data

Use the parameters in https://docs.osmcode.org/osmium/latest/osmium-tags-filter.html to filter data. Unfiltered planet PBF gets too high memory usage.
