import os
import logging

from astropy.io import registry as io_registry
from qtpy import compat
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QTabBar, QWidget, QAction, QColorDialog, QPushButton, QTabWidget
from qtpy.uic import loadUi

from specutils import Spectrum1D

from ..core.models import DataListModel, PlotProxyModel
from ..utils import UI_PATH
from .plotting import PlotWindow
from ..core.delegates import DataItemDelegate
from . import resources


class Workspace(QWidget):
    """
    A widget representing the primary interaction area for a given workspace.
    This includes the :class:`~qtpy.QtWidgets.QListView`, and the
    :class:`~qtpy.QtWigets.QMdiArea` widgets, and associated model information.
    """
    def __init__(self, *args, **kwargs):
        super(Workspace, self).__init__(*args, **kwargs)
        self._name = "Untitled Workspace"

        # Load the ui file and attach it to this instance
        loadUi(os.path.join(UI_PATH, "workspace.ui"), self)

        # Define a new data list model for this workspace
        self._model = DataListModel()

        # Set the styled item delegate on the model
        # self.list_view.setItemDelegate(DataItemDelegate(self))

        # Don't expand mdiarea tabs
        self.mdi_area.findChild(QTabBar).setExpanding(True)

        # Setup listview context menu
        self._toggle_visibility_action = QAction("Visible", parent=self)
        self._toggle_visibility_action.setCheckable(True)
        self._change_color_action = QAction("Change Color", parent=self)

        self.list_view.addAction(self._change_color_action)
        self.list_view.addAction(self._toggle_visibility_action)

        # When the current subwindow changes, mount that subwindow's proxy model
        self.mdi_area.subWindowActivated.connect(self._on_sub_window_activated)

        # Connect signals
        self._toggle_visibility_action.triggered.connect(self._on_toggle_visibility)
        self._change_color_action.triggered.connect(self._on_changed_color)

        # Add an initially empty plot
        self.add_plot_window()
        # self.mdi_area.findChild(QTabWidget).setCornerWidget(QPushButton())

    @property
    def name(self):
        """The name of this workspace."""
        return self._name

    @property
    def model(self):
        """
        The data model for this workspace.

        .. note:: there is always at most one model per workspace.
        """
        return self._model

    @property
    def proxy_model(self):
        return self.current_plot_window.proxy_model

    @property
    def current_plot_window(self):
        """
        Get the current active plot window tab.
        """
        return self.mdi_area.currentSubWindow() or self.mdi_area.subWindowList()[0]

    @property
    def current_data_item(self):
        """
        Get the currently selected :class:`~specviz.core.items.PlotDataItem`.
        """
        idx = self.list_view.currentIndex()
        item = self.proxy_model.data(idx, role=Qt.UserRole)

        return item

    def add_plot_window(self):
        """
        Creates a new plot widget sub window and adds it to the workspace.
        """
        plot_window = PlotWindow(model=self.model, parent=self.mdi_area)
        self.list_view.setModel(plot_window.plot_widget.proxy_model)

        plot_window.setWindowTitle(plot_window._plot_widget.title)
        plot_window.setAttribute(Qt.WA_DeleteOnClose)

        self.mdi_area.addSubWindow(plot_window)
        plot_window.showMaximized()

        self.mdi_area.subWindowActivated.emit(plot_window)

    def _on_sub_window_activated(self, window):
        if window is None:
            return

        # Disconnect all plot widgets from the core model's item changed event
        for sub_window in self.mdi_area.subWindowList():
            try:
                self._model.itemChanged.disconnect(
                    sub_window.plot_widget.on_item_changed)
            except TypeError:
                pass

        self.list_view.setModel(window.proxy_model)

        # Connect the current window's plot widget to the item changed event
        self.model.itemChanged.connect(window.plot_widget.on_item_changed)

        # Re-evaluate plot unit compatibilities
        window.plot_widget.check_plot_compatibility()

    def _on_toggle_visibility(self, state):
        idx = self.list_view.currentIndex()
        item = self.proxy_model.data(idx, role=Qt.UserRole)
        item.visible = state

        self.proxy_model.dataChanged.emit(idx, idx)

    def _on_changed_color(self, color):
        color = QColorDialog.getColor()

        if color.isValid():
            idx = self.list_view.currentIndex()
            item = self.proxy_model.data(idx, role=Qt.UserRole)

            item.color = color.name()

            self.proxy_model.dataChanged.emit(idx, idx)

    def _on_new_plot(self):
        self.add_plot_window()

    def _on_load_data(self):
        filters = [x + " (*)" for x in io_registry.get_formats(Spectrum1D)['Format']]

        file_path, fmt = compat.getopenfilename(parent=self,
                                                caption="Load spectral data file",
                                                filters=";;".join(filters))

        if not file_path:
            return

        spec = Spectrum1D.read(file_path, format=fmt.split()[0])

        name = file_path.split('/')[-1].split('.')[0]

        self.model.add_data(spec, name=name)

    def _on_delete_data(self):
        proxy_idx = self.list_view.currentIndex()
        model_idx = self.proxy_model.mapToSource(proxy_idx)

        # Ensure that the plots get removed from all plot windows
        for sub_window in self.mdi_area.subWindowList():
            proxy_idx = sub_window.proxy_model.mapFromSource(model_idx)
            sub_window.plot_widget.remove_plot(proxy_idx)

        self.model.removeRow(model_idx.row())
