import numpy as np
import h5py as h5
import glob
from scipy.signal import butter, filtfilt, welch
from scipy.ndimage.filters import gaussian_filter1d
import os
import pandas as pd
from matplotlib import pyplot as plt


# mouse = '439183' 

# remote_server = '/mnt/sd5.2'
# outpath = '/mnt/md0/data/opt/production/' + mouse + '/images'


def align_to_physiology(session_path, outpath):
    probes = ('probeA', 'probeB', 'probeC', 'probeD', 'probeE', 'probeF')
    session_id = os.path.basename(session_path)
    channel_vis_mod_file = glob.glob(os.path.join(outpath, 'channel_visual_modulation_' + 
                                                          session_id + '.npy'))
    channel_vis_mod = np.load(channel_vis_mod_file[0], allow_pickle=True)[()]
    for probe_idx, probe in enumerate(probes[:]):
        try:
            rel_probe_path = session_id + '_' + probe +'_sorted/continuous'
            remote_directory = glob.glob(os.path.join(session_path, rel_probe_path + '/Neuropix*100.1'))

            print(remote_directory)
            remote_directory = remote_directory[0]

            raw_data = np.memmap(remote_directory + '/continuous.dat', dtype='int16')
            data = np.reshape(raw_data, (int(raw_data.size / 384), 384))
            
            start_index = int(2500 * 1000) 
            end_index = start_index+25000
           
            b,a = butter(3,[1/(2500/2),1000/(2500/2)],btype='band')
            
            D = data[start_index:end_index,:]*0.195

            for i in range(D.shape[1]):
               D[:,i] = filtfilt(b,a,D[:,i])
              
            M = np.median(D[:,370:])
               
            for i in range(D.shape[1]):
                D[:,i] = D[:,i] - M
                
            channels = np.arange(D.shape[1])
            nfft = 2048
                
            power = np.zeros((int(nfft/2+1), channels.size))

            for channel in range(D.shape[1]):
                sample_frequencies, Pxx_den = welch(D[:,channel], fs=2500, nfft=nfft)
                power[:,channel] = Pxx_den
                
            in_range = (sample_frequencies > 0) * (sample_frequencies < 10)

            fig = plt.figure(frameon=False)
            plt.clf()
            fig.set_size_inches(1,8)
            
            ax = plt.Axes(fig, [0., 0., 1., 1.])
            ax.set_axis_off()
            fig.add_axes(ax)
            
            S = np.std(D,0)
            S[S < 10] = np.nan
            S[S > 350] = np.nan
            
            mean_power = np.mean(power[in_range,:],0)
            ax.plot(mean_power/mean_power.max(),channels,'.',color='pink')

            unit_histogram = np.zeros((384,len(probes)),dtype='float')
            total_units = 0    
                 
            metrics_file = glob.glob(os.path.join(session_path, rel_probe_path + 
                '/Neuropix*100.0/metrics.csv'))

            print(metrics_file)
            metrics = pd.read_csv(metrics_file[0])
            
            #units = nwb['processing'][probe]['unit_list']
          
            #modulation_index = np.zeros((len(units),))
            #channels = np.zeros((len(units),))
            
            for unit_idx, unit in metrics.iterrows():
                
                #channel = nwb['processing'][probe]['UnitTimes'][str(unit)]['channel'].value
                channel = unit['peak_channel']
                   
                baseline = 1
                evoked = 1
                
                unit_histogram[channel,probe_idx] += 1 
        
                total_units += 1
                
            GF = gaussian_filter1d(unit_histogram[:,probe_idx]*100,2.5)
            ax.barh(np.arange(384),GF/GF.max(),height=1.0,alpha=0.1,color='teal')
            ax.plot(GF/GF.max(),np.arange(384),linewidth=3.0,alpha=0.78,color='teal') 
            
            ax2 = ax.twiny()
            ax2.plot(channel_vis_mod[probe[-1]], np.arange(384), linewidth=2.5, color='lightgreen')
            
            plt.ylim([0,384])
            plt.xlim([-0.05, 1])
            #ax.set_xlim([-5,800])
            #ax2.set_xlim([-0.05, 1])
         
            #if not os.path.exists(outpath):
            #    os.mkdir(outpath)
            
            fig.savefig(outpath + '/physiology_' + probe + '_' + session_id + '.png', dpi=300)   
            plt.close(fig)
        except Exception as e:
            print("Error processing probe {} due to error {}".format(probe, e))
        