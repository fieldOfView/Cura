from UM.Extension import Extension
from UM.Application import Application
from UM.Preferences import Preferences
from UM.Resources import Resources
from UM.Logger import Logger

from UM.Scene.Selection import Selection
from UM.Scene.SceneNode import SceneNode
from UM.Math.Matrix import Matrix
from UM.Math.Vector import Vector
from UM.Message import Message

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("BlackBeltPlugin")

from PyQt5.QtGui import QPixmap

import numpy
import math
import os.path
from shutil import copy2

class BlackBeltPlugin(Extension):
    def __init__(self):
        super().__init__()
        plugin_path = os.path.dirname(os.path.abspath(__file__))

        self.addMenuItem(i18n_catalog.i18n("Skew selected model(s)"), self.skewForBlackBelt)
        self.addMenuItem(i18n_catalog.i18n("Unskew selected model(s)"), self.unskewForBlackBelt)

        splash_screen = Application.getInstance()._splash
        splash_image = QPixmap(os.path.join(plugin_path, "images", "splash.png"))
        splash_screen.setPixmap(splash_image.scaled(splash_image.size() * splash_screen._scale))
        splash_screen.repaint()

        self._global_container_stack = None
        self._preferences_fixed = False
        Application.getInstance().globalContainerStackChanged.connect(self._onGlobalContainerStackChanged)
        self._onGlobalContainerStackChanged()

        # See if the definition that is distributed with the plugin is newer than the one in the configuration folder
        plugin_definition_path = os.path.join(plugin_path, "definitions", "blackbelt.def.json")
        config_definition_path = os.path.join(Resources.getStoragePath(Resources.DefinitionContainers), "blackbelt.def.json")
        try:
            config_definition_mtime = os.path.getmtime(config_definition_path)
        except FileNotFoundError:
            config_definition_mtime = 0

        if config_definition_mtime < os.path.getmtime(plugin_definition_path):
            Logger.log("d", "Copying BlackBelt definition to configuration folder")
            copy2(plugin_definition_path, config_definition_path)

    def _onGlobalContainerStackChanged(self):
        if not self._preferences_fixed:
            # This is run only once, but is delayed from __init__ because it does not work otherwise
            self._fixPreferences()

        if self._global_container_stack:
            self._global_container_stack.propertyChanged.disconnect(self._onSettingValueChanged)
        self._global_container_stack = Application.getInstance().getGlobalContainerStack()
        if self._global_container_stack:
            self._global_container_stack.propertyChanged.connect(self._onSettingValueChanged)

            # HACK: Move blackbelt_settings to the top of the list of settings
            definition_container = self._global_container_stack.getBottom()
            if definition_container._definitions[len(definition_container._definitions) -1].key == "blackbelt_settings":
                definition_container._definitions.insert(0, definition_container._definitions.pop(len(definition_container._definitions) -1))

    def _onSettingValueChanged(self, key, property_name):
        if key in ["blackbelt_gantry_angle"] and property_name == "value":
            # Setting the gantry angle changes the build volume.
            # Force rebuilding the build volume by reloading the global container stack.
            # This is a bit of a hack, but it seems quick enough.
            Application.getInstance().globalContainerStackChanged.emit()

    def _fixPreferences(self):
        preferences = Preferences.getInstance()
        visible_settings = preferences.getValue("general/visible_settings")
        if not visible_settings:
            # Wait until the default visible settings have been set
            return

        visible_settings_changed = False
        for key in ["blackbelt_settings", "blackbelt_gantry_angle", "blackbelt_nozzle_size"]:
            if key not in visible_settings:
                visible_settings += ";%s" % key
                visible_settings_changed = True

        if not visible_settings_changed:
            return

        preferences.setValue("general/visible_settings", visible_settings)

        expanded_settings = preferences.getValue("cura/categories_expanded")
        if expanded_settings is None:
            expanded_settings = ""
        for key in ["blackbelt_settings"]:
            if key not in expanded_settings:
                expanded_settings += ";%s" % key
        preferences.setValue("cura/categories_expanded", expanded_settings)

        self._preferences_fixed = True


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
        gantry_angle = math.radians(float(self._global_container_stack.getProperty("blackbelt_gantry_angle", "value")))
        if not gantry_angle:
            return

        matrix_data = numpy.identity(4)
        matrix_data[2, 2] = 1/math.sin(gantry_angle)  # scale Z
        matrix_data[1, 2] = -1/math.tan(gantry_angle) # shear ZY
        return Matrix(matrix_data)

    def applyTransformToNodes(self, nodes, transform):
        for node in nodes:
            matrix = node.getLocalTransformation().preMultiply(transform)
            node.setTransformation(matrix)