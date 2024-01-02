from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

def findPath(matrix, startPoint, endPoint):
    # 1. create a grid
    grid = Grid(matrix=matrix)

    # 2. create a start and end cell
    start = grid.node(startPoint[0], startPoint[1])
    end = grid.node(endPoint[0], endPoint[1])

    # 3. create a finder with a movement style
    #finder = AStarFinder(diagonal_movement=DiagonalMovement.always)
    finder = AStarFinder()

    # 4. use the finder to find the path
    opath, runs = finder.find_path(start, end, grid)

    # print the result
    path = []
    for item in opath:
        path.append((item.x, item.y))

    return path