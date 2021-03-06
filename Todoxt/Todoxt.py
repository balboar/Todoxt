
from PyQt5 import QtGui,QtCore,QtWidgets
import sys
import os
import configparser
import logging
import qdarkstyle
from pathlib import Path
if os.name == 'nt':
    import winreg

import todoParser
import todoxt_window
import settings_dialog

REGISTRY_KEY = 'Software\Todoxt'
LINUX_CONFIG_PATH = '/.Todoxt'

class todoTxtApp(todoxt_window.Ui_MainWindow):
    def __init__(self,dialog):

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        todoxt_window.Ui_MainWindow.__init__(self)
        self._os = os.name
        if self._os == 'posix':
            self.configPath = str(Path.home()) + LINUX_CONFIG_PATH
            self._path, self._qtstyle = self.loadConfig()
        elif self._os == 'nt':
            hKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            try:
                self._path = winreg.QueryValue(hKey, "Path")
                self._qtstyle = winreg.QueryValue(hKey, "QtStyle")
            except OSError:
                self._path = ''
                winreg.SetValue(hKey, "Path", winreg.REG_SZ, self._path)

            winreg.CloseKey(hKey)
        self._opened =False
        self.setupUi(dialog)

        # self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        self.readTodoFile()

        self.shortcutNewTask = QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+T'), self.EditNew, self.setFocusNewTask)
        self.shortcutFind = QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+F'), self.findEdit, self.setFocusFindEdit)

        self.treeWidget.itemChanged.connect(self.onChanged)
        self.treeWidget.itemClicked.connect(self.onClicked)

        self.btnSettings.clicked.connect(self.onSettingsClicked)
        self.btnRefresh.clicked.connect(self.onRefresh)
        self.EditNew.returnPressed.connect(self.onNewTask)
        self.findEdit.textChanged.connect(self.findInList)

    def checkDir(self, file_path):
        if not os.path.exists(file_path):
            os.makedirs(file_path)


    def readTodoFile(self):
        if self._opened == False and str(self._path):
            try:
                self._tasks, self._contexts, self._projects = todoParser.from_file(self._path)
                self.treeWidget.clear()
                for todo in self._tasks:
                    self.addItems(todo)
                self._opened = True
            except FileNotFoundError:
                pass

    def setFocusNewTask(self):
        self.EditNew.setFocus()

    def setFocusFindEdit(self):
        self.findEdit.setFocus()

    def loadConfig(self):
        self.config = configparser.ConfigParser()
        if os.path.isfile(self.configPath + '/config.ini'):
            self.config.read(self.configPath + '/config.ini')
            if self.config.has_option('TodoTxtApp', 'Path') and self.config.has_option('TodoTxtApp', 'QTStyle'):
                return self.config.get('TodoTxtApp', 'Path') , self.config.get('TodoTxtApp', 'QTStyle')
            else:
                self.createConfigFile()
                return None,None
        else:
            self.createConfigFile()

    def createConfigFile(self):
        cfgfile = open(self.configPath + '/config.ini', 'w')
        self.config.add_section('TodoTxtApp')
        self.config.set('TodoTxtApp', 'Path', '')
        self.config.set('TodoTxtApp', 'QTStyle', 'White')
        self.config.write(cfgfile)
        cfgfile.close()
        self.config.get('TodoTxtApp', 'Path')

    def onRefresh(self):
        self._opened = False
        self.findEdit.clear()
        self.readTodoFile()

    def addItems(self, todo):
        item = todoxt_window.customQtTreeWidgetItem(todo)
        item.isExpanded = False
        item.setText(1,todo.getTask())
        if todo.creation_date:
            item.setText(2, str(todo.creation_date))
        if todo.projects:
            item.setText(4,' '.join(todo.projects))
        if todo.contexts:
            item.setText(3,' '.join(todo.contexts))
        item.setFlags(
            QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        item.setCheckState(0,QtCore.Qt.Unchecked)
        self.treeWidget.addTopLevelItem(item)


    def findInList(self):
        if self.findEdit.text():
            f = lambda task : self.findEdit.text() in task
            _searchList = []
            for todo in self._tasks:
                if self.findEdit.text().upper() in str(todo).upper():
                    _searchList.append(todo)
            self.refreshTaskList(_searchList)
        else:
            self.refreshTaskList(self._tasks)

    def onChanged(self,item,column):
        if column == 1:
            setattr(item._todo,'text',item.text(1))
        elif column == 2:
            setattr(item._todo,'completion_date',item.text(2))
        elif column == 3:
            setattr(item._todo,'contexts',item.text(3).spli())
        elif column == 4:
            setattr(item._todo, 'projects', item.text(4).split())
        todoParser.to_file(self._path,self._tasks)

    def onClicked(self,item,column):
        if column == 0:
            self.treeWidget.blockSignals(True)
            if item.checkState(0) == QtCore.Qt.Checked:
                self.taskCompleted(item)
            self.treeWidget.blockSignals(False)

    def taskCompleted(self,item):
        setattr(todoParser.Todo(item._todo),'completed',True)
        donefile = open(os.path.dirname(self._path)+ '/done.txt', 'a')
        donefile.write(str(item._todo)+'\n')
        donefile.close()
        self._tasks.remove(item._todo)
        self.treeWidget.takeTopLevelItem(self.treeWidget.indexOfTopLevelItem(item))
        todoParser.to_file(self._path, self._tasks)

    def refreshTaskList(self,taskList):
        index = 0
        while index < self.treeWidget.topLevelItemCount():
            self.treeWidget.takeTopLevelItem(index)
            index+=index
        for todo in taskList:
            self.addItems(todo)


    def newTask(self,text):
        todo = todoParser.new_todo(text)
        self._tasks.append(todo)
        todoParser.to_file(self._path, self._tasks)
        self.addItems(todo)

    def onNewTask(self):
        if self.EditNew.text():
            self.newTask(self.EditNew.text())
            self.EditNew.clear()

    def onSettingsClicked(self):
        dialog = SettingsDialog()
        dialog.lineEdit.setText(self._path)
        dialog.comboBox.setCurrentText(self._qtstyle)
        dialog.exec_()
        self._path= dialog.lineEdit.text()
        if str(self._path)!='':
            try:
                if self._os == 'posix':
                    cfgfile = open(self.configPath + '/config.ini', 'w')
                    self.config.set('TodoTxtApp', 'Path', self._path)
                    self.config.write(cfgfile)
                    cfgfile.close()
                elif self._os == 'nt':
                    hKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, access=winreg.KEY_READ)
                    winreg.SetValue(hKey, "Path", winreg.REG_SZ, self._path)
                    winreg.CloseKey(hKey)
                self._opened = False
                self.readTodoFile()
            except:
                self.logger.error('Error')
        if self._qtstyle!=dialog.comboBox.currentText():
            self._qtstyle = dialog.comboBox.currentText()
            if self._os == 'posix':
                cfgfile = open(self.configPath + '/config.ini', 'w')
                self.config.set('TodoTxtApp', 'QTStyle', self._qtstyle)
                self.config.write(cfgfile)
                cfgfile.close()
            elif self._os == 'nt':
                hKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, access=winreg.KEY_READ)
                winreg.SetValue(hKey, "QTStyle", winreg.REG_SZ, self._qtstyle)
                winreg.CloseKey(hKey)





class SettingsDialog(QtWidgets.QDialog,settings_dialog.Ui_Dialog):
    def __init__(self,parent = None):
        super(SettingsDialog,self).__init__(parent)
        # self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setupUi(self)
        self.toolButton.clicked.connect(self.onFileExplorerClicked)

    def onFileExplorerClicked(self):
        self.path = QtWidgets.QFileDialog.getOpenFileName(self,'Select file',os.getcwd(),'Text files (*.txt)')
        self.lineEdit.setText(self.path[0])


class MessageBox(QtWidgets.QMessageBox):
    def __init__(self,msg1,msg2):
        super(MessageBox, self).__init__()
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setIcon(QtWidgets.QMessageBox.Warning)
        error_dialog.setText(msg1)
        error_dialog.setWindowTitle(msg1)
        error_dialog.setInformativeText(msg2)
        error_dialog.show()

def loadQtStyle():
    Qtstyle = 'White'
    if os.name == 'nt':
        try:
            hKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            winreg.QueryValue(hKey, "QTStyle")
        except OSError:
            hKey = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
            winreg.SetValue(hKey, "QTStyle", winreg.REG_SZ, Qtstyle)

        return  winreg.QueryValue(hKey, "QTStyle")
        winreg.CloseKey(hKey)
    else:
        config = configparser.ConfigParser()
        linuxPath = str(Path.home())+LINUX_CONFIG_PATH
        if os.path.isfile( linuxPath+ '/config.ini'):
            config.read(linuxPath+ '/config.ini')
            if config.has_option('TodoTxtApp', 'QTStyle'):
                Qtstyle = config.get('TodoTxtApp', 'QTStyle')
        return Qtstyle


if __name__=='__main__':
    app=QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon('icon.png'))
    Qtstyle = loadQtStyle()
    if Qtstyle == 'Black':
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    dialog=QtWidgets.QMainWindow()
    form = todoTxtApp(dialog)
    dialog.show()
    sys.exit(app.exec_())
