import numpy as np
import json
import ast
import glob
import argparse
import noise_models as noise_models
import datetime
from chainer import optimizers
import os
import pandas as pd


parser = argparse.ArgumentParser(description='Driver for 5G Experiments')
parser.add_argument('--showfig', '-g', dest='showfig', action='store_true',
                    help='Show the figure')
parser.add_argument('--configfile', '-c', dest='configfile', type=str,
                    help='Which config file to use')
parser.add_argument('--configfile_dir', '-d', dest='configfile_dir', type=str,
                    help='Which directory of config files to use')
parser.add_argument('--startidx', '-s', dest='startidx', type=int,
                    help='Which file to start at')
parser.add_argument('--endidx', '-e', dest='endidx', type=int,
                    help='Which file to end at')
parser.add_argument('--verbose', '-v', dest='verbose', action='store_true', 
                    help='Print out verbose')
args = parser.parse_args()

showfig = args.showfig
configfile = args.configfile
startidx = args.startidx
endidx = args.endidx
configfile_dir = args.configfile_dir
startidx = args.startidx
endidx = args.endidx
verbose = args.verbose

import utilities as util
import models as models
import data_generation as data_generation
import plotting as plotting


use_dir = False 


if configfile:
    cfg_fns = [configfile]
elif configfile_dir:
    if configfile_dir[-1] != '/':
        configfile_dir += '/'
    cfg_fns = glob.glob(configfile_dir + '*')
    cfg_fns.sort()
    if endidx:
        assert startidx <= endidx, "Startidx is greater than endidx...not judging, just letting you know..."
        cfg_fns = cfg_fns[startidx:endidx+1]
elif use_dir:
    # cfg_fns = "config_files/noise_model.ini"
    cfg_fns = glob.glob('exp_bm_gaussian_11am/*')
    cfg_fns.sort()
    if endidx:
        assert startidx <= endidx, "Startidx is greater than endidx...not judging, just letting you know..."
        cfg_fns = cfg_fns[startidx:endidx]
    #cfg_fns = glob.glob('test_batch/*')
else:
    #cfg_fns = ["config_files/noise_baseModel.ini"]
    #cfg_fns = ["config_files/broken_structured.ini"]
    cfg_fns = ["config_files/baseModel2D.ini"]
    #cfg_fns = ["expset_08312016_10pm/exp1_setting3.ini"]*1 + ["expset_08312016_10pm/exp1_setting10.ini"]*1

df_all = pd.DataFrame()

for cfg_fn in cfg_fns:
    if verbose:
        print "CFG: ", cfg_fn
    config, dir_name = util.load_configuration(cfg_fn)

    params = util.create_param_dict(config)

    df = pd.DataFrame(util.parseParams(params))


    all_predY = None
    all_error = None
    mean_errors = []
    std_errors = []
    for iter_number in range(params['exp_details__num_iterations_per_setting']):
        # generate mobile points, base stations, and angles
        mobiles, bases, angles = data_generation.generate_data(params['data__num_pts'],
                                                               params['data__num_stations'],
                                                               params ['data__ndims'],
                                                               pts_r=3.9, bs_r=4,
                                                               bs_type=params['data__bs_type'], points_type="random")





        # IMPORTANT: remember to add noise before replicating data (e.g., for snbp-mlp)
        if params['noise__addnoise_train']:
            angles = noise_models.add_noise_dispatcher(angles, params['noise__noise_model'], params['data__ndims'], base_idxs=params['noise__bases_to_noise'], 
                                                            noise_params=params['noise__noise_params'])

        if params['NN__type'] == 'snbp-mlp':
            rep_idxs = [[0,2],[1,2]]
            angles = data_generation.replicate_data(angles, params['data__ndims'],  rep_idxs)


        # split data
        trainXs, trainY, testXs, testY = util.test_train_split(angles, mobiles)


        if params['NN__type'] == "bmlp":
            model = models.BaseMLP(np.hstack(trainXs).shape[1], params['NN__network_size'],
                                   params['data__ndims'])
        elif params['NN__type'] == 'smlp':
            model = models.StructuredMLP(None, params['NN__network_size'][0],
                                         params['NN__network_size'][1], params['data__ndims'],
                                         [[0,1],[2,3]])
        elif params['NN__type'] == 'snbp-mlp':
            model = models.NBPStructuredMLP(trainXs[0].shape[1], params['NN__network_size'][0],
                                            params['NN__network_size'][1], params['data__ndims'],
                                            len(rep_idxs))

        # train model
        loss = model.trainModel(trainXs, trainY, testXs, testY,
                                   n_epoch=params['NN__n_epochs'],
                                   batchsize=params['NN__batchsize'],
                                   max_flag=params['NN__take_max'],
                                   verbose=verbose)

        f = open(dir_name + 'loss_iteration%d.txt' % (iter_number), 'w')
        f.write("%f" % (loss))
        f.close()


        # generate mobile points, base stations, and angles
        mobiles, bases, angles = data_generation.generate_data(50*50,
                                                               params['data__num_stations'],
                                                               params ['data__ndims'],
                                                               pts_r=3, bs_r=4,
                                                               bs_type=params['data__bs_type'], points_type="grid")



        selected_point = np.random.randint(50*50)

        angles = angles[selected_point,:]
        trueTestY = mobiles[selected_point,:]
        mobiles = mobiles[selected_point,:]


        angles = np.tile(angles, (params['data__numsamplesperpoints'],1))
        mobiles = np.tile(mobiles, (params['data__numsamplesperpoints'],1))



        if params['noise__addnoise_test']:
            angles = noise_models.add_noise_dispatcher(angles, params['noise__noise_model'], params['data__ndims'], base_idxs=params['noise__bases_to_noise'], 
                                                            noise_params=params['noise__noise_params'])


        

        # if we are in noise experiment 2 we want to average all of the points before running through the model
        if params['data__noiseyexperimentnumber'] == 2:
            angles = np.mean(angles, axis=0)
            mobiles = np.mean(mobiles, axis=0)




        if params['NN__type'] == 'snbp-mlp':
            angles = data_generation.replicate_data(angles, params['data__ndims'],  rep_idxs)


        # print "TY1: ", mobiles.shape

        trainXs, trainY, testXs, testY = util.test_train_split(angles, mobiles, 0.)

        # print "TY2: ", testY.shape
        # assert False
        

        # test model
        predY, error = model.testModel(testXs, testY)

        # print "BEFORE: ", predY.shape
        # print "BEFORE: ", error.shape

        # if we are in noise experiment 1 we want to average the output from the model
        if params['data__noiseyexperimentnumber'] == 1:
            predY = np.mean(predY, axis=0)
            predY = predY.reshape(len(predY), 1)
            error = np.mean(error)

            # print "AFTER: ", predY.shape
            # print "AFTER: ", error

        # assert False

        error = error.reshape(1,1)


        f = open(dir_name + 'error_iteration%d.txt' % iter_number, 'w')
        f.write("Mean Error: %f\n" % (np.mean(error)))
        f.write("Error Standard Deviation: %f\n" % (np.std(error)))
        f.close()

        mean_errors.append(np.mean(error))
        std_errors.append(np.std(error))


        testY = trueTestY.reshape(len(trueTestY),1)
        print "A: ", testY.shape
        print "B: ", predY.shape
        print "C: ", error.shape
        plotting.plot_error(testY, predY, error, bases,
                            "Num Stations: %d" % (params['data__num_stations']),
                            params['exp_details__save'], dir_name, iter_number)

        if all_predY == None:
            # all_predY = np.zeros((predY.shape[0], predY.shape[1], params['exp_details__num_iterations_per_setting']))
            all_predY = np.zeros((predY.shape[0], predY.shape[1], 1))
        if all_error == None:
            # all_error = np.zeros((error.shape[0], params['exp_details__num_iterations_per_setting']))
            all_error = np.zeros((error.shape[0], 1))

        all_predY[:,:,iter_number] = predY
        all_error[:,iter_number] = error

    f = open(dir_name + 'error_average.txt', 'w')
    f.write("Mean Error: %f\n" % (np.mean(mean_errors)))
    f.close()

    f = open(dir_name + 'resultsdata.npz', 'w')
    np.savez(f, all_predY=all_predY, all_error=all_error)
    f.close()

    df['mean_err'] = np.mean(mean_errors)
    df['std_err'] = np.mean(std_errors)
    df_all = df_all.append(df, ignore_index=True)

    # print out warning if figures not saved
    if params['exp_details__save']:
        print "****** Figures saved to directory %s ********" % (dir_name)
    else:
        print "****** Not saving!!!! ****** "
        print "If you would like to save, change the config file"

res_dir_folder = 'aggregated_results'
if not os.path.exists(res_dir_folder):
    os.makedirs(res_dir_folder)

res_dir_name = "%s/%s__%s.csv" % (res_dir_folder, config.get("exp_details", "setname"), datetime.datetime.now().strftime("%m_%d_%Y_%I:%M:%S%p"))
df_all.to_csv(res_dir_name)
