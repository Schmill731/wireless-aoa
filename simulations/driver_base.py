import numpy as np

import utilities as util
import models as models
import data_generation as data_generation
import plotting as plotting
import json
import ast

from chainer import optimizers



#plt.ion()

cfg_fn = "test1.ini"

config = util.load_configuration(cfg_fn)

params = {}
params['NN__type'] = config.get("NN", "type")
params['NN__network_size'] = json.loads(config.get("NN", "network_size"))
params['data__num_pts'] = int(config.get("data", "num_pts"))
params['data__ndims'] = int(config.get("data", "ndims"))
params['data__num_stations'] = int(config.get("data", "num_stations"))
params['data__bs_type'] = config.get("data", "bs_type")
params['exp_details__save'] = ast.literal_eval(config.get("exp_details", "save"))


# TODO: params (for now, we'll get from config file after)
bs_type = "colinear"
ndims = 2
num_pts = 2000
num_stations = 3

# generate mobile points, base stations, and angles
mobiles, bases, angles = data_generation.generate_data(params['data__num_pts'], params['data__num_stations'], params['data__ndims'], pts_r=3.9, bs_r=4, bs_type=params['data__bs_type'])

# split data
trainXs, trainY, testXs, testY = util.test_train_split(angles, mobiles)


# TODO: initiate model
# model = models.BaseMLP(np.hstack(trainXs).shape[1], [500,50,200,50], params['data__ndims'])
model = models.BaseMLP(np.hstack(trainXs).shape[1], params['NN__network_size'], params['data__ndims'])

# model = models.StructuredMLP(trainXs[0].shape[1]/2, (500,50), (200,50))

# Setup optimizer
optimizer = optimizers.Adam()
optimizer.setup(model)


# train model
model = models.train_model(model, trainXs, trainY, testXs, testY, n_epoch=1000, batchsize=200)

# test model
predY, error = models.test_model(model, testXs, testY)


plotting.plot_error(testY, predY, error, bases, "Num Stations: %d" % (params['data__num_stations']))
	



# TODO: write results file to directory
if params['exp_details__save']:
	print "****** NEED TO IMPLEMENT SAVING ********"
else:
	print "****** Not saving!!!! ****** "

# TODO: save figures to directory
if params['exp_details__save']:
	print "****** NEED TO IMPLEMENT SAVING ********"
else:
	print "****** Not saving!!!! ****** "





