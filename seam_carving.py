from typing import Dict, Any

import utils
import numpy as np
import utils

NDArray = Any


def resize(image: NDArray, out_height: int, out_width: int, forward_implementation: bool) -> Dict[str, NDArray]:
    """

    :param image: ِnp.array which represents an image.
    :param out_height: the resized image height
    :param out_width: the resized image width
    :param forward_implementation: a boolean flag that indicates whether forward or basic implementation is used.
                                    if forward_implementation is true then the forward-looking energy is used otherwise
                                    the basic implementation is used.
    :return: A dictionary with three elements, {'resized' : img1, 'vertical_seams' : img2 ,'horizontal_seams' : img3},
            where img1 is the resized image and img2/img3 are the visualization images
            (where the chosen seams are colored red and black for vertical and horizontal seams, respectively).
    """

    # get width and height, and count how many seams to add/remove horizontally and vertically
    height, width, _ = image.shape
    widthDiff = out_width - width
    heightDiff = out_height - height

    # initialize useful matrices - MAYBE MAKE THIS GLOBAL?

    # saves the image converted to grayscale, WILL BE SHRANK AND ENLARGED
    grayscaleMat = utils.to_grayscale(image)

    # save for each cell its original row and column, WILL BE SHRANK AND ENLARGED
    originalRowMat, originalColMat = np.indices((height, width))

    # TODO: every cell will be TRUE or FALSE, coloured in RED or not.
    #  this will be in original height and width:
    VerticalSeamMatMask = np.zeros_like(grayscaleMat, dtype=bool)
    # TODO: every cell will be TRUE or FALSE, coloured in Black or not.
    #  this will be in new shrunk/enlarged width (after removing/adding vertical seams),
    #  but in original height (before adding/removing horizontal seams).
    HorizontalSeamMatMask = np.zeros((height, out_width), dtype=bool)

    # backtracking matrix. for every cell, the value is either 0 1 or 2:
    # 0 for upper left cell, 1 for upper cell, 2 for upper right cell
    # denotes the cell that gave the current cell its value in the cost matrix.
    costMat, backTrackingMat = getCostMatrix(grayscaleMat, forward_implementation)

    # TODO: here, copy grayscaleMat, find k seams and delete them, marking on outputVerticalSeamMat.
    #   if adding instead of removing - using outputVerticalSeamMat duplicate the pixels marked using np.insert.
    # add or remove k seams horizontally
    if heightDiff > 0:
        resized_image = add_k_seams(image, out_height, out_width, forward_implementation, heightDiff)
    if heightDiff < 0:
        resized_image = remove_k_seams(image, out_height, out_width, forward_implementation, heightDiff)

    # rotate the image, add/remove k seams horizontally, and rotate back
    if widthDiff > 0:
        resized_image = rotate_image_counter_clockwise(
            add_k_seams(rotate_image_clockwise(image, height, out_width),
                        out_height, out_width, forward_implementation, widthDiff))
    if widthDiff < 0:
        resized_image = rotate_image_counter_clockwise(
            remove_k_seams(rotate_image_clockwise(image, height, out_width), out_height, out_width,
                           forward_implementation, widthDiff))

    # TODO: return { 'resized' : img1, 'vertical_seams' : img2 ,'horizontal_seams' : img3}


def remove_k_seams(image: NDArray, out_height: int, out_width: int, forward_implementation: bool, k: int):
    # TODO this function removes the best seam from the image, k times.
    #  when deleting seams, we must delete one by one: i.e, calculate cost matrix, delete the seam, and calculate
    #  cost matrix again....
    currHeight, currWidth = image.shape
    for i in range(k):  # use range if you don't want to use tqdm
        img = carve_column(image)
    return img


def add_k_seams(image: NDArray, out_height: int, out_width: int, forward_implementation: bool, k: int):
    # TODO this function duplicates the best seam from the image, k times.
    # TODO  when adding seams, we must find all k best seams using the same cost matrix, and only then
    #   #  duplicate them all once.
    r, c = image.shape
    for i in range(k):  # use range if you don't want to use tqdm
        img = carve_column(image)
    return img


def carve_column(image: NDArray, forward_implementation: bool):
    r, c = image.shape
    # TODO: will not do grayscale here, we only need to do this once, not for every seam
    gray_image = utils.to_grayscale(image)
    M, backtrack = minimum_seam(gray_image, forward_implementation)

    # Create a (r, c) matrix filled with the value True
    # We'll be removing all pixels from the image which
    # have False later
    mask = np.ones((r, c), dtype=np.bool)

    # Find the position of the smallest element in the
    # last row of M
    j = np.argmin(M[-1])

    for i in reversed(range(r)):
        # Mark the pixels for deletion
        mask[i, j] = False
        j = backtrack[i, j]
    # Delete all the pixels marked False in the mask,
    # and resize it to the new image dimensions
    img = image[mask]
    return img


# image in gray scale
def minimum_seam(image: NDArray, forward_implementation: bool):
    r, c = image.shape
    cost_matrix = getCostMatrix(image, )
    M = cost_matrix.copy()
    backtrack = np.zeros_like(M, dtype=np.int)

    for i in range(1, r):
        for j in range(0, c):
            # Handle the left edge of the image, to ensure we don't index -1
            if j == 0:
                index = np.argmin(M[i - 1, j:j + 2])
                backtrack[i, j] = index + j
                min_energy = M[i - 1, index + j]
            else:
                index = np.argmin(M[i - 1, j - 1:j + 2])
                backtrack[i, j] = index + j - 1
                min_energy = M[i - 1, index + j - 1]
            M[i, j] += min_energy
    return M, backtrack


def getCostMatrix(grayscaleMat: NDArray, forward_implementation: bool) -> (NDArray, NDArray):
    """

    :param grayscaleMat: a matrix of the image, in grayscale.
    :param forward_implementation: the calculation is different depending on the implementation
    :return: the completed cost matrix, and the backtracking matrix
            backTrackingMat: for every cell, the value is either 0 1 or 2:
            1 for upper left cell, 2 for upper cell, 3 for upper right cell
            denotes the cell that gave the current cell its value (in the cost matrix.
    """
    # get E(i,j).
    height, width = grayscaleMat.shape

    # calculate forward energy if needed (or just zeroes)
    if forward_implementation:
        # create three forward energy matrices for cl, cv, and cr
        forwardCL, forwardCV, forwardCR = get_forward_energy_matrix(grayscaleMat, height, width)
    else:
        # just zeroes
        forwardCR = forwardCV = forwardCL = np.zeros_like(grayscaleMat)

    # find cost matrix using gradients and forward energy by going row by row and getting minimums from prev row
    gradientMat = utils.get_gradients(grayscaleMat)
    costMatrix = np.copy(gradientMat)
    backTrackingMat = np.zeros_like(grayscaleMat, dtype=int)

    # for every row calculate cost matrix using the previous row.
    for i in range(1, height):
        # M[i-1,j-1]
        costRollUpLeft = np.roll(costMatrix[i - 1], shift=1)
        # M[i-1,j] is costMatrix[i - 1]
        # M[i-1,j+1]
        costRollUpRight = np.roll(costMatrix[i - 1], shift=-1)
        # arrange the candidates in a list
        possibleValueForCostMatrixRow = [np.add(costRollUpLeft, forwardCL[i]), np.add(costMatrix[i - 1], forwardCV[i]),
                                         np.add(costRollUpRight, forwardCR[i])]
        # find the minimum index (0 1 or 2 meaning left, up, or right ), and copy the value into costMatrix
        backTrackingMat[i] = np.argmin(possibleValueForCostMatrixRow, axis=0)
        # TODO: use the indexes from currMinIdx to somehow select the correct values from three different arrays,
        #  faster performance instead of doing minimum twice.
        np.add(costMatrix[i], np.min(possibleValueForCostMatrixRow, axis=0), out=costMatrix[i])

        # edge cases - left edge j=0, right edge j = width-1
        possibleValLeftEdge = [costMatrix[i - 1, 0] + forwardCV[i, 0], costRollUpRight[0] + forwardCR[i, 0]]
        backTrackingMat[i, 0] = np.argmin(possibleValLeftEdge) + 1  # because it cant be 0 (left)
        costMatrix[i, 0] = gradientMat[i, 0] + np.min(possibleValLeftEdge)
        possibleValRightEdge = [costMatrix[i - 1, width - 1] + forwardCV[i, width - 1],
                                costRollUpRight[width - 1] + forwardCR[i, width - 1]]
        backTrackingMat[i, width - 1] = np.argmin(possibleValRightEdge)
        costMatrix[i, width - 1] = gradientMat[i, width - 1] + np.min(possibleValRightEdge)

    return costMatrix, backTrackingMat


# this function calculates Cv, Cr, and Cl for a given grayscale image
def get_forward_energy_matrix(grayScaleMat: NDArray, height, width) -> \
        (NDArray, NDArray, NDArray):
    forwardCV = np.empty_like(grayScaleMat)
    forwardCL = np.empty_like(grayScaleMat)
    forwardCR = np.empty_like(grayScaleMat)

    # TODO calculate cv,cr,and cl using np.add, np.roll, np.subtract, np.abs
    matRollJPlus1 = np.roll(grayScaleMat, axis=1, shift=-1)  # take j+1
    matRollJMinus1 = np.roll(grayScaleMat, axis=1, shift=1)  # take j-1
    matRollIMinus1 = np.roll(grayScaleMat, axis=0, shift=1)  # take i-1

    # CV
    np.copyto(forwardCV, matRollJPlus1)
    np.subtract(forwardCV, matRollJMinus1, out=forwardCV)
    np.absolute(forwardCV, out=forwardCV)
    # CL
    np.copyto(forwardCL, matRollIMinus1)
    np.subtract(forwardCL, matRollJMinus1, out=forwardCL)
    np.absolute(forwardCL, out=forwardCL)
    np.add(forwardCL, forwardCV, out=forwardCL)
    # CR
    np.copyto(forwardCR, matRollIMinus1)
    np.subtract(forwardCR, matRollJPlus1, out=forwardCR)
    np.absolute(forwardCR, out=forwardCR)
    np.add(forwardCR, forwardCV, out=forwardCR)

    # calculate left and right edges
    # CR = absolute ( I(i,1) - I(i-1,0) )
    np.copyto(forwardCR[:, 0], grayScaleMat[:, 1])
    np.subtract(forwardCR[:, 0], np.roll(grayScaleMat[:, 0], axis=0, shift=1), out=forwardCR[:, 0])
    np.absolute(forwardCR[:, 0], out=forwardCR[:, 0])

    # CL = absolute ( I(i-1,width) - I(i,width-1) )
    np.copyto(forwardCL[:, width - 1], grayScaleMat[:, width - 2])
    np.subtract(forwardCL[:, width - 1], np.roll(grayScaleMat[:, width - 1], axis=0, shift=1),
                out=forwardCL[:, width - 1])
    np.absolute(forwardCL[:, width - 1], out=forwardCL[:, width - 1])

    # add 255 to CL,CV,CR on the edges.
    forwardCL[:, width - 1] += 255
    forwardCV[:, width - 1] += 255
    forwardCV[:, 0] += 255
    forwardCR[:, 0] += 255

    return forwardCL, forwardCV, forwardCR


# function to rotate image 90 degrees clockwise
# TODO: handle the grayscale case and the image RGB case.
def rotate_image_clockwise(image: NDArray, out_height: int, out_width: int):
    return np.rot90(image, -1, (0, 1))


# function to rotate image 90 degrees counter clockwise
# TODO: handle the grayscale case and the image RGB case.
def rotate_image_counter_clockwise(image: NDArray, out_height: int, out_width: int):
    return np.rot90(image, 3, (0, 1))
