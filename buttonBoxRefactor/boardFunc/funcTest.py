def neighbors(matrix, rowNumber, colNumber):
    result = []
    # search the grid by the cords given 
    for rowAdd in range(-1, 2):
        newRow = rowNumber + rowAdd
        if newRow >= 0 and newRow <= len(matrix)-1:
            for colAdd in range(-1, 2):
                newCol = colNumber + colAdd
                if newCol >= 0 and newCol <= len(matrix)-1:
                    if newCol == colNumber and newRow == rowNumber:
                        continue
                    result.append((newRow,newCol))
    return result

def arrayMap(i, width):
    x = i % width;    # the remainder of i / width
    y = i // width;    # // is floor division
    return y,x
    