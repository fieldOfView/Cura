// Copyright (c) 2017 Ultimaker B.V.
// Cura is released under the terms of the LGPLv3 or higher.

import QtQuick 2.2
import QtQuick.Controls 1.1
import QtQuick.Controls.Styles 1.1

import UM 1.2 as UM
import Cura 1.0 as Cura

import "Menus"
import "Preferences"

Column
{
    id: base;

    property int currentExtruderIndex: ExtruderManager.activeExtruderIndex;
    property bool currentExtruderVisible: extrudersList.visible;

    spacing: Math.floor(UM.Theme.getSize("sidebar_margin").width * 0.9)

    signal showTooltip(Item item, point location, string text)
    signal hideTooltip()

    Item
    {
        anchors
        {
            left: parent.left
            right: parent.right
        }
        visible: extruderSelectionRow.visible
        height: UM.Theme.getSize("default_lining").height
        width: height
    }

    Item
    {
        anchors
        {
            left: parent.left
            leftMargin: UM.Theme.getSize("sidebar_margin").width
            right: parent.right
            rightMargin: UM.Theme.getSize("sidebar_margin").width
        }
        visible: extruderSelectionRow.visible
        height: UM.Theme.getSize("default_lining").hieght
        width: height
    }

    Item
    {
        id: extruderSelectionRow
        width: parent.width
        height: Math.floor(UM.Theme.getSize("sidebar_tabs").height * 2 / 3)
        visible: machineExtruderCount.properties.value > 1 && !sidebar.monitoringPrint

        anchors
        {
            left: parent.left
            leftMargin: Math.floor(UM.Theme.getSize("sidebar_margin").width * 0.7)
            right: parent.right
            rightMargin: Math.floor(UM.Theme.getSize("sidebar_margin").width * 0.7)
            topMargin: UM.Theme.getSize("sidebar_margin").height
        }

        ListView
        {
            id: extrudersList
            property var index: 0
            height: UM.Theme.getSize("sidebar_header_mode_tabs").height
            width: Math.floor(parent.width)
            boundsBehavior: Flickable.StopAtBounds
            anchors
            {
                left: parent.left
                leftMargin: Math.floor(UM.Theme.getSize("default_margin").width / 2)
                right: parent.right
                rightMargin: Math.floor(UM.Theme.getSize("default_margin").width / 2)
                verticalCenter: parent.verticalCenter
            }

            ExclusiveGroup { id: extruderMenuGroup; }

            orientation: ListView.Horizontal

            model: Cura.ExtrudersModel { id: extrudersModel; addGlobal: false }

            Connections
            {
                target: Cura.MachineManager
                onGlobalContainerChanged: forceActiveFocus() // Changing focus applies the currently-being-typed values so it can change the displayed setting values.
            }

            delegate: Button
            {
                height: ListView.view.height
                width: ListView.view.width / extrudersModel.rowCount()

                text: model.name
                tooltip: model.name
                exclusiveGroup: extruderMenuGroup
                checked: base.currentExtruderIndex == index

                onClicked:
                {
                    forceActiveFocus() // Changing focus applies the currently-being-typed values so it can change the displayed setting values.
                    ExtruderManager.setActiveExtruderIndex(index);
                }

                style: ButtonStyle
                {
                    background: Item
                    {
                        Rectangle
                        {
                            anchors.fill: parent
                            border.width: control.checked ? UM.Theme.getSize("default_lining").width * 2 : UM.Theme.getSize("default_lining").width
                            border.color: (control.checked || control.pressed) ? UM.Theme.getColor("action_button_active_border") :
                                          control.hovered ? UM.Theme.getColor("action_button_hovered_border") :
                                          UM.Theme.getColor("action_button_border")
                            color: (control.checked || control.pressed) ? UM.Theme.getColor("action_button_active") :
                                   control.hovered ? UM.Theme.getColor("action_button_hovered") :
                                   UM.Theme.getColor("action_button")
                            Behavior on color { ColorAnimation { duration: 50; } }
                        }

                        Item
                        {
                            id: extruderButtonFace
                            anchors.centerIn: parent
                            width: {
                                var extruderTextWidth = extruderStaticText.visible ? extruderStaticText.width : 0;
                                var iconWidth = extruderIconItem.width;
                                return Math.floor(extruderTextWidth + iconWidth + UM.Theme.getSize("default_margin").width / 2);
                            }

                            // Static text "Extruder"
                            Label
                            {
                                id: extruderStaticText
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left

                                color: (control.checked || control.pressed) ? UM.Theme.getColor("action_button_active_text") :
                                       control.hovered ? UM.Theme.getColor("action_button_hovered_text") :
                                       UM.Theme.getColor("action_button_text")

                                font: UM.Theme.getFont("large_nonbold")
                                text: catalog.i18nc("@label", "Extruder")
                                visible: width < (control.width - extruderIconItem.width - UM.Theme.getSize("default_margin").width)
                                elide: Text.ElideRight
                            }

                            // Everthing for the extruder icon
                            Item
                            {
                                id: extruderIconItem
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.right: parent.right

                                property var sizeToUse:
                                {
                                    var minimumWidth = control.width < UM.Theme.getSize("button").width ? control.width : UM.Theme.getSize("button").width;
                                    var minimumHeight = control.height < UM.Theme.getSize("button").height ? control.height : UM.Theme.getSize("button").height;
                                    var minimumSize = minimumWidth < minimumHeight ? minimumWidth : minimumHeight;
                                    minimumSize -= Math.floor(UM.Theme.getSize("default_margin").width / 2);
                                    return minimumSize;
                                }

                                width: sizeToUse
                                height: sizeToUse

                                UM.RecolorImage {
                                    id: mainCircle
                                    anchors.fill: parent

                                    sourceSize.width: parent.width
                                    sourceSize.height: parent.width
                                    source: UM.Theme.getIcon("extruder_button")

                                    color: extruderNumberText.color
                                }

                                Label
                                {
                                    id: extruderNumberText
                                    anchors.centerIn: parent
                                    text: index + 1;
                                    color: (control.checked || control.pressed) ? UM.Theme.getColor("action_button_active_text") :
                                           control.hovered ? UM.Theme.getColor("action_button_hovered_text") :
                                           UM.Theme.getColor("action_button_text")
                                    font: UM.Theme.getFont("default_bold")
                                }

                                // Material colour circle
                                // Only draw the filling colour of the material inside the SVG border.
                                Rectangle
                                {
                                    anchors
                                    {
                                        right: parent.right
                                        top: parent.top
                                        rightMargin: parent.sizeToUse * 0.01
                                        topMargin: parent.sizeToUse * 0.05
                                    }

                                    color: model.color

                                    width: parent.width * 0.35
                                    height: parent.height * 0.35
                                    radius: width / 2

                                    border.width: 1
                                    border.color: UM.Theme.getColor("extruder_button_material_border")

                                    opacity: !control.checked ? 0.6 : 1.0
                                }
                            }
                        }
                    }
                    label: Item {}
                }
            }
        }
    }

    Item
    {
        id: variantRowSpacer
        height: UM.Theme.getSize("sidebar_margin").height / 4
        width: height
        visible: !extruderSelectionRow.visible
    }

    Row
    {
        id: categoryRow

        height: UM.Theme.getSize("sidebar_setup").height
        visible: Cura.MachineManager.hasMaterials && !sidebar.monitoringPrint && !sidebar.hideSettings

        anchors
        {
            left: parent.left
            leftMargin: UM.Theme.getSize("sidebar_margin").width
            right: parent.right
            rightMargin: UM.Theme.getSize("sidebar_margin").width
        }

        Label
        {
            id: categoryLabel
            text: "Category"

            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * 0.45 - UM.Theme.getSize("sidebar_margin").width
            font: UM.Theme.getFont("default");
            color: UM.Theme.getColor("text");
        }

        ToolButton {
            id: categorySelection
            text: Cura.MachineManager.currentCategory
            tooltip: Cura.MachineManager.currentCategory
            anchors.verticalCenter: parent.verticalCenter

            height: UM.Theme.getSize("setting_control").height
            width: parent.width * 0.55 + UM.Theme.getSize("sidebar_margin").width
            style: UM.Theme.styles.sidebar_header_button
            activeFocusOnPress: true;

            menu: CategoryMenu {}
        }
    }

    Row
    {
        id: materialRow
        height: UM.Theme.getSize("sidebar_setup").height
        visible: Cura.MachineManager.hasMaterials && !sidebar.monitoringPrint && !sidebar.hideSettings

        anchors
        {
            left: parent.left
            leftMargin: UM.Theme.getSize("sidebar_margin").width
            right: parent.right
            rightMargin: UM.Theme.getSize("sidebar_margin").width
        }

        Label
        {
            id: materialLabel
            text: catalog.i18nc("@label","Material");
            width: parent.width * 0.45 - UM.Theme.getSize("sidebar_margin").width
            font: UM.Theme.getFont("default");
            color: UM.Theme.getColor("text");
        }

        ToolButton {
            id: materialSelection
            text: Cura.MachineManager.activeMaterialName
            tooltip: Cura.MachineManager.activeMaterialName
            visible: Cura.MachineManager.hasMaterials
            property var valueError:
            {
                var data = Cura.ContainerManager.getContainerMetaDataEntry(Cura.MachineManager.activeMaterialId, "compatible")
                if(data == "False")
                {
                    return true
                }
                else
                {
                    return false
                }
                return "%1:".arg(label)
            }
            style: UM.Theme.styles.sidebar_header_button
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * 0.55 + UM.Theme.getSize("sidebar_margin").width
            menu: MaterialMenu { extruderIndex: base.currentExtruderIndex }
        }
    }

    Row
    {
        id: adhesionRow

        height: UM.Theme.getSize("sidebar_setup").height*4
        visible: (Cura.MachineManager.hasVariants || Cura.MachineManager.hasMaterials) && !sidebar.monitoringPrint && !sidebar.hideSettings


        anchors
        {
            left: parent.left
            leftMargin: UM.Theme.getSize("sidebar_margin").width
            right: parent.right
            rightMargin: UM.Theme.getSize("sidebar_margin").width
        }

        Label
        {
            height: parent.rowHeight;
            verticalAlignment: Qt.AlignVCenter;
            text: catalog.i18nc("@label", "Adhesion Info")

            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * 0.45 - UM.Theme.getSize("sidebar_margin").width
            font: UM.Theme.getFont("default");
            color: UM.Theme.getColor("text");
        }

        ReadOnlyTextArea
        {
            //text: properties.adhesion_info;
            // TODO: need fill and data to/from somewhere???
            text: ""
            wrapMode: Text.WordWrap;
            readOnly: false;
            visible: true;

            width: parent.width * 0.55 + UM.Theme.getSize("sidebar_margin").width
            height: parent.height;
            txtFont: UM.Theme.getFont("default");

            // TODO: need fill and data to/from somewhere???
            //onEditingFinished: base.setMetaDataEntry("adhesion_info", properties.adhesion_info, text)
        }

    }

    Row
    {
        id: printCoreRow
        height: UM.Theme.getSize("sidebar_setup").height
        visible: Cura.MachineManager.hasVariants && !sidebar.monitoringPrint && !sidebar.hideSettings

        anchors
        {
            left: parent.left
            leftMargin: UM.Theme.getSize("sidebar_margin").width
            right: parent.right
            rightMargin: UM.Theme.getSize("sidebar_margin").width
        }

        Label
        {
            id: printCoreLabel
            text: Cura.MachineManager.activeDefinitionVariantsName;
            width: parent.width * 0.45 - UM.Theme.getSize("sidebar_margin").width
            font: UM.Theme.getFont("default");
            color: UM.Theme.getColor("text");
        }

        ToolButton {
            id: printCoreSelection
            text: Cura.MachineManager.activeVariantName
            tooltip: Cura.MachineManager.activeVariantName;
            visible: Cura.MachineManager.hasVariants

            height: UM.Theme.getSize("setting_control").height
            width: parent.width * 0.55 + UM.Theme.getSize("sidebar_margin").width
            style: UM.Theme.styles.sidebar_header_button
            activeFocusOnPress: true;

            menu: NozzleMenu { extruderIndex: base.currentExtruderIndex }
        }
    }

    // Material info row
    Item
    {
        id: materialInfoRow
        height: Math.floor(UM.Theme.getSize("sidebar_setup").height / 2)
        visible: (Cura.MachineManager.hasVariants || Cura.MachineManager.hasMaterials) && !sidebar.monitoringPrint && !sidebar.hideSettings && Cura.MachineManager.currentMaterialHasInfo

        anchors
        {
            left: parent.left
            leftMargin: UM.Theme.getSize("sidebar_margin").width
            right: parent.right
            rightMargin: UM.Theme.getSize("sidebar_margin").width
        }

        Item {
            height: UM.Theme.getSize("sidebar_setup").height
            anchors.right: parent.right
            width: Math.floor(parent.width * 0.7 + UM.Theme.getSize("sidebar_margin").width)

            UM.RecolorImage {
                id: warningImage
                anchors.right: materialInfoLabel.left
                anchors.rightMargin: UM.Theme.getSize("default_margin").width
                anchors.verticalCenter: parent.Bottom
                source: UM.Theme.getIcon("warning")
                width: UM.Theme.getSize("section_icon").width
                height: UM.Theme.getSize("section_icon").height
                color: UM.Theme.getColor("material_compatibility_warning")
                visible: !Cura.MachineManager.isCurrentSetupSupported
            }

            Label {
                id: materialInfoLabel
                wrapMode: Text.WordWrap
                text: catalog.i18nc("@label", "<a href='%1'>Material info</a>")
                font: UM.Theme.getFont("default")
                color: UM.Theme.getColor("text")
                linkColor: UM.Theme.getColor("text_link")
                verticalAlignment: Text.AlignTop
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.bottom: parent.bottom

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        Cura.MachineManager.openCurrentMaterialInfo()
                    }
                }
            }
        }
    }


    UM.SettingPropertyProvider
    {
        id: machineExtruderCount

        containerStackId: Cura.MachineManager.activeMachineId
        key: "machine_extruder_count"
        watchedProperties: [ "value" ]
        storeIndex: 0
    }

    UM.I18nCatalog { id: catalog; name:"cura" }
}
