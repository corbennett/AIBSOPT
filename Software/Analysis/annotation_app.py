"""

This app allows a user to browse through an OPT volume and mark probe track locations.

"""

import sys
from functools import partial
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QGridLayout, QFileDialog, QSlider, QLabel, QLineEdit
import PyQt5.QtWidgets as QtWidgets 
from PyQt5.QtGui import QIcon, QKeyEvent, QImage, QPixmap, QColor
from PyQt5.QtCore import pyqtSlot, Qt

from PIL import Image, ImageQt

import numpy as np
import pandas as pd

import os

DEFAULT_SLICE = 400
DEFAULT_VIEW = 0

class App(QWidget):
 
    def __init__(self):
        super().__init__()
        self.title = 'OPT Annotation'
        self.left = 500
        self.top = 100
        self.width = 800
        self.height = 800
        self.initUI()
     
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        grid = QGridLayout()

        self.image = QLabel()
        self.image.setObjectName("image")
        self.image.mousePressEvent = self.clickedOnImage
        im8 = Image.fromarray(np.ones((800,800),dtype='uint8')*255)
        imQt = QImage(ImageQt.ImageQt(im8))
        imQt.convertToFormat(QImage.Format_ARGB32)
        self.image.setPixmap(QPixmap.fromImage(imQt))
        grid.addWidget(self.image, 0, 0)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(1022)
        self.slider.setValue(DEFAULT_SLICE)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(100)
        self.slider.valueChanged.connect(self.sliderMoved)
        grid.addWidget(self.slider, 1,0)

        self.slider_values = [DEFAULT_SLICE, DEFAULT_SLICE, DEFAULT_SLICE]

        subgrid = QGridLayout()

        self.probes = ('A1', 'B1', 'C1', 'D1', 'E1', 'F1',
                       'A2', 'B2', 'C2', 'D2', 'E2', 'F2')
        
        self.probe_map = {'Probe A1': 0, 'Probe B1': 1, 'Probe C1': 2, 'Probe D1' : 3,
                          'Probe E1': 4, 'Probe F1': 5,
                          'Probe A2': 6, 'Probe B2': 7, 'Probe C2': 8, 'Probe D2' : 9,
                          'Probe E2': 10, 'Probe F2': 11,
                          'switch A': 12, 'switch B': 13, 'switch C': 14, 'switch D': 15,
                          'switch E': 16, 'switch F': 17
                     }

        self.color_map = {'Probe A1': 'darkred', 'Probe B1': 'cadetblue',
                     'Probe C1': 'goldenrod', 'Probe D1' : 'darkgreen',
                     'Probe E1': 'darkblue', 'Probe F1': 'blueviolet',
                     'Probe A2': 'red', 'Probe B2': 'darkturquoise',
                     'Probe C2': 'yellow', 'Probe D2' : 'green',
                     'Probe E2': 'blue', 'Probe F2': 'violet'}

        self.probe_buttons = [QPushButton('Probe ' + i) for i in self.probes]

        for i, button in enumerate(self.probe_buttons):
            button.setToolTip('Annotate ' + button.text())
            button.clicked.connect(partial(self.selectProbe, button))
            subgrid.addWidget(button, i//6, i % 6)

        self.coronal_button = QPushButton('Coronal', self)
        self.coronal_button.setToolTip('Switch to coronal view')
        self.coronal_button.clicked.connect(self.viewCoronal)

        self.horizontal_button = QPushButton('Horizontal', self)
        self.horizontal_button.setToolTip('Switch to horizontal view')
        self.horizontal_button.clicked.connect(self.viewHorizontal)

        self.sagittal_button = QPushButton('Sagittal', self)
        self.sagittal_button.setToolTip('Switch to sagittal view')
        self.sagittal_button.clicked.connect(self.viewSagittal)
        
        self.pointLock_button = QPushButton('Point Lock ON', self)
        self.pointLock_button.setToolTip('Toggle point lock')
        self.pointLock_button.clicked.connect(self.pointLockToggle)
        self.pointLock_button.setStyleSheet("background-color: rgb(170,0,0);color: white;font: bold 12px")
        
        self.switch_probe_button = QPushButton('Switch probe day', self)
        self.switch_probe_button.setToolTip('Switch probe recording day')
        self.switch_probe_button.clicked.connect(self.switchProbeDay)

        self.projection_button = QPushButton('Show Projection', self)
        self.projection_button.setToolTip('Show projection of next 10 slices')
        self.projection_button.clicked.connect(self.showProjection)
        
        self.levelsLowField = QLineEdit(self)
        self.levelsLowField.setFixedWidth(120)
        self.levelsHighField = QLineEdit(self)
        self.levelsHighField.setFixedWidth(120)
        
        self.updateButton = QPushButton('Update', self)
        self.updateButton.clicked.connect(self.refreshImage)

        self.current_view = DEFAULT_VIEW

        subgrid.addWidget(self.coronal_button,2,0)
        subgrid.addWidget(self.horizontal_button,2,1)
        subgrid.addWidget(self.sagittal_button,2,2)
        subgrid.addWidget(self.projection_button,2,3)
        subgrid.addWidget(self.pointLock_button,2,4,1,2)
        
        subgrid.addWidget(self.switch_probe_button,3,0,1,1)
        subgrid.addWidget(self.levelsLowField,3,1,1,1)
        subgrid.addWidget(self.levelsHighField,3,2,1,1)
        subgrid.addWidget(self.updateButton,3,3,1,1)
        
                          
        save_button = QPushButton('Save', self)
        save_button.setToolTip('Save values as CSV')
        save_button.clicked.connect(self.saveData)

        load_button = QPushButton('Load', self)
        load_button.setToolTip('Load volume data')
        load_button.clicked.connect(self.loadData)

        subgrid.addWidget(save_button,3,4)
        subgrid.addWidget(load_button,3,5)

        grid.addLayout(subgrid,2,0)

        self.current_directory = '/mnt/md0/data/opt/production'

        self.data_loaded = False

        self.selected_probe = None

        self.showing_projection = False
        
        self.point_lock = True

        self.setLayout(grid)
        self.viewCoronal()
        self.show()

    def keyPressEvent(self, e):
        
        if e.key() == Qt.Key_A:
            self.selectProbe(self.probe_buttons[0])
        if e.key() == Qt.Key_B:
            self.selectProbe(self.probe_buttons[1])
        if e.key() == Qt.Key_C:
            self.selectProbe(self.probe_buttons[2])
        if e.key() == Qt.Key_D:
            self.selectProbe(self.probe_buttons[3])
        if e.key() == Qt.Key_E:
            self.selectProbe(self.probe_buttons[4])
        if e.key() == Qt.Key_F:
            self.selectProbe(self.probe_buttons[5])
        if e.key() == Qt.Key_1:
            self.selectProbe(self.probe_buttons[6])
        if e.key() == Qt.Key_2:
            self.selectProbe(self.probe_buttons[7])
        if e.key() == Qt.Key_3:
            self.selectProbe(self.probe_buttons[8])
        if e.key() == Qt.Key_4:
            self.selectProbe(self.probe_buttons[9])
        if e.key() == Qt.Key_5:
            self.selectProbe(self.probe_buttons[10])
        if e.key() == Qt.Key_6:
            self.selectProbe(self.probe_buttons[11])
        if e.key() == Qt.Key_Backspace:
            self.deletePoint()

    def deletePoint(self):
        if not self.showing_projection and not self.point_lock:
            if self.selected_probe is not None:
    
                if self.current_view == 0:
                    matching_index = self.annotations[(self.annotations.AP == self.slider.value()) &
                                                           (self.annotations.probe_name == self.selected_probe)].index.values
                elif self.current_view == 1:
                    matching_index = self.annotations[(self.annotations.DV == self.slider.value()) &
                                                           (self.annotations.probe_name == self.selected_probe)].index.values
                elif self.current_view == 2:
                    matching_index = self.annotations[(self.annotations.ML == self.slider.value()) &
                                                           (self.annotations.probe_name == self.selected_probe)].index.values
    
                if len(matching_index) > 0:
                    self.annotations = self.annotations.drop(index=matching_index)
    
                    self.saveData()
                
                    self.refreshImage()

    def clickedOnImage(self , event):
        if not self.showing_projection and not self.point_lock:
            if self.data_loaded:
                x = int(event.pos().x() * 1024 / 800)
                y = int(event.pos().y() * 1024 / 800)

                #print('X: ' + str(x))
                #print('Y: ' + str(y))

                if self.selected_probe is not None:
                    #print('updating volume')

                    if self.current_view == 0:
                        AP = self.slider.value()
                        DV = y
                        ML = 1023-x
                        matching_index = self.annotations[(self.annotations.AP == AP) &
                                                           (self.annotations.probe_name == 
                                                            self.selected_probe)].index.values
                    elif self.current_view == 1:
                        AP = 1023-y
                        DV = self.slider.value()
                        ML = 1023-x
                        matching_index = self.annotations[(self.annotations.DV == DV) &
                                                           (self.annotations.probe_name == 
                                                            self.selected_probe)].index.values
                    elif self.current_view == 2:
                        AP = x
                        DV = y
                        ML = self.slider.value()
                        matching_index = self.annotations[(self.annotations.ML == ML) &
                                                           (self.annotations.probe_name == 
                                                            self.selected_probe)].index.values


                    if len(matching_index) > 0:
                        self.annotations = self.annotations.drop(index=matching_index)

                    self.annotations = self.annotations.append(pd.DataFrame(data = {'AP' : [AP],
                                        'ML' : [ML],
                                        'DV': [DV],
                                        'probe_name': [self.selected_probe]}), 
                                        ignore_index=True)

                    self.saveData()

                    self.refreshImage()

    def selectProbe(self, b):

        for button in self.probe_buttons:
            button.setStyleSheet("background-color: white")
        
        b.setStyleSheet("background-color: " + self.color_map[b.text()])

        self.selected_probe = b.text()

    def sliderMoved(self):

        self.slider_values[self.current_view] = self.slider.value()
        self.refreshImage()

    def viewCoronal(self):
        
        self.current_view = 0
        self.slider.setValue(self.slider_values[self.current_view])
        self.coronal_button.setStyleSheet("background-color: gray")
        self.horizontal_button.setStyleSheet("background-color: white")
        self.sagittal_button.setStyleSheet("background-color: white")
        self.refreshImage()

    def viewHorizontal(self):

        self.current_view = 1
        self.slider.setValue(self.slider_values[self.current_view])
        self.coronal_button.setStyleSheet("background-color: white")
        self.horizontal_button.setStyleSheet("background-color: gray")
        self.sagittal_button.setStyleSheet("background-color: white")
        self.refreshImage()

    def viewSagittal(self):

        self.current_view = 2
        self.slider.setValue(self.slider_values[self.current_view])
        self.coronal_button.setStyleSheet("background-color: white")
        self.horizontal_button.setStyleSheet("background-color: white")
        self.sagittal_button.setStyleSheet("background-color: gray")
        self.refreshImage()
        
    def switchProbeDay(self):
        
        if self.selected_probe is not None:
            
            for ii in range(0,len(self.annotations.probe_name)):
                if self.annotations.probe_name.iloc[ii][:7]==self.selected_probe[:7]:
                    if self.annotations.probe_name.iloc[ii][-1]=='1':
                        self.annotations.probe_name.iloc[ii]=self.annotations.probe_name.iloc[ii][:-1]+'2'
                    elif self.annotations.probe_name.iloc[ii][-1]=='2':
                        self.annotations.probe_name.iloc[ii]=self.annotations.probe_name.iloc[ii][:-1]+'1'
                
                    self.saveData()
            
            self.refreshImage()
            
    def pointLockToggle(self):
        
            if self.point_lock:
                self.point_lock = False
                self.pointLock_button.setText('Point Lock OFF')
                self.pointLock_button.setStyleSheet("background-color: white;color: black;font: 12px")
            else:
                self.point_lock = True
                self.pointLock_button.setText('Point Lock ON')
                self.pointLock_button.setStyleSheet("background-color: rgb(170,0,0);color: white;font: bold 12px")
            
        
    def refreshImage(self):

        colors = ('darkred', 'orangered', 'goldenrod', 
            'darkgreen', 'darkblue', 'blueviolet',
            'red','orange','yellow','green','blue','violet')
        
        #set level-scaling cutoffs
        low_thresh=[]
        try:
            low_thresh=int(self.levelsLowField.text())
        except:
            low_thresh=0
        if low_thresh:
            if (low_thresh<0)|(low_thresh>100):
                low_thresh=0
        else:
            low_thresh=0
            
        high_thresh=[]
        try:
            high_thresh=int(self.levelsHighField.text())
        except:
            high_thresh=100
        if high_thresh:
            if (high_thresh<0)|(high_thresh>100):
                high_thresh=100
        else:
            high_thresh=100
        
        
        # if self.data_loaded:
        #     plane = np.take(self.volume,
        #          self.slider.value(),
        #          axis=self.current_view)
        #     if self.current_view == 2:
        #         plane = plane.T
        #     if self.current_view == 1:
        #         plane = np.rot90(np.rot90(plane))
        #     if self.current_view == 0:
        #         plane = np.fliplr(plane)
        if self.data_loaded:
            if self.showing_projection:
                projection_indices = np.arange(self.slider.value()-25, self.slider.value()+25)
                get_plane = lambda x: np.max(x, axis=self.current_view)
            else:
                projection_indices = self.slider.value()
                get_plane = lambda x: x
            
            plane = np.take(self.volume,
                  projection_indices,
                  axis=self.current_view)
            if self.current_view == 2:
                plane = get_plane(plane)
                plane = plane.T
            if self.current_view == 1:
                plane = get_plane(plane)
                plane = np.rot90(np.rot90(plane))
            if self.current_view == 0:
                plane = get_plane(plane)
                plane = np.fliplr(plane)
            #scale image levels
            upper_q=np.percentile(plane,high_thresh)
            lower_q=np.percentile(plane,low_thresh)
            plane_scaled = (plane-lower_q)/(upper_q-lower_q)
            plane_scaled[plane_scaled<0]=0
            plane_scaled[plane_scaled>1]=1
            plane_scaled=np.round(plane_scaled*255)
            plane_scaled=np.asarray(plane_scaled, dtype='uint8')
            
            im8 = Image.fromarray(plane_scaled)            
        else:
            im8 = Image.fromarray(np.ones((1024,1024),dtype='uint8')*255)
        
        imQt = QImage(ImageQt.ImageQt(im8))
        imQt = imQt.convertToFormat(QImage.Format_RGB16)

        #print(self.current_view)
        #print(self.slider.value())
           
        if self.data_loaded:
            for idx, row in self.annotations.iterrows():

                if self.current_view == 0:
                    #shouldDraw = row.AP == self.slider.value()
                    shouldDraw = np.isin(row.AP, projection_indices)
                    x = 1023-row.ML
                    y = row.DV
                elif self.current_view == 1:
                    shouldDraw = np.isin(row.DV, projection_indices)
                    x = 1023-row.ML
                    y = 1023-row.AP
                elif self.current_view == 2:
                    shouldDraw = np.isin(row.ML, projection_indices)
                    x = row.AP
                    y = row.DV

                if shouldDraw:
                    color = QColor(self.color_map[row.probe_name])
                    
                    for j in range(x-10,x+10):
                        for k in range(y-10,y+10):
                            if row.probe_name[-1] == '1':
                                if pow(j-x,2) + pow(k-y,2) < 20:
                                    imQt.setPixelColor(j,k,color)
                            else:
                                if (pow(j-x,2) + pow(k-y,2) < 25) and (pow(j-x,2) + pow(k-y,2)) > 5:
                                    imQt.setPixelColor(j,k,color)

        pxmap = QPixmap.fromImage(imQt).scaledToWidth(800).scaledToHeight(800)
        self.image.setPixmap(pxmap)
    
    
    def showProjection(self):

        if not self.showing_projection:
            self.showing_projection = True
            self.projection_button.setStyleSheet("background-color: darkGray")
        else:
            self.showing_projection = False
            self.projection_button.setStyleSheet("background-color: lightGray")

        self.refreshImage()
        


    def loadData(self):
        
        fname, filt = QFileDialog.getOpenFileName(self, 
            caption='Select volume file', 
            directory=self.current_directory,
            filter='*nc.001')

        print(fname)

        self.current_directory = os.path.dirname(fname)
        self.output_file = os.path.join(self.current_directory, 'probe_annotations.csv')

        if fname.split('.')[-1] == '001':

            self.volume = self.loadVolume(fname)
            self.data_loaded = True
            self.setWindowTitle(os.path.basename(fname))
            
            if os.path.exists(self.output_file):
                self.annotations = pd.read_csv(self.output_file, index_col=0)
            else:
                self.annotations = pd.DataFrame(columns = ['AP','ML','DV', 'probe_name'])

            self.refreshImage()

        else:
            print('invalid file')

            
    def saveData(self):
        
        if self.data_loaded:
            self.annotations.to_csv(self.output_file)

    def loadVolume(self, fname, _dtype='u1', num_slices=1023):
        
        dtype = np.dtype(_dtype)

        volume = np.fromfile(fname, dtype) # read it in

        z_size = np.sum([volume[1], volume[2] << pow(2,3)])
        x_size = np.sum([(val << pow(2,i+1)) for i, val in enumerate(volume[8:4:-1])])
        y_size = np.sum([(val << pow(2,i+1)) for i, val in enumerate(volume[12:8:-1])])
        
        fsize = np.array([z_size, x_size, y_size]).astype('int')

        volume = np.reshape(volume[13:], fsize) # remove 13-byte header and reshape
        
        print("Data loaded.")
        
        return volume


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())

