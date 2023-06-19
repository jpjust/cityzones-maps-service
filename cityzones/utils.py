import math

def __calculate_distance(a: dict, b: dict) -> float:
    """
    Calculate the distance from a to b using haversine formula.
    """
    lat1 = math.radians(a['lat'])
    lat2 = math.radians(b['lat'])
    lon1 = math.radians(a['lon'])
    lon2 = math.radians(b['lon'])
    r = 6378137
    return 2 * r * math.asin(math.sqrt(math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2))

def __calculate_distance_in_grid(grid: dict, a: dict, b: dict) -> int:
    """
    Calculate the distance from a to b in the grid.
    """
    x1 = a['id'] % grid['grid_x']
    x2 = b['id'] % grid['grid_x']
    y1 = int(a['id'] / grid['grid_x'])
    y2 = int(b['id'] / grid['grid_x'])
    return math.sqrt(abs(x2 - x1) ** 2 + abs(y2 - y1) ** 2)
