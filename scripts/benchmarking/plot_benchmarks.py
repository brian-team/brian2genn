import matplotlib.pyplot as plt
import numpy as np

import pandas
import seaborn as sns
data = pandas.read_csv('benchmarks.txt', sep='\t', header=None,
                       names=['neurons', 'synapses', 'device', 'threads',
                              'spikemon', 'run', 'time'],
                       dtype={'spikemon': bool, 'neurons': int, 'synapses': int,
                              'threads': int, 'run': bool, 'time': float})
def assign_label(row):
    device = row['device']
    if device == 'cpp_standalone':
        device = 'C++ standalone'
    threads = row['threads']
    if threads == -1:
        suffix = ' (CPU)'
    elif threads == 0:
        suffix = ''
    else:
        suffix = '(%d threads)' % threads
    return device + suffix

data['label'] = data.apply(assign_label, axis=1)

def do_plot(device, threads, run, spikemon, color, label, prep_time=None, add_text=False):
    norun_subset = data[(data['device'] == device) &
                       (data['threads'] == threads) &
                       (data['run'] == False) &
                       (data['spikemon'] == spikemon)]
    norun_mean = norun_subset[['neurons', 'time']].groupby(['neurons']).mean()
    norun_mean.reset_index(level=0, inplace=True)
    data_subset = data[(data['device'] == device) &
                       (data['threads'] == threads) &
                       (data['run'] == run) &
                       (data['spikemon'] == spikemon)]
    data_subset = pandas.merge(data_subset, norun_mean, on=['neurons'])
    data_subset['normalized_time'] = data_subset['time_x'] - data_subset['time_y']
    mean_data = data_subset[['neurons', 'time_x', 'normalized_time']].groupby(['neurons']).mean()
    mean_data.reset_index(level=0, inplace=True)

    if prep_time == 'subtract':
        time_key = 'normalized_time'
    else:
        time_key = 'time_x'
    plt.plot('neurons', time_key, 'o', data=data_subset, color=color, label='')
    plt.plot('neurons', time_key, data=mean_data, color=color, label=label)
    if add_text:
        for neuron in add_text:
            time = mean_data[mean_data['neurons'] == neuron][time_key]
            if not len(time) == 1:
                continue
            time = np.array(time)[0]
            plt.text(neuron, time*1.075, '%.1fs' % time, color=color, weight='bold')

    if prep_time == 'extra':
        plt.plot('neurons', 'time', ':', data=norun_mean, color=color, label='')
    

plt.figure()
do_plot('genn', 0, True, True, 'lightblue', 'GeNN (GPU)')
do_plot('genn', -1, True, True, 'steelblue', 'GeNN (CPU)')
do_plot('cpp_standalone', 0, True, True, 'olive', 'C++ standalone')
do_plot('cpp_standalone', 2, True, True, 'forestgreen', 'C++ standalone (2 threads)')
do_plot('cpp_standalone', 4, True, True, 'limegreen', 'C++ standalone (4 threads)')
do_plot('cpp_standalone', 8, True, True, 'lawngreen', 'C++ standalone (8 threads)')
plt.legend(frameon=False, loc='best')
plt.title('Total runtime for 5s biological time')
plt.gca().set(xscale='log', yscale='log', xlabel='number of neurons', ylabel='time (s)')
plt.savefig('benchmarks1.png', dpi=300)

annotations = [1450, 12700, 125200]
plt.figure()
do_plot('genn', 0, True, True, 'lightblue', 'GeNN (GPU)', add_text=annotations)
do_plot('cpp_standalone', 0, True, True, 'olive', 'C++ standalone', add_text=annotations)
do_plot('cpp_standalone', 8, True, True, 'lawngreen', 'C++ standalone (8 threads)', add_text=annotations)
plt.legend(frameon=False, loc='best')
plt.title('Total runtime for 5s biological time')
plt.gca().set(xscale='log', yscale='log', xlabel='number of neurons', ylabel='time (s)')
plt.savefig('benchmarks2.png', dpi=300)

plt.figure()
do_plot('genn', 0, True, True, 'lightblue', 'GeNN (GPU)', prep_time='extra', add_text=annotations)
do_plot('cpp_standalone', 0, True, True, 'olive', 'C++ standalone', prep_time='extra', add_text=annotations)
do_plot('cpp_standalone', 8, True, True, 'lawngreen', 'C++ standalone (8 threads)', prep_time='extra', add_text=annotations)
plt.legend(frameon=False, loc='best')
plt.title('Total runtime for 5s biological time')
plt.gca().set(xscale='log', yscale='log', xlabel='number of neurons', ylabel='time (s)')
plt.savefig('benchmarks3.png', dpi=300)

plt.figure()
plt.axhline(5, color='gray', linestyle=':')
do_plot('genn', 0, True, True, 'lightblue', 'GeNN (GPU)', prep_time='subtract', add_text=annotations)
do_plot('cpp_standalone', 0, True, True, 'olive', 'C++ standalone', prep_time='subtract', add_text=annotations)
do_plot('cpp_standalone', 8, True, True, 'lawngreen', 'C++ standalone (8 threads)', prep_time='subtract', add_text=annotations)

plt.legend(frameon=False, loc='best')
plt.title('Runtime only for 5s biological time')
plt.gca().set(xscale='log', yscale='log', xlabel='number of neurons', ylabel='time (s)')
plt.savefig('benchmarks4.png', dpi=300)

plt.figure()
plt.axhline(5, color='gray', linestyle=':')
do_plot('genn', 0, True, False, 'lightblue', 'GeNN (GPU)', prep_time='subtract', add_text=annotations)
do_plot('cpp_standalone', 0, True, False, 'olive', 'C++ standalone', prep_time='subtract', add_text=annotations)
do_plot('cpp_standalone', 8, True, False, 'lawngreen', 'C++ standalone (8 threads)', prep_time='subtract', add_text=annotations)

plt.legend(frameon=False, loc='best')
plt.title('Runtime only for 5s biological time (no monitors)')
plt.gca().set(xscale='log', yscale='log', xlabel='number of neurons', ylabel='time (s)')
plt.savefig('benchmarks5.png', dpi=300)

plt.show()


