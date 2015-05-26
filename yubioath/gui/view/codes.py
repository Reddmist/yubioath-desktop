# Copyright (c) 2014 Yubico AB
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Additional permission under GNU GPL version 3 section 7
#
# If you modify this program, or any covered work, by linking or
# combining it with the OpenSSL project's OpenSSL library (or a
# modified version of that library), containing parts covered by the
# terms of the OpenSSL or SSLeay licenses, We grant you additional
# permission to convey the resulting work. Corresponding Source for a
# non-source form of such a combination shall include the source code
# for the parts of OpenSSL used as well as that of the covered work.

from PySide import QtGui, QtCore
from .. import messages as m
from ..controller import CredentialType
from time import time


INF = float('inf')


class TimeleftBar(QtGui.QProgressBar):
    expired = QtCore.Signal()

    def __init__(self):
        super(TimeleftBar, self).__init__()

        self.setInvertedAppearance(True)
        self.setRange(0, 30000)
        self.setValue(0)
        self.setTextVisible(False)

        self._timer = 0
        self._timeleft = 0

    def set_timeleft(self, millis):
        self._timeleft = max(0, millis)
        self.setValue(min(millis, self.maximum()))
        if self._timer == 0 and millis > 0:
            self._timer = self.startTimer(250)
        elif self._timer != 0 and millis <= 0:
            self.killTimer(self._timer)
            self._timer = 0

    def timerEvent(self, event):
        self.set_timeleft(max(0, self._timeleft - 250))
        if self._timeleft == 0:
            self.expired.emit()


class Code(QtGui.QWidget):

    def __init__(self, cred, timer, on_change):
        super(Code, self).__init__()
        self.cred = cred
        self._on_change = on_change
        self.cred.changed.connect(self._draw)
        self.timer = timer

        layout = QtGui.QHBoxLayout(self)

        labels = QtGui.QVBoxLayout()
        self._name_lbl = QtGui.QLabel(cred.name)
        labels.addWidget(self._name_lbl)
        self._code_lbl = QtGui.QLabel()
        labels.addWidget(self._code_lbl)
        layout.addLayout(labels)
        layout.addStretch()

        self._calc_btn = QtGui.QPushButton('Calc')
        self._calc_btn.clicked.connect(self._calc)
        layout.addWidget(self._calc_btn)

        self._copy_btn = QtGui.QPushButton('Copy')
        self._copy_btn.clicked.connect(self._copy)
        layout.addWidget(self._copy_btn)

        timer.time_changed.connect(self._draw)

        self._draw()

    @property
    def expired(self):
        return self.cred.code.timestamp < self.timer.time

    def _draw(self):
        if self.expired:
            name_fmt = '<b style="color: gray;">%s</b>'
        else:
            name_fmt = '<b>%s</b>'
        self._code_lbl.setText(name_fmt % (self.cred.code.code))
        self._on_change()

    def _copy(self):
        print "TODO: copy", self.cred.code.code

    def _calc(self):
        if self.cred.cred_type in [CredentialType.TOUCH, CredentialType.HOTP]:
            self.cred.calculate()


class CodesList(QtGui.QWidget):

    def __init__(self, timer, credentials=[], on_change=None):
        super(CodesList, self).__init__()

        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        for cred in credentials:
            layout.addWidget(Code(cred, timer, on_change))


class CodesWidget(QtGui.QWidget):

    def __init__(self, controller):
        super(CodesWidget, self).__init__()

        self._controller = controller
        controller.refreshed.connect(self.refresh)
        controller.timer.time_changed.connect(self.refresh_timer)

        self._build_ui()
        self.refresh()
        self.refresh_timer()

    def _build_ui(self):
        layout = QtGui.QVBoxLayout(self)
        self._timeleft = TimeleftBar()
        layout.addWidget(self._timeleft)

        self._scroll_area = QtGui.QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(QtGui.QWidget())
        layout.addWidget(self._scroll_area)

    def refresh_timer(self, timestamp=None):
        if timestamp is None:
            timestamp = self._controller.timer.time
        expiring = False
        for c in self._controller.credentials or []:
            if c.code.timestamp >= timestamp and c.code.timestamp < INF:
                expiring = True
                break
        if expiring:
            self._timeleft.set_timeleft(1000 * (timestamp + 30 - time()))
        else:
            self._timeleft.set_timeleft(0)

    def refresh(self):
        self._scroll_area.takeWidget()
        creds = self._controller.credentials
        self._scroll_area.setWidget(
            CodesList(self._controller.timer, creds or [], self.refresh_timer))
        # Show timer IF: AutoCredential in creds, OR TouchCredential