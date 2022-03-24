"""

This app allows a user to compare CCF structure boundaries with physiological landmarks and update them accordingly.

"""

import sys
from functools import partial
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QGridLayout, QFileDialog, QSlider, QLabel
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtGui import QIcon, QKeyEvent, QImage, QPixmap, QColor
from PyQt5.QtCore import pyqtSlot, Qt

from PIL import Image, ImageQt

import numpy as np
import pandas as pd
import re

import os, glob

# OFFSET_MAP = {'probeA': 120, 'probeB': 346, 'probeC': 572, 'probeD' : 798,
#                      'probeE': 1024, 'probeF': 1250}
# INDEX_MAP = {'probeA': 0, 'probeB': 1, 'probeC': 2, 'probeD' : 3,
#                      'probeE': 4, 'probeF': 5}

OFFSET_MAP = {'Probe A1': 120, 'Probe B1': 346, 'Probe C1': 572, 'Probe D1' : 798, 'Probe E1': 1024, 'Probe F1': 1250,
                'Probe A2': 120, 'Probe B2': 346, 'Probe C2': 572, 'Probe D2' : 798, 'Probe E2': 1024, 'Probe F2': 1250}

INDEX_MAP = {'Probe A1': 0, 'Probe B1': 1, 'Probe C1': 2, 'Probe D1' : 3, 'Probe E1': 4, 'Probe F1': 5,
                'Probe A2': 0, 'Probe B2': 1, 'Probe C2': 2, 'Probe D2' : 3, 'Probe E2': 4, 'Probe F2': 5}


#structure_tree = pd.read_csv('/mnt/md0/data/opt/template_brain/ccf_structure_tree_2017.csv')
structure_tree = pd.read_csv(r"\\allen\programs\mindscope\workgroups\np-behavior\ccf_structure_tree_2017.csv")

def findBorders(structure_ids):
    
    borders = np.where(np.diff(structure_ids) != 0)[0]
    jumps = np.concatenate((np.array([5]),np.diff(borders)))
    border_ids = structure_ids[borders]
    l6b = np.array(['6b' in structure_tree.loc[sid]['acronym'] for sid in border_ids])
    borders = borders[(jumps > 3)|l6b]
    
    return borders


class BoundaryButtons():
    
    def __init__(self, probe, parent):
        self.probe = probe
        self.parent = parent
        self.buttons = []
        
    def createButtons(self):
        
        for i in range(50):
            button = QPushButton(str(i), self.parent)
            button.setGeometry(-100,20+i*50,50,15)
            button.clicked.connect(partial(self.buttonClicked, button))
            
            self.buttons.append(button)
            
    def updateBoundaries(self, structure_ids, border_locs):

        borders = findBorders(structure_ids)
  
        for i, border in enumerate(borders):
            
            try:
                name = structure_tree[structure_tree.index == structure_ids[border]]['acronym'].iloc[0]
            except IndexError:
                name = 'none'
            
            numbers = re.findall(r'\d+', name)
            
            if len(numbers) > 0 and name[:2] != 'CA':
                name = '/'.join(numbers)
                
            name = name.split('-')[0]
                
            self.buttons[i].setText(name)
            self.buttons[i].setObjectName(str(border))
            self.buttons[i].move(OFFSET_MAP[self.probe + str(self.parent.day)], border_locs[border] + 3)
        
        for i in range(len(borders),len(self.buttons)):
            self.buttons[i].setGeometry(-100,20+i*50,50,15)
            self.buttons[i].setObjectName(str(i))
            self.buttons[i].setText('')
            # print(self.buttons[i].objectName())
            # print(self.buttons[i].text())
            # print(self.buttons[i].geometry())
            # print(' ')
            
        self.parent.show()
        
    def buttonClicked(self, button):
        
        self.parent.selectBoundary(self.probe, button.objectName())
        

class App(QWidget):
 
    def __init__(self):
        super().__init__()
        self.title = 'OPT Annotation'
        self.left = 300
        self.top = 100
        self.width = 1600
        self.height = 800
        self.initUI()
     
    def initUI(self, day=1, fname=None):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        grid = QGridLayout()
        
        #self.probes = ('probeA', 'probeB', 'probeC', 'probeD', 'probeE', 'probeF')
        #self.probes = ('Probe A1', 'Probe B1', 'Probe C1', 'Probe D1', 'Probe E1', 'Probe F1')
        self.probes = ['Probe '+p+str(day) for p in 'ABCDEF']
        self.day = day
        self.fname = fname
        self.day_selected = False
        self.probe_images = [QLabel(i) for i in self.probes]
        
        im8 = Image.fromarray(np.ones((800,100),dtype='uint8')*230)
        imQt = QImage(ImageQt.ImageQt(im8))
        imQt.convertToFormat(QImage.Format_ARGB32)

        for i, image in enumerate(self.probe_images):
            image.setObjectName(self.probes[i][:-1])
            image.mousePressEvent = partial(self.clickedOnImage, image)
            image.setPixmap(QPixmap.fromImage(imQt))
            grid.addWidget(image,0,i*2)
            
        self.boundary_buttons = [BoundaryButtons(i[:-1], self) for i in self.probes]
        
        subgrid = QGridLayout()

        save_button = QPushButton('Save', self)
        save_button.setToolTip('Save values as CSV')
        save_button.clicked.connect(self.saveData)

        load_button = QPushButton('Load', self)
        load_button.setToolTip('Load volume data')
        load_button.clicked.connect(self.loadData)

        self.set_day1_button = QPushButton('Day 1', self)
        self.set_day1_button.setToolTip('Set annotations for day 1')
        self.set_day1_button.clicked.connect(partial(self.setDay, 1))

        self.set_day2_button = QPushButton('Day 2', self)
        self.set_day2_button.setToolTip('Set annotations for day 2')
        self.set_day2_button.clicked.connect(partial(self.setDay, 2))

        subgrid.addWidget(save_button,2,2)
        subgrid.addWidget(load_button,3,2)
        subgrid.addWidget(self.set_day1_button, 4,2)
        subgrid.addWidget(self.set_day2_button, 5,2)


        grid.addLayout(subgrid,0,13)

        self.current_directory = r'\\allen\programs\mindscope\workgroups\np-behavior\processed_ALL'

        self.data_loaded = False

        self.selected_probe = None

        self.setLayout(grid)
        
        for buttons in self.boundary_buttons:
            buttons.createButtons()
            
        self.selected_probe = None
        self.selected_boundary = -1
        
        self.init_anchors = [False, False]

        self.show()
        
    def keyPressEvent(self, e):
        
        if e.key() == Qt.Key_Backspace:
            self.deleteAnchorPoint()

    def clickedOnImage(self , image, event):

        x = event.pos().x()
        y = event.pos().y()

        if x < 100 and image.objectName() == self.selected_probe[:-1]:
            
            self.anchor_points[self.selected_boundary, INDEX_MAP[self.selected_probe]] = int(y / 2)
            #print(y)

        self.refreshImage(self.selected_probe)

    def deleteAnchorPoint(self):
        
        self.anchor_points[self.selected_boundary, INDEX_MAP[self.selected_probe]] = -1
        self.refreshImage(self.selected_probe)

    def refreshImage(self, probe_to_refresh = None):

        if self.data_loaded:
            
            for i, probe in enumerate(self.probes):

                print(probe)
                
                if (probe == probe_to_refresh or probe_to_refresh == None) and (probe in self.df['probe'].unique()):
                    
                    structure_ids = self.df[self.df['probe'] == probe]['structure_id'].values
                    #print('structure ids for probe {}'.format(probe))
                    #print(structure_ids)
                    borders = findBorders(structure_ids)
                    # #most ventral point in annotation
                    if len(self.df_ann)>0:
                        probe_ann_pts = self.df_ann[self.df_ann['probe'] == probe]
                        tip_ind = np.argmax(probe_ann_pts['D/V'].values)
                        tip = [
                            probe_ann_pts['A/P'].iloc[tip_ind],
                            probe_ann_pts['D/V'].iloc[tip_ind],
                            probe_ann_pts['M/L'].iloc[tip_ind],
                        ]
                        
                        probe_df = self.df[self.df['probe'] == probe]
                        distances = probe_df.apply(
                            lambda row: np.sqrt(
                                (row['A/P'] - tip[0])**2 +
                                (row['D/V'] - tip[1])**2 + 
                                (row['M/L'] - tip[2])**2), axis=1)
                        tipRow = np.argmin(distances.values)
                        #borders = findBorders(structure_ids)
                        border_dist_from_tip = 400-borders
                        #ensure chosen anchor point is above tip & visible in GUI
                        positive_border_dist_from_tip = border_dist_from_tip[border_dist_from_tip>=0]
                        closest_border_to_tip = np.argmin(positive_border_dist_from_tip)
                    
                    if len(structure_ids) > 0:
                
                        scale_factor = 6.0
                        
                        # #set nearest border to tip as the initial anchor
                        # if self.init_anchors[self.day-1] == False and len(self.df_ann)>0:
                        #     self.anchor_points[borders[closest_border_to_tip], i] = borders[closest_border_to_tip]
                            
                        anchor_inds = np.where(self.anchor_points[:,i] > -1)[0]
                        anchor_locs = self.anchor_points[anchor_inds,i]
                        
                        if len(self.df_ann)>0:
                            border_locs = np.arange(self.anchor_points.shape[0]) - (400 - tipRow)
                        else:
                            border_locs = np.arange(self.anchor_points.shape[0])
                            
                        for ii, ind in enumerate(anchor_inds):
                            if ii == 0:
                                border_locs = border_locs - border_locs[ind] + anchor_locs[ii]
                            else:
                                scaling = (anchor_locs[ii] - anchor_locs[ii-1]) / (anchor_inds[ii] - anchor_inds[ii-1])
     
                                border_locs[anchor_inds[ii-1]:anchor_inds[ii]] = \
                                    (border_locs[anchor_inds[ii-1]:anchor_inds[ii]] - border_locs[anchor_inds[ii-1]]) * scaling + \
                                    border_locs[anchor_inds[ii-1]]
                                border_locs[anchor_inds[ii]:] = border_locs[anchor_inds[ii]:] - border_locs[anchor_inds[ii]] + anchor_locs[ii]
                                   
                                
                        #imQt = self.images[i].copy()
                        imQt = self.images[probe[:-1]].copy()
                        
                        print('image height')
                        print(imQt.height())
                        
                        if imQt.height() == 2400:
                            
                            self.boundary_buttons[i].updateBoundaries(structure_ids, border_locs*2)
                            channels = 384 - (border_locs * scale_factor / 2400 * 384)
                            
                            self.df.loc[self.df.probe == probe, 'channels'] = channels
                            
                            border_locs = border_locs*scale_factor 
   
                            borders = findBorders(structure_ids)
                            # print(probe)
                            # print(structure_ids[borders])
                            # print(borders)
        
                            for j, border in enumerate(borders):
                                
                                y = int(border_locs[border]) #+ 5
                                
                                if probe == self.selected_probe and border == self.selected_boundary:
                                    color = QColor(20,200,60)
                                    d = 6
                                else:
                                    if border in anchor_inds:
                                        color = QColor(20,200,60)
                                    else:
                                        color = QColor(10,10,10)
                                    d = 3
                
                                if y < (2400 - d) and y > 0:
                                    for x in range(0,300):
                                        for dy in range(0,d):
                                            imQt.setPixelColor(x,y+dy,color)
                                        
                            self.probe_images[i].setPixmap(QPixmap.fromImage(imQt).scaledToWidth(100).scaledToHeight(800))
            
            if self.init_anchors[self.day-1] == False:
                #allows tip anchors to be changed after they are set initially
                self.init_anchors[self.day-1] = True
            
    def selectBoundary(self, probe, border_index):
        
        probe = probe + str(self.day)
        self.selected_probe = probe
        print(probe)
        self.selected_boundary = int(border_index)
        
        self.refreshImage(probe)

    
    def setDay(self, day):
        
        self.day = day
        self.day_selected = True

        if day == 1:
            self.set_day1_button.setStyleSheet("background-color: gray")
            self.set_day2_button.setStyleSheet("background-color: white")
        else:
            self.set_day1_button.setStyleSheet("background-color: white")
            self.set_day2_button.setStyleSheet("background-color: gray")

        self.probes = [p[:-1]+str(day) for p in self.probes]
        print(self.probes)
        
        self.loadData()
        
        
    def loadData(self):
        
        if not self.day_selected:
            self.setDay(1)

        if self.fname is None:
            self.fname, filt = QFileDialog.getOpenFileName(self, 
                caption='Select ccf coordinates file', 
                directory=self.current_directory,
                filter='*.csv')
        
        self.init_anchors = [False, False]
        
        fname = self.fname
        print(fname)

        self.current_directory = os.path.dirname(fname)
        self.output_file = os.path.join(self.current_directory, 'final_ccf_coordinates.csv')
        self.annotation_ccf_coordinates = os.path.join(self.current_directory, 'annotation_ccf_coordinates.csv')
        
        channel_vis_mod_files = glob.glob(os.path.join(self.current_directory, 'channel_visual_modulation*.npy'))
        session_dates = [cvm.split('_')[-1][:8] for cvm in channel_vis_mod_files]
        session_dates = np.unique(session_dates)
        session_dates = session_dates[np.argsort(session_dates)]
        print(session_dates)

        selected_session = session_dates[self.day-1]
        print(selected_session)
        self.anchor_points_file = os.path.join(self.current_directory, selected_session + '_coordinate_anchor_points.npy')
        
        if fname.split('.')[-1] == 'csv':

            self.setWindowTitle(os.path.dirname(fname))
            if self.data_loaded:
                self.df.loc[self.df['probe'].isin(self.probes), 'channels'] = 0
            else:
                self.df = pd.read_csv(fname)
                self.df['channels'] = 0

            #self.probes = [p for p in self.probes if p in self.df['probe'].unique()]
            #print(self.probes)

            if os.path.exists(self.annotation_ccf_coordinates):    
                self.df_ann = pd.read_csv(self.annotation_ccf_coordinates)
            else:
                print('Missing annotation_ccf_coordinates.csv')
                self.df_ann = []
            
            physiology_plots = glob.glob(os.path.join(self.current_directory, 'physiology_probe*'+selected_session + '*.png'))
            physiology_probes = [os.path.basename(p).split('_')[1] for p in physiology_plots]
            physiology_probes = ['Probe ' + p[-1] for p in physiology_probes]
            print(physiology_probes)
            #self.images = [QImage(p) for p in physiology_plots]
            self.images = {probe: QImage(p) for p,probe in zip(physiology_plots, physiology_probes)}


            if os.path.exists(self.anchor_points_file):
                self.anchor_points = np.load(self.anchor_points_file)
            else:
                self.anchor_points = np.zeros((572,6)) - 1
            
            self.data_loaded = True
            #if self.day_selected:
            self.refreshImage()
            

    def saveData(self):
        
        if self.data_loaded:
            self.df.to_csv(self.output_file)
            np.save(self.anchor_points_file, self.anchor_points)
            print('Saved data to ' + self.output_file)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())

