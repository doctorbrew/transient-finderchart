"""Exercise the actual Qt time control without opening a visible window."""
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from findingchart_guiplotter.qt_compat import QApplication, QDateTime, Qt, qdatetime_to_datetime
    from findingchart_guiplotter.gui import MainWindow
except ImportError:
    MainWindow = None


@unittest.skipIf(MainWindow is None, "Qt GUI dependencies unavailable")
class ObservationTimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_widget_defaults_to_current_utc(self):
        window = MainWindow()
        try:
            widget = window.datetime_edit
            self.assertEqual(widget.timeSpec(), Qt.TimeSpec.UTC)
            self.assertIn("UTC", widget.text())
            selected = qdatetime_to_datetime(widget.dateTime())
            self.assertEqual(selected.tzinfo, timezone.utc)
            self.assertLess(abs((datetime.now(timezone.utc) - selected).total_seconds()), 5)
        finally:
            window.close()

    def test_conversion_preserves_offset_instant(self):
        qt_time = QDateTime.fromString("2025-10-30T03:00:00+02:00", Qt.DateFormat.ISODate)
        self.assertEqual(qdatetime_to_datetime(qt_time), datetime(2025, 10, 30, 1, tzinfo=timezone.utc))

    def test_failed_pa_does_not_change_slit_settings(self):
        from findingchart_guiplotter.models import Target
        window = MainWindow()
        try:
            window.target = Target(display_name="SN", ra_deg=0, dec_deg=-89)
            window.pa_spin.setValue(87)
            window.slit_check.setChecked(False)
            with patch.object(window, "show_error") as error:
                window.set_pa_to_parallactic()
            self.assertEqual(window.pa_spin.value(), 87)
            self.assertFalse(window.slit_check.isChecked())
            self.assertIn("horizon", error.call_args.args[0])
        finally:
            window.close()
