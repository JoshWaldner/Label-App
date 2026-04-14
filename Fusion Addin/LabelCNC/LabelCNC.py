import math
import re
from .lib import fusionAddInUtils as futil
import adsk.core
from os.path import join as OPJ
import json
from datetime import datetime

# import qrcode as qrcode
import os
import adsk.fusion
import adsk.cam
import traceback


app = adsk.core.Application.get()
ui = app.userInterface
# TODO *** Specify the command identity information. ***
CMD_ID = "LabelCNC_cmdDialog"  # Unique ID for the command, used to reference the command in the UI and in the code
CMD_NAME = "LabelCNC"  # Name of the command that will appear in the UI
CMD_Description = ""  # Add a description of the add-in
IS_PROMOTED = True
WORKSPACE_ID = "CAMEnvironment"
PANEL_ID = "MillingTab"
TOOLBAR_PANEL = "CAMActionPanel"
COMMAND_BESIDE_ID = ""
Size = 2.54
SelectedDefault = 0
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "")
resourcePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
BrowseIcon = os.path.join(resourcePath, "Browse")
FilePath = os.path.expanduser("~/Desktop/LabelCNCApp/Data")


local_handlers = []


def run(context):
    try:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER
        )
        futil.add_handler(cmd_def.commandCreated, command_created)
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(TOOLBAR_PANEL)
        control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
        control.isPromoted = IS_PROMOTED
        # start()

    except:
        futil.handle_error("run")


def stop(context):
    try:
        # Remove all of the event handlers your app has created
        futil.clear_handlers()
        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(TOOLBAR_PANEL)
        command_control = panel.controls.itemById(CMD_ID)
        command_definition = ui.commandDefinitions.itemById(CMD_ID)

        # Delete the button command control
        if command_control:
            command_control.deleteMe()

        # Delete the command definition
        if command_definition:
            command_definition.deleteMe()
        # This will run the start function in each of your commands as defined in commands/__init__.py
        # stop()

    except:
        futil.handle_error("stop")


def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f"{CMD_NAME} Command Created Event")

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs
    OutputFolder = inputs.addStringValueInput("LabelsOutput", "Output Folder", FilePath)
    OutputFolder.isEnabled = False
    OutputFolderButton = inputs.addBoolValueInput("BrowseLabelOutput", "Browse", False)
    OutputFolderButton.resourceFolder = BrowseIcon
    OutputFolderButton.tooltip = "Browse for Output Folder"


    # TODO Connect to the events that are needed by this command.
    futil.add_handler(
        args.command.execute, command_execute, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.inputChanged, command_input_changed, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.executePreview, command_preview, local_handlers=local_handlers
    )
    futil.add_handler(
        args.command.validateInputs,
        command_validate_input,
        local_handlers=local_handlers,
    )
    futil.add_handler(
        args.command.destroy, command_destroy, local_handlers=local_handlers
    )


# This event handler is called when the user clicks the OK button in the command dialog or
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    try:
        # General logging for debug.
        futil.log(f"{CMD_NAME} Command Execute Event")
        inputs = args.command.commandInputs
        SaveFolder = inputs.itemById("LabelsOutput").value
        Export_svg_dataset(SaveFolder)
    except:
        ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


# This event handler is called when the command needs to compute a new preview in the graphics window.
def command_preview(args: adsk.core.CommandEventArgs):
    pass


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    try:
        input = args.input
        inputs = args.inputs
        ui = app.userInterface
        # CamInputs = ToolBox.GetInputs(inputs)
        if input.id == "BrowseLabelOutput":
            dialog = ui.createFolderDialog()
            dialog.initialDirectory = ""
            dialog.title = "Select output folder"
            if dialog.showDialog() == adsk.core.DialogResults.DialogOK:
                pathToSave = inputs.itemById("LabelsOutput").value = dialog.folder

            inputs.itemById("BrowseLabelOutput").value = False
            global FilePath
            FilePath = pathToSave

    except:
        ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    # futil.log(f'{CMD_NAME} Validate Input Event')

    inputs = args.inputs

    # Verify the validity of the input values. This controls if the OK button is enabled or not.


# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    # futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    local_handlers = []


def Export_svg_dataset(base_path: str):
    """Export SVG files for all setups, organized in a folder structure
    under ``base_path``.  This is intended for use as a dataset for training
    machine learning models, and is not expected to be human‑readable.
    """
    doc = adsk.core.Application.get().activeDocument
    cam = adsk.cam.CAM.cast(doc.products.itemByProductType("CAMProductType"))
    for setup in cam.setups:
        LocalWCS = setup.workCoordinateSystem
        SortedFaces = faceEvaluator(setup)
        bounds = setup.stockSolids.item(0).boundingBox

        dims = _get_stock_points(bounds)
        Path = _get_svg_path(base_path, doc.name, setup.name, bounds.maxPoint.z)
        data = _get_data(setup=setup)
        parts = _get_parts_data(setup=setup, faces=SortedFaces)
        # fullModel = _get_full_model()

        data["parts"] = parts
        with open(Path, "w") as f:

            json.dump(data, f, indent=4)


def _get_stock_points(bounds):
    z0 = bounds.minPoint.z
    return [
        adsk.core.Point3D.create(bounds.minPoint.x, bounds.minPoint.y, z0),
        adsk.core.Point3D.create(bounds.maxPoint.x, bounds.minPoint.y, z0),
        adsk.core.Point3D.create(bounds.maxPoint.x, bounds.maxPoint.y, z0),
        adsk.core.Point3D.create(bounds.minPoint.x, bounds.maxPoint.y, z0),
    ]


def _get_svg_path(base, doc_name, setup_name, dims):
    doc_name = re.sub(r"v\d{1,}", "", doc_name).strip()
    setup_name = setup_name.strip()
    folder = OPJ(os.path.normpath(base.strip()), doc_name)
    os.makedirs(folder, exist_ok=True)
    filename = f"{doc_name} {setup_name} ({round(dims/2.54, 2)}in).json"
    return OPJ(folder, filename)


def _get_data(setup):
    bounds = setup.stockSolids.item(0).boundingBox
    stock_points = _get_stock_points(bounds)
    minX, minY = bounds.minPoint.x, bounds.minPoint.y
    dim = _get_stock_dimensions(bounds)
    return {
        "stock": [
            {
                "name": setup.name,
                "Date": f"{datetime.now().date()} {datetime.now().time()}",
                "points": [
                    {
                        "x": round(stock_points[0].x - minX, 2),
                        "y": round((-stock_points[0].y + dim[1] * 2.54) + minY, 2),
                    },
                    {
                        "x": round(stock_points[1].x - minX, 2),
                        "y": round((-stock_points[1].y + dim[1] * 2.54) + minY, 2),
                    },
                    {
                        "x": round(stock_points[2].x - minX, 2),
                        "y": round((-stock_points[2].y + dim[1] * 2.54) + minY, 2),
                    },
                    {
                        "x": round(stock_points[3].x - minX, 2),
                        "y": round((-stock_points[3].y + dim[1] * 2.54) + minY, 2),
                    },
                ],
            }
        ],
    }


def _get_parts_data(setup: adsk.cam.Setup, faces):
    parts = []
    if isinstance(faces, dict):
        BottomFace = faces.get("bottom_face")
        MiterFace = (
            faces.get("miter_long", [])
            + faces.get("miter_short", [])
            + faces.get("miter_mill", [])
        )
        Milling = faces.get("flat_mill_big", []) + faces.get("flat_mill_small", [])
    else:
        BottomFace = getattr(faces, "bottom_face", [])
        MiterFace = (
            getattr(faces, "miter_long", [])
            + getattr(faces, "miter_short", [])
            + getattr(faces, "miter_mill", [])
        )
        Milling = getattr(faces, "flat_mill_big", []) + getattr(
            faces, "flat_mill_small", []
        )

    if BottomFace is None:
        BottomFace = []
    elif not hasattr(BottomFace, "__iter__") or isinstance(
        BottomFace, adsk.fusion.BRepFace
    ):
        BottomFace = [BottomFace]

    bounds = setup.stockSolids.item(0).boundingBox
    dim = _get_stock_dimensions(bounds)
    minX, minY = bounds.minPoint.x, bounds.minPoint.y

    for face in BottomFace:
        outer_loop = []
        holes = []
        miter = []
        mill = []

        for loop in face.loops:
            loop_points = _gen_points(loop, face.body)
            points = [
                {
                    "x": round(p.x - minX, 2),
                    "y": round((-p.y + dim[1] * 2.54) + minY, 2),
                }
                for p in loop_points
            ]

            if loop.isOuter:
                outer_loop = points

            else:
                holes.append(
                    [
                        {
                            "x": round(p.x - minX, 2),
                            "y": round((-p.y + dim[1] * 2.54) + minY, 2),
                        }
                        for p in loop_points
                    ]
                )

        for miter_face in MiterFace:
            if miter_face in face.body.faces:
                for loop in miter_face.loops:
                    miter.append(
                        [
                            {
                                "x": round(p.x - minX, 2),
                                "y": round((-p.y + dim[1] * 2.54) + minY, 2),
                            }
                            for p in _gen_points(loop, miter_face.body)
                        ]
                    )

        for mill_face in Milling:
            if mill_face in face.body.faces:
                for loop in mill_face.loops:
                    mill.append(
                        [
                            {
                                "x": round(p.x - minX, 2),
                                "y": round((-p.y + dim[1] * 2.54) + minY, 2),
                            }
                            for p in _gen_points(loop, mill_face.body)
                        ]
                    )

        parts.append(
            {
                "name": face.body.parentComponent.name.replace("Component", "").strip(),
                "geometry": {"outer": outer_loop, "holes": holes},
                "operations": {"miter": miter, "mill": mill},
            }
        )

    return parts


def _get_stock_dimensions(bounds):
    return tuple(
        round(
            (getattr(bounds.maxPoint, axis) - getattr(bounds.minPoint, axis)) / 2.54, 2
        )
        for axis in ("x", "y", "z")
    )


def _gen_points(loop: adsk.fusion.BRepLoop, body: adsk.fusion.BRepBody):
    pts_out, last = [], None
    for coedge in loop.coEdges:
        pts = _sample_edge(coedge.edge)
        if coedge.isOpposedToEdge:
            pts.reverse()
        for p in pts:
            if last is None or last.distanceTo(p) > 0.01:
                pts_out.append(p)
                last = p
    return pts_out


def _sample_edge(edge):
    eval = edge.evaluator
    ok, start, end = eval.getParameterExtents()
    if not ok:
        return []
    if isinstance(edge.geometry, adsk.core.Line3D):
        pts = []
        for t in (start, end):
            ok, p = eval.getPointAtParameter(t)
            if ok and p:
                pts.append(p)
        return pts
    segs = 50
    step = (end - start) / segs
    pts = []
    for i in range(segs + 1):
        t = end if i == segs else start + i * step
        try:
            ok, p = eval.getPointAtParameter(t)
        except Exception:
            continue
        if ok and p:
            pts.append(p)
    return pts


def faceEvaluator(setup: adsk.cam.Setup):
    faces = setup.stockSolids.item(0).faces
    bottom_face = None
    miter_long = []
    miter_short = []
    miter_mill = []
    flat_mill_big = []
    flat_mill_small = []

    for face in faces:
        if isinstance(face.geometry, adsk.core.Plane):
            if not bottom_face:
                bottom_face = face
            elif face.geometry.normal.isParallelTo(bottom_face.geometry.normal):
                if face.area > bottom_face.area * 0.5:
                    miter_long.append(face)
                else:
                    miter_short.append(face)
            else:
                if face.area > bottom_face.area * 0.5:
                    flat_mill_big.append(face)
                else:
                    flat_mill_small.append(face)
        else:
            miter_mill.append(face)

    return {
        "bottom_face": bottom_face,
        "miter_long": miter_long,
        "miter_short": miter_short,
        "miter_mill": miter_mill,
        "flat_mill_big": flat_mill_big,
        "flat_mill_small": flat_mill_small,
    }
