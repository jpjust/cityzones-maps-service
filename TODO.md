# Restricted positioning algorithm

In restricted positioning algorithm the EDUs can be deployed only in permitted zones (only roads for now). If the EDU is placed in a not permitted zone, it must be moved to the nearest permitted zone only if the current zone will still be covered by it.

If all permitted zones within the covering radius of the EDU is already occupied by another EDU, the current zone can be cleared and the EDU removed.
