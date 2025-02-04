import vtk

import numpy as np
import pandas as pd
import os

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  

from scipy.spatial.distance import euclidean


def loadVolume(fname, _dtype='u1'):

    """
    Loads an OPT volume file in Drishti format

    Parameters
    ===========
    fname - filename (string)
    dtype - data type (default = unsigned 8-bit integer)

    Returns
    ========
    volume - 3-dimensional np.ndarray

    """
        
    dtype = np.dtype(_dtype)

    volume = np.fromfile(fname, dtype) # read it in
    
    z_size = np.sum([volume[1], volume[2] << pow(2,3)])
    x_size = np.sum([(val << pow(2,i+1)) for i, val in enumerate(volume[8:4:-1])])
    y_size = np.sum([(val << pow(2,i+1)) for i, val in enumerate(volume[12:8:-1])])
    
    fsize = np.array([z_size, x_size, y_size]).astype('int')

    volume = np.reshape(volume[13:], fsize) # remove 13-byte header and reshape
    
    return volume

def define_transform(source_landmarks, target_landmarks, volume_size=[1024, 1024, 1023]):

    """
    Defines a non-linear warp between a set of source and target landmarks

    Parameters
    ==========
    source_landmarks - np.ndarray (N x 3)
    target_landmarks - np.ndarray (N x 3)
    volume_size - list of x, y, z max dimensions

    Returns
    =======
    transform - vtkThinPlateSplineTransform

    """

    transform = vtk.vtkThinPlateSplineTransform()

    source_points = vtk.vtkPoints()
    target_points = vtk.vtkPoints()

    for x in [0,volume_size[0]]:
        for y in [0,volume_size[1]]:
            for z in [0,volume_size[2]]:
                source_points.InsertNextPoint([z,x,y])
                target_points.InsertNextPoint([z,x,y])

    for i in range(source_landmarks.shape[0]):
        if source_landmarks[i,0] > -1 and target_landmarks[i,0] > -1:
            source_points.InsertNextPoint(source_landmarks[i,:])
        
    for i in range(target_landmarks.shape[0]):
        if source_landmarks[i,0] > -1 and target_landmarks[i,0] > -1:
            target_points.InsertNextPoint(target_landmarks[i,:])

    transform.SetBasisToR() # for 3D transform
    transform.SetSourceLandmarks(source_points)
    transform.SetTargetLandmarks(target_points)
    transform.Update()

    return transform



def plot_transform(source_landmarks, target_landmarks):

    """
    Creates a figure showing the translation between
    source and target landmarks

    Parameters
    ==========
    source_landmarks - np.ndarray (N x 3)
    target_landmarks - np.ndarray (N x 3)
    volume_size - list of x, y, z max dimensions

    Returns
    =======
    fig - figure handle

    """

    fig = plt.figure(2)
    plt.clf()
    ax = fig.add_subplot(111, projection='3d')

    ok_points = source_landmarks[:,0] > 0

    ax.scatter(source_landmarks[ok_points,0],source_landmarks[ok_points,1],
               -source_landmarks[ok_points,2],s=4,c='tan')

    distances = []

    for i in np.where(ok_points)[0]:
        distances.append( euclidean(source_landmarks[i,:], target_landmarks[i,:]))
        
        ax.plot3D([source_landmarks[i,0],target_landmarks[i,0]],
                 [ source_landmarks[i,1],target_landmarks[i,1]],
                   [-source_landmarks[i,2],-target_landmarks[i,2]]
                  ,'-k',alpha=0.35)

    plt.xlabel('AP')
    plt.ylabel('LR')
    ax.set_zlabel('DV')

    plt.show()

    return fig


def transform_probe_coordinates(transform, probe_annotations, labels, volume, 
    structure_tree, save_path=None, save_figures=False):

    """
    Creates a figure showing the translation between
    source and target landmarks

    Parameters
    ==========
    transform - vtkThinPlateSplineTransform
    probe_annotations - pd.DataFrame with original coordinates
    plot - boolean (generates plots if True)

    Returns
    =======
    df - pd.DataFrame containing transformed coordinates + structure IDs

    """

    if save_figures:
        save_prefix = os.path.basename(save_path) + '_'
        fig1 = plt.figure(147142)
        plt.clf()
        ax1 = fig1.add_subplot(111, projection='3d')
        
        fig2 = plt.figure(147143)
        plt.clf()

    colors = ('red', 'orange', 'brown', 'green', 'blue', 'purple',
              'red', 'orange', 'brown', 'green', 'blue', 'purple')

    probes = ('Probe A1', 'Probe B1', 'Probe C1', 'Probe D1', 'Probe E1', 'Probe F1',
              'Probe A2', 'Probe B2', 'Probe C2', 'Probe D2', 'Probe E2', 'Probe F2')
    
    probes_short = ('A1', 'B1', 'C1', 'D1', 'E1', 'F1',
                    'A2', 'B2', 'C2', 'D2', 'E2', 'F2')

    origin = np.array([-35, 42, 217],dtype='int')
    scaling = np.array([1160/1023,  1140/940, 800/590])

    df_columns = ['probe','structure_id', 'A/P','D/V','M/L']

    df = pd.DataFrame(columns = df_columns)
    
    df_a = pd.DataFrame(columns = df_columns)

    for probe_idx, probe in enumerate(probes):
        
        x = probe_annotations[probe_annotations.probe_name == probe].ML
        y = probe_annotations[probe_annotations.probe_name == probe].DV
        z = probe_annotations[probe_annotations.probe_name == probe].AP

        if len(z) > 0:
        
            data = np.vstack((z,y,x)).T
            data_a = np.copy(data)
            print(data_a.shape)
            datamean = data.mean(axis=0)
            D = data - datamean
            m1 = np.min(D[:,1]) * 2
            m2 = np.max(D[:,1]) * 2
            uu,dd,vv = np.linalg.svd(D)

            linepts = vv[0] * np.mgrid[-200:200:0.7][:,np.newaxis]
            linepts += datamean
            
            if linepts[-1,1] - linepts[0,1] < 0:
                linepts = np.flipud(linepts)
             
            if save_figures:
                ax1.scatter(z,x,-y,c=colors[probe_idx], s=5, alpha=0.95)
                ax1.plot3D(linepts[:,0],linepts[:,2],-linepts[:,1],color=colors[probe_idx], alpha=0.5)
                plt.xlabel('A/P')
                plt.ylabel('M/L')

            intensity_values = np.zeros((linepts.shape[0],40))
            structure_ids = np.zeros((linepts.shape[0],))
            ccf_coordinates = np.zeros((linepts.shape[0],3))
            
            
            for j in range(linepts.shape[0]):
                
                z2,x2,y2 = transform.TransformFloatPoint(linepts[j,np.array([0,2,1])])
                
                ccf_coordinate = (np.array([1023-z2,x2,y2]) - origin) * scaling
                ccf_coordinate = ccf_coordinate[np.array([0,2,1])]
                
                ccf_coordinate_mm = ccf_coordinate * 0.01
                
                ccf_coordinates[j,:] = ccf_coordinate_mm
                

                try:
                    structure_ids[j] = int(labels[int(ccf_coordinate[0]),int(ccf_coordinate[1]),int(ccf_coordinate[2])]) - 1
                except IndexError:
                    structure_ids[j] = -1
                
                for k in range(-20,20):
                    try:
                        intensity_values[j,k+20] = (volume[int(linepts[j,0]),int(linepts[j,1]+k),int(linepts[j,2]+k)])
                    except IndexError:
                        pass
                          
            data = {'probe': [probes[probe_idx]]*linepts.shape[0], 
                    'structure_id': structure_ids.astype('int'), 
                    'A/P' : np.around(ccf_coordinates[:,0],3), 
                    'D/V' : np.around(ccf_coordinates[:,1],3), 
                    'M/L' : np.around(ccf_coordinates[:,2],3) 
                    }
            
            probe_df = pd.DataFrame(data)
        
            df = pd.concat((df, probe_df) ,ignore_index=True)
            
            #get the ccf coordinates of transformed annotation points
            intensity_values_a = np.zeros((data_a.shape[0],40))
            structure_ids_a = np.zeros((data_a.shape[0],))
            ccf_coordinates_a = np.zeros((data_a.shape[0],3))
            
            for j in range(data_a.shape[0]):
                
                za,xa,ya = transform.TransformFloatPoint(data_a[j,np.array([0,2,1])])
                
                ccf_coordinate_a = (np.array([1023-za,xa,ya]) - origin) * scaling
                ccf_coordinate_a = ccf_coordinate_a[np.array([0,2,1])]
                
                ccf_coordinate_a_mm = ccf_coordinate_a * 0.01
                
                ccf_coordinates_a[j,:] = ccf_coordinate_a_mm
                
                try:
                    structure_ids_a[j] = int(labels[int(ccf_coordinate_a[0]),int(ccf_coordinate_a[1]),int(ccf_coordinate_a[2])]) - 1
                except IndexError:
                    structure_ids_a[j] = -1
                
                for k in range(-20,20):
                    try:
                        intensity_values_a[j,k+20] = (volume[int(data_a[j,0]),int(data_a[j,1]+k),int(data_a[j,2]+k)])
                    except IndexError:
                        pass
            
            data_a = {
                'probe': [probes[probe_idx]]*data_a.shape[0], 
                'structure_id': structure_ids_a.astype('int'), 
                'A/P' : np.around(ccf_coordinates_a[:,0],3), 
                'D/V' : np.around(ccf_coordinates_a[:,1],3), 
                'M/L' : np.around(ccf_coordinates_a[:,2],3)
                }
            
            probe_df_a = pd.DataFrame(data_a)
        
            df_a = pd.concat((df_a, probe_df_a) ,ignore_index=True)
            
            if save_figures:
                plt.figure(147143)
                plt.subplot(1,24,probe_idx*2+1)
                plt.imshow(intensity_values, cmap='gray',aspect='auto')
                plt.plot([20,20],[0,j],'-r')
                plt.axis('off')
                plt.title(probes_short[probe_idx])

                fig = plt.figure(frameon=False)
                fig.set_size_inches(1,8)
                
                ax = plt.Axes(fig, [0., 0., 1., 1.])
                ax.set_axis_off()
                fig.add_axes(ax)
                
                ax.imshow(intensity_values, cmap='gray',aspect='auto')

                fig.savefig(os.path.join(save_path, save_prefix + probe + '.png'), dpi=300)    
                
                plt.close(fig)
                    
                borders = np.where(np.abs(np.diff(structure_ids)) > 0)[0]
                jumps = np.concatenate((np.array([5]),np.diff(borders)))
                borders = borders[jumps > 6]
                
                for border in borders[::1]:
                    plt.plot([0,40],[border,border],'-',color='white',alpha=0.5)
                    
                plt.subplot(1,24,probe_idx*2+2)
                for border in borders[::1]:
                    plt.text(0,j-border-1,structure_tree[structure_tree.index == structure_ids[border-1]]['acronym'].iloc[0])
                    
                plt.text(0,0,structure_tree[structure_tree.index == structure_ids[-1]]['acronym'].iloc[0])
                plt.ylim([0,j+1])
                plt.axis('off')

    if save_figures:
        fig1.savefig(os.path.join(save_path, save_prefix + 'probe_line_fits.png'), dpi=300)
        fig2.savefig(os.path.join(save_path, save_prefix + 'probe_tracks.png'), dpi=300)

    return df, df_a


def run_volume_registration(mouse, opt_directory, scan_type='fluor'):

#if __name__ == "__main__":

    #prefix = '/mnt/md0/data/opt/production/'
    #prefix = base_opt_directory
    #mouse = '495662'

    #scan_type = 'fluor'

    fname = os.path.join(opt_directory, 'probe_annotations.csv')
    probe_annotations = pd.read_csv(fname, index_col = 0)

    volume = loadVolume(os.path.join(opt_directory,'mouse' + mouse +'_' + scan_type + '.pvl.nc.001'))
    #template = loadVolume('/mnt/md0/data/opt/template_brain/template_fluor.pvl.nc.001')
    #template = loadVolume(r"\\allen\programs\mindscope\workgroups\np-behavior\template_fluor.pvl.nc.001")
    template = loadVolume(r"C:\Users\svc_ccg\Desktop\Data\Atlas\template_fluor.pvl.nc.001")
    # template = loadVolume(r"D:\CCF_temp\template_fluor.pvl.nc.001")
    
    #labels = np.load('/mnt/md0/data/opt/annotation_volume_10um_by_index.npy')
    #labels = np.load(r"\\allen\programs\mindscope\workgroups\np-behavior\annotation_volume_10um_by_index.npy")
    labels = np.load(r"C:\Users\svc_ccg\Desktop\Data\Atlas\annotation_volume_10um_by_index.npy")
    # labels = np.load(r"D:\CCF_temp\annotation_volume_10um_by_index.npy")

    source_landmarks = np.load(os.path.join(opt_directory, 'landmark_annotations.npy'))
    #arget_landmarks = np.load('/mnt/md0/data/opt/template_brain/landmark_annotations.npy')
    target_landmarks = np.load(r"\\allen\programs\mindscope\workgroups\np-behavior\template_landmark_annotations.npy")

    #structure_tree = pd.read_csv('/mnt/md0/data/opt/template_brain/ccf_structure_tree_2017.csv')
    structure_tree = pd.read_csv(r"\\allen\programs\mindscope\workgroups\np-behavior\ccf_structure_tree_2017.csv")

    output_file = os.path.join(opt_directory,'initial_ccf_coordinates.csv')
    
    output_file_a = os.path.join(opt_directory,'annotation_ccf_coordinates.csv')

    source_landmarks = source_landmarks[:,np.array([2,0,1])]
    target_landmarks = target_landmarks[:,np.array([2,0,1])]

    transform = define_transform(source_landmarks, target_landmarks)

    fig = plot_transform(source_landmarks, target_landmarks)
    fig.savefig(os.path.join(opt_directory, 'transform_plot.png'))

    df, df_a = transform_probe_coordinates(transform, probe_annotations, 
        labels, volume, structure_tree, opt_directory, save_figures=True)

    df.to_csv(output_file)
    
    df_a.to_csv(output_file_a)

