# MySQL spatial queries

To insert a row with geospatial data, use the following statement:

```sql
INSERT INTO `cells`(`coord`) VALUES (ST_GeomFromText('POINT(1 1)'));
```

This statement will insert a cell positioned at point `(1, 1)`.

Then it is easy to select columns within a boundary.

```sql
SELECT id, ST_AsText(coord) FROM `cells` WHERE MBRContains(ST_GeomFromText('Polygon((0 0, 0 2, 2 2, 2 0, 0 0))'), coord);
```

This will select all cells within the boundary defined by the polygon `(0, 0), (0, 2), (2, 2), (2, 0), (0, 0)`. Pay attention that the last point is also the first point, so the perimeter is closed.

When using geographical coordinates, just use longitude as `x` and latitude as `y`:

```sql
SELECT id, ST_AsText(coord) FROM `cells` WHERE MBRContains(ST_GeomFromText('Polygon((-39.088252 -13.379074, -39.089363 -13.341446, -39.046233 -13.342497, -39.044822 -13.384983, -39.088252 -13.379074))'), coord);
```
