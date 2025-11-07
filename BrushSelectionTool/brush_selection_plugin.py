import os

from qgis.core import (
    QgsFeatureRequest,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRenderContext,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import QElapsedTimer, Qt
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import QAction


class BrushSelectionTool(QgsMapTool):
    """
    Pixel-based 'brush' selector that shows the live stroke geometry as you drag,
    but computes feature selection only on mouse release.
    - Radius is in *screen pixels* (so it behaves nicely in EPSG:4326).
    - Visual rubber band shows the buffered path in real time.
    - Selection is done once with spatially indexed bbox prefiltering.
    """

    def __init__(
        self,
        iface,
        canvas,
        radius_px=20,
        segments=8,
        add_to_selection=True,
        active_layer_only=True,
    ):
        super().__init__(canvas)
        self.iface = iface
        self.canvas = canvas
        self.radius_px = int(radius_px)  # screen pixels
        self.segments = int(segments)  # buffer segment resolution
        self.add_to_selection = add_to_selection
        self.active_layer_only = active_layer_only

        self.dragging = False
        self.path_points = []  # QgsPointXY[]
        self._last_added = None
        self.shift_pressed = False
        self.setCursor(Qt.CrossCursor)

        # Rubber band for the *stroke* (capsule buffer along path)
        self.stroke_rb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.stroke_rb.setColor(QColor(0, 150, 255, 60))  # translucent fill
        self.stroke_rb.setWidth(2)
        self.stroke_rb.setStrokeColor(QColor(0, 100, 200, 150))

        # Rubber band for the *cursor circle* at the tip (nice feedback)
        self.cursor_rb = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.cursor_rb.setColor(QColor(0, 150, 255, 80))
        self.cursor_rb.setWidth(1)
        self.cursor_rb.setStrokeColor(QColor(0, 100, 200, 180))

    # ---------- Public knobs ----------
    def setRadiusPx(self, radius_px):
        self.radius_px = max(1, int(radius_px))

    def setActiveLayerOnly(self, val: bool):
        self.active_layer_only = bool(val)

    def setAddToSelection(self, val: bool):
        self.add_to_selection = bool(val)

    # ---------- Canvas events ----------
    def canvasPressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.dragging = True
        self.shift_pressed = event.modifiers() & Qt.ShiftModifier
        self.path_points = []
        self._last_added = None
        self._append_point_if_far(event.mapPoint(), force=True)
        self._updateVisuals(event.mapPoint())

    def canvasMoveEvent(self, event):
        # Always update the visuals to show brush tip
        self._updateVisuals(event.mapPoint())

        if not self.dragging or not (event.buttons() & Qt.LeftButton):
            return

        # Record points with spacing threshold (in pixels -> map units)
        self._append_point_if_far(event.mapPoint())

        # Update the live stroke (buffered path) as you drag
        self._updateStrokeRubberBand()

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self.dragging:
            return

        self.dragging = False
        self._append_point_if_far(event.mapPoint(), force=True)

        # Build final stroke geometry and select once
        stroke_geom = self._build_stroke_geometry(
            self.path_points, self._radius_mu(), self.segments
        )
        if stroke_geom and not stroke_geom.isEmpty():
            self._select_features(stroke_geom)

        # Reset
        self.path_points = []
        self._last_added = None
        self.stroke_rb.reset(QgsWkbTypes.PolygonGeometry)

    def wheelEvent(self, event):
        """Handle mouse wheel events for radius adjustment when Shift is pressed."""
        if event.modifiers() & Qt.ShiftModifier:
            # Get wheel delta (usually ±120 per notch)
            delta = event.angleDelta().y()
            step = 2 if delta > 0 else -2
            new_radius = max(1, min(200, self.radius_px + step))

            if new_radius != self.radius_px:
                self.setRadiusPx(new_radius)

                # Update cursor circle immediately for visual feedback
                if hasattr(event, "pos"):
                    screen_pos = event.pos()
                    map_point = self.toMapCoordinates(screen_pos)
                    self._updateVisuals(map_point)

            event.accept()
            return

        # Let parent handle other wheel events
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        """Track Shift key press."""
        if event.key() == Qt.Key_Shift:
            self.shift_pressed = True
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Track Shift key release."""
        if event.key() == Qt.Key_Shift:
            self.shift_pressed = False
        super().keyReleaseEvent(event)

    def deactivate(self):
        self.stroke_rb.reset(QgsWkbTypes.PolygonGeometry)
        self.cursor_rb.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()

    # ---------- Helpers ----------
    def _radius_mu(self) -> float:
        """Convert current pixel radius to map units based on current zoom."""
        return float(self.radius_px) * self.canvas.mapUnitsPerPixel()

    def _append_point_if_far(self, map_point: QgsPointXY, force: bool = False):
        mp = map_point
        if self._last_added is None or force:
            self.path_points.append(mp)
            self._last_added = mp
            return

        # Threshold: ~2 pixels
        threshold_mu = 2.0 * self.canvas.mapUnitsPerPixel()
        if self._dist_sq(mp, self._last_added) >= threshold_mu * threshold_mu:
            self.path_points.append(mp)
            self._last_added = mp

    @staticmethod
    def _dist_sq(a: QgsPointXY, b: QgsPointXY) -> float:
        dx = a.x() - b.x()
        dy = a.y() - b.y()
        return dx * dx + dy * dy

    def _updateVisuals(self, map_point: QgsPointXY):
        """Update the cursor circle at the tip and keep stroke_rb unchanged here."""
        circle = QgsGeometry.fromPointXY(map_point).buffer(
            self._radius_mu(), max(8, self.segments)
        )
        self.cursor_rb.setToGeometry(circle, None)

    def _updateStrokeRubberBand(self):
        """Update the live *stroke* rubber band (buffered polyline)."""
        if not self.path_points:
            self.stroke_rb.reset(QgsWkbTypes.PolygonGeometry)
            return

        stroke = self._build_stroke_geometry(
            self.path_points, self._radius_mu(), self.segments
        )
        if stroke and not stroke.isEmpty():
            self.stroke_rb.setToGeometry(stroke, None)

    def _build_stroke_geometry(self, points, radius_mu, segments):
        if not points:
            return None
        try:
            if len(points) == 1:
                return QgsGeometry.fromPointXY(points[0]).buffer(
                    radius_mu, max(8, segments)
                )
            line = QgsGeometry.fromPolylineXY(points)
            return line.buffer(radius_mu, max(8, segments))
        except Exception:
            return None

    def _iter_target_layers(self):
        if self.active_layer_only:
            lyr = self.iface.activeLayer()
            if lyr and lyr.type() == lyr.VectorLayer:
                yield lyr
            return
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == layer.VectorLayer:
                yield layer

    def _select_features(self, geom: QgsGeometry):
        bbox = geom.boundingBox()
        total = 0
        layer_counts = []

        self.canvas.setRenderFlag(False)
        timer = QElapsedTimer()
        timer.start()

        for layer in self._iter_target_layers():
            req = QgsFeatureRequest().setFilterRect(bbox).setSubsetOfAttributes([])
            # Respect layer's subset string (filter) - only iterate through filtered features
            req.setFlags(QgsFeatureRequest.NoFlags)

            # Set up renderer context to check feature visibility
            renderer = layer.renderer().clone()
            context = QgsRenderContext()
            context.setExpressionContext(layer.createExpressionContext())
            renderer.startRender(context, layer.fields())

            ids = []
            for feat in layer.getFeatures(req):
                fgeom = feat.geometry()
                if not fgeom or fgeom.isEmpty():
                    continue
                if fgeom.intersects(geom):
                    # Check if feature would actually be rendered (respects categorized symbology visibility)
                    context.expressionContext().setFeature(feat)
                    if renderer.willRenderFeature(feat, context):
                        ids.append(feat.id())

            renderer.stopRender(context)

            if ids:
                should_add = self.add_to_selection or self.shift_pressed
                method = (
                    QgsVectorLayer.AddToSelection
                    if should_add
                    else QgsVectorLayer.SetSelection
                )
                layer.selectByIds(ids, method)
                layer_counts.append((layer.name(), len(ids)))
                total += len(ids)
            else:
                should_add = self.add_to_selection or self.shift_pressed
                if not should_add:
                    layer.removeSelection()
                layer_counts.append((layer.name(), len(ids)))
                total += len(ids)

        elapsed_ms = timer.elapsed()
        self.canvas.setRenderFlag(True)

        # Status
        if layer_counts:
            per_layer = ", ".join(f"{name}: {cnt}" for name, cnt in layer_counts)
            msg = f"Brush selected {total} feature(s) [{per_layer}] in {elapsed_ms} ms"
        else:
            msg = f"Brush selected 0 features in {elapsed_ms} ms"
        try:
            self.iface.mainWindow().statusBar().showMessage(msg, 5000)
        except Exception:
            pass


class BrushSelectionPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.tool = None
        self.action = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "paintbrush.png")
        self.action = QAction(
            QIcon(icon_path), "Brush Selection", self.iface.mainWindow()
        )
        self.action.setToolTip("Brush Selection - Use Shift+Scroll to change radius")
        self.action.triggered.connect(self.run)
        self.action.setCheckable(True)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.action.setChecked(False)
            self.iface.removeToolBarIcon(self.action)
            self.action = None

    def run(self):
        if self.action.isChecked():
            # Tool is being activated
            self.tool = BrushSelectionTool(
                iface=self.iface,
                canvas=self.canvas,
                radius_px=20,  # Default radius
                segments=8,
                add_to_selection=False,
                active_layer_only=True,
            )
            self.canvas.setMapTool(self.tool)
        else:
            # Tool is being deactivated
            if self.tool is not None:
                self.canvas.unsetMapTool(self.tool)
                self.tool = None
