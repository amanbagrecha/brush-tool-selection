from qgis.PyQt.QtCore import Qt, QPoint, QElapsedTimer
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QAction, QSlider, QLabel, QHBoxLayout, QWidget
from qgis.core import (
    QgsProject,
    QgsGeometry,
    QgsPointXY,
    QgsWkbTypes,
    QgsFeatureRequest,
    QgsRectangle,
    QgsCoordinateTransformContext,
)
from qgis.gui import QgsMapTool, QgsRubberBand


class BrushSelectionTool(QgsMapTool):
    """
    Pixel-based 'brush' selector that shows the live stroke geometry as you drag,
    but computes feature selection only on mouse release.
    - Radius is in *screen pixels* (so it behaves nicely in EPSG:4326).
    - Visual rubber band shows the buffered path in real time.
    - Selection is done once with spatially indexed bbox prefiltering.
    """

    def __init__(self, iface, canvas, radius_px=20, segments=8, add_to_selection=True, active_layer_only=True):
        super().__init__(canvas)
        self.iface = iface
        self.canvas = canvas
        self.radius_px = int(radius_px)  # screen pixels
        self.segments = int(segments)    # buffer segment resolution
        self.add_to_selection = add_to_selection
        self.active_layer_only = active_layer_only

        self.dragging = False
        self.path_points = []  # QgsPointXY[]
        self._last_added = None
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
        self.path_points = []
        self._last_added = None
        self._append_point_if_far(event.pos(), force=True)
        self._updateVisuals(event.pos())

    def canvasMoveEvent(self, event):
        # Always update the visuals to show brush tip
        self._updateVisuals(event.pos())

        if not self.dragging or not (event.buttons() & Qt.LeftButton):
            return

        # Record points with spacing threshold (in pixels -> map units)
        self._append_point_if_far(event.pos())

        # Update the live stroke (buffered path) as you drag
        self._updateStrokeRubberBand()

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self.dragging:
            return

        self.dragging = False
        self._append_point_if_far(event.pos(), force=True)

        # Build final stroke geometry and select once
        stroke_geom = self._build_stroke_geometry(self.path_points, self._radius_mu(), self.segments)
        if stroke_geom and not stroke_geom.isEmpty():
            self._select_features(stroke_geom)

        # Reset
        self.path_points = []
        self._last_added = None
        self.stroke_rb.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self):
        self.stroke_rb.reset(QgsWkbTypes.PolygonGeometry)
        self.cursor_rb.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()

    # ---------- Helpers ----------
    def _radius_mu(self) -> float:
        """Convert current pixel radius to map units based on current zoom."""
        return float(self.radius_px) * self.canvas.mapUnitsPerPixel()

    def _map_point(self, screen_pt: QPoint) -> QgsPointXY:
        return self.toMapCoordinates(screen_pt)

    def _append_point_if_far(self, screen_pt: QPoint, force: bool = False):
        mp = self._map_point(screen_pt)
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

    def _updateVisuals(self, screen_pt: QPoint):
        """Update the cursor circle at the tip and keep stroke_rb unchanged here."""
        mp = self._map_point(screen_pt)
        circle = QgsGeometry.fromPointXY(mp).buffer(self._radius_mu(), max(8, self.segments))
        self.cursor_rb.setToGeometry(circle, None)

    def _updateStrokeRubberBand(self):
        """Update the live *stroke* rubber band (buffered polyline)."""
        if not self.path_points:
            self.stroke_rb.reset(QgsWkbTypes.PolygonGeometry)
            return

        stroke = self._build_stroke_geometry(self.path_points, self._radius_mu(), self.segments)
        if stroke and not stroke.isEmpty():
            self.stroke_rb.setToGeometry(stroke, None)

    def _build_stroke_geometry(self, points, radius_mu, segments):
        if not points:
            return None
        try:
            if len(points) == 1:
                return QgsGeometry.fromPointXY(points[0]).buffer(radius_mu, max(8, segments))
            line = QgsGeometry.fromPolylineXY(points)
            return line.buffer(radius_mu, max(8, segments))
        except Exception:
            return None

    def _iter_target_layers(self):
        if self.active_layer_only:
            lyr = self.iface.activeLayer()
            if lyr and lyr.type() == lyr.VectorLayer and lyr.geometryType() == QgsWkbTypes.PolygonGeometry:
                yield lyr
            return
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == layer.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                yield layer

    def _select_features(self, geom: QgsGeometry):
        bbox = geom.boundingBox()
        total = 0
        layer_counts = []

        self.canvas.setRenderFlag(False)
        timer = QElapsedTimer()
        timer.start()

        for layer in self._iter_target_layers():
            req = (
                QgsFeatureRequest()
                .setFilterRect(QgsRectangle(bbox))
                .setSubsetOfAttributes([])
            )

            ids = []
            for feat in layer.getFeatures(req):
                fgeom = feat.geometry()
                if not fgeom or fgeom.isEmpty():
                    continue
                if fgeom.intersects(geom):
                    ids.append(feat.id())

            if ids:
                method = layer.AddToSelection if self.add_to_selection else layer.SetSelection
                layer.selectByIds(ids, method)
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
        self.radius_slider = None
        self.toolbar = None
        self.active_only_label = None

    def initGui(self):
        self.action = QAction(QIcon(), "Brush Selection Tool (fast, px)", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.action.setCheckable(True)

        self.toolbar = self.iface.addToolBar("Brush Selection (fast, px)")
        self.toolbar.addAction(self.action)

        # Radius control (pixels)
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(6, 2, 6, 2)
        layout.addWidget(QLabel("Radius (px):"))

        self.radius_slider = QSlider(Qt.Horizontal)
        self.radius_slider.setMinimum(1)
        self.radius_slider.setMaximum(200)  # pixel radius range
        self.radius_slider.setValue(20)
        self.radius_slider.valueChanged.connect(self.radiusChanged)

        self.radius_label = QLabel("20 px")
        layout.addWidget(self.radius_slider)
        layout.addWidget(self.radius_label)

        widget.setLayout(layout)
        self.toolbar.addWidget(widget)

        # Hint: active layer only
        self.active_only_label = QLabel("Active layer only")
        self.active_only_label.setToolTip("Selection is performed on the active polygon layer for speed. "
                                          "Change via tool.setActiveLayerOnly(False) if needed.")
        self.toolbar.addWidget(self.active_only_label)

    def unload(self):
        if self.toolbar:
            try:
                self.iface.mainWindow().removeToolBar(self.toolbar)
            except Exception:
                pass
            self.toolbar = None
        if self.action:
            self.action.setChecked(False)
            self.action = None

    def run(self):
        if self.action.isChecked():
            self.tool = BrushSelectionTool(
                iface=self.iface,
                canvas=self.canvas,
                radius_px=self.radius_slider.value(),
                segments=8,
                add_to_selection=True,
                active_layer_only=True,
            )
            self.canvas.setMapTool(self.tool)
        else:
            if self.tool is not None:
                self.canvas.unsetMapTool(self.tool)
                self.tool = None

    def radiusChanged(self, value):
        self.radius_label.setText(f"{value} px")
        if self.tool:
            self.tool.setRadiusPx(value)
