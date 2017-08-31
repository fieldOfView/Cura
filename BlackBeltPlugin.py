from UM.Extension import Extension
from UM.Application import Application
from UM.Scene.Selection import Selection
from UM.Scene.SceneNode import SceneNode
from UM.Math.Matrix import Matrix
from UM.Math.Vector import Vector
from UM.Message import Message

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("BlackBeltPlugin")

import numpy
import math

class BlackBeltPlugin(Extension):
    def __init__(self):
        super().__init__()
        self.addMenuItem(i18n_catalog.i18n("Skew selected model(s)"), self.skewForBlackBelt)
        self.addMenuItem(i18n_catalog.i18n("Unskew selected model(s)"), self.unskewForBlackBelt)

    ##  Skews all selected objects for BlackBelt printing
    def skewForBlackBelt(self):
        selected_nodes = Selection.getAllSelectedObjects()
        if not selected_nodes:
            Message(i18n_catalog.i18nc("@info:status", "No model(s) selected to skew.")).show()
            return

        # Apply shear transformation
        transform_matrix = self.makeTransformMatrix()
        if not transform_matrix:
            Message(i18n_catalog.i18nc("@info:status", "Cannot skew model(s). Gantry angle is not set.")).show()
            return
        self.applyTransformToNodes(selected_nodes, transform_matrix)

        # Move skewed objects to the right of the buildvolume

        # Glorious hack: BlackBelt has no disallowed areas
        # This makes sure the object does not conflict with a tiny "brim" around the buildvolume (which should be 0-width but isn't)
        Application.getInstance().getBuildVolume().setDisallowedAreas([])

        build_volume_front = Application.getInstance().getBuildVolume().getBoundingBox().front
        for node in selected_nodes:
            node_front = node.getBoundingBox().front
            node.translate(Vector(0, 0, build_volume_front - node_front), SceneNode.TransformSpace.World)

    ##  Undos the skew for BalckBelt printing for all selected objects
    def unskewForBlackBelt(self):
        selected_nodes = Selection.getAllSelectedObjects()
        if not selected_nodes:
            Message(i18n_catalog.i18nc("@info:status", "No model(s) selected to unskew.")).show()
            return

        # Apply inverse of shear transformation (instead of doing a proper undo)
        transform_matrix = self.makeTransformMatrix()
        if not transform_matrix:
            Message(i18n_catalog.i18nc("@info:status", "Cannot unskew model(s). Gantry angle is not set.")).show()
            return
        self.applyTransformToNodes(selected_nodes, transform_matrix.getInverse())

    def makeTransformMatrix(self):
        global_container_stack = Application.getInstance().getGlobalContainerStack()
        gantry_angle = math.radians(float(global_container_stack.getProperty("blackbelt_gantry_angle", "value")))
        if not gantry_angle:
            return

        matrix_data = numpy.identity(4)
        matrix_data[2, 2] = 1/math.sin(gantry_angle)  # scale Z
        matrix_data[1, 2] = -1/math.tan(gantry_angle) # shear ZY
        return Matrix(matrix_data)

    def applyTransformToNodes(self, nodes, transform):
        for node in nodes:
            matrix = node.getLocalTransformation().multiply(transform)
            node.setTransformation(matrix)