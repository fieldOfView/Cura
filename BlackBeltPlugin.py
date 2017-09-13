from UM.Extension import Extension
from UM.Application import Application
from UM.Preferences import Preferences
from UM.Resources import Resources
from UM.Logger import Logger
from UM.Message import Message

from UM.Scene.Selection import Selection
from UM.Scene.SceneNode import SceneNode
from UM.Scene.SceneNodeDecorator import SceneNodeDecorator
from UM.Math.Matrix import Matrix
from UM.Math.Vector import Vector

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

        self._application = Application.getInstance()

        splash_screen = self._application._splash
        splash_image = QPixmap(os.path.join(plugin_path, "images", "splash.png"))
        splash_screen.setPixmap(splash_image)
        splash_screen.repaint()

        self._global_container_stack = None
        self._application.globalContainerStackChanged.connect(self._onGlobalContainerStackChanged)
        self._onGlobalContainerStackChanged()

        # See if the definition that is distributed with the plugin is newer than the one in the configuration folder
        plugin_definition_path = os.path.join(plugin_path, "definitions", "blackbelt.def.json")
        config_definition_path = os.path.join(Resources.getPath(Resources.Preferences, ""), "definitions", "blackbelt.def.json")
        os.makedirs(os.path.dirname(config_definition_path), exist_ok=True)
        try:
            config_definition_mtime = os.path.getmtime(config_definition_path)
        except FileNotFoundError:
            config_definition_mtime = 0

        if config_definition_mtime < os.path.getmtime(plugin_definition_path):
            Logger.log("d", "Copying BlackBelt definition to configuration folder")
            copy2(plugin_definition_path, config_definition_path)

        self._scene_root = self._application.getController().getScene().getRoot()
        self._scene_root.addDecorator(BlackBeltDecorator())
        self._application.getBackend().slicingStarted.connect(self._onSlicingStarted)

        self._application.engineCreatedSignal.connect(self._fixPreferences)

    def _onGlobalContainerStackChanged(self):
        if self._global_container_stack:
            self._global_container_stack.propertyChanged.disconnect(self._onSettingValueChanged)
        self._global_container_stack = self._application.getGlobalContainerStack()
        if self._global_container_stack:
            self._global_container_stack.propertyChanged.connect(self._onSettingValueChanged)

            # HACK: Move blackbelt_settings to the top of the list of settings
            definition_container = self._global_container_stack.getBottom()
            if definition_container._definitions[len(definition_container._definitions) -1].key == "blackbelt_settings":
                definition_container._definitions.insert(0, definition_container._definitions.pop(len(definition_container._definitions) -1))

    def _onSlicingStarted(self):
        self._scene_root.callDecoration("calculateTransformData")

    def _onSettingValueChanged(self, key, property_name):
        if key in ["blackbelt_gantry_angle"] and property_name == "value":
            # Setting the gantry angle changes the build volume.
            # Force rebuilding the build volume by reloading the global container stack.
            # This is a bit of a hack, but it seems quick enough.
            self._application.globalContainerStackChanged.emit()

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
        self._application.expandedCategoriesChanged.emit()

## Decorator for easy access to gantry angle and transform matrix.
class BlackBeltDecorator(SceneNodeDecorator):
    def __init__(self):
        super().__init__()
        self._gantry_angle = 0
        self._transform_matrix = Matrix()
        self._scene_front = 0

    def calculateTransformData(self):
        global_stack = Application.getInstance().getGlobalContainerStack()
        machine_depth = global_stack.getProperty("machine_depth", "value")
        self._scene_front = Application.getInstance()._scene_bounding_box.front - (machine_depth / 2)

        gantry_angle = global_stack.getProperty("blackbelt_gantry_angle", "value")
        if not gantry_angle:
            self._gantry_angle = 0
            self._transform_matrix = Matrix()
            return
        self._gantry_angle = math.radians(float(gantry_angle))

        matrix_data = numpy.identity(4)
        matrix_data[2, 2] = 1/math.sin(self._gantry_angle)  # scale Z
        matrix_data[1, 2] = -1/math.tan(self._gantry_angle) # shear ZY
        matrix = Matrix(matrix_data)

        # use front buildvolume face instead of bottom face
        matrix.rotateByAxis(-math.radians(90), Vector(1,0,0))
        matrix.rotateByAxis(-math.radians(180), Vector(0,1,0))
        # bottom face has origin at the center, front face has origin at one side
        matrix.translate(Vector(0, machine_depth / 2, 0))

        self._transform_matrix = matrix

    def getGantryAngle(self):
        return self._gantry_angle

    def getTransformMatrix(self):
        return self._transform_matrix

    def getSceneFront(self):
        return self._scene_front