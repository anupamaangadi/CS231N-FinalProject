import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
sys.path.append('/home/ubuntu/.local/lib/python2.7/site-packages/')
import pickle
import urllib
import io
import skimage.transform
#from gen_adver import FastGradient
from textwrap import wrap
import os
import sys

import multiprocessing as mp
    
import theano
import theano.tensor as T
from theano import pp
import time

import lasagne
from lasagne.layers import InputLayer, DenseLayer, DropoutLayer
from lasagne.layers.dnn import Conv2DDNNLayer as ConvLayer
from lasagne.layers.dnn import Pool2DDNNLayer as PoolLayer
from lasagne.layers import NonlinearityLayer
from lasagne.layers import DropoutLayer
from lasagne.layers import LocalResponseNormalization2DLayer as NormLayer
from lasagne.utils import floatX

# local
from diskreader import DiskReader

''' 
Implements bootstrapping on a class.
'''
class Bootstrap(object):
    
    def __init__(self, network = None, diskReader = None):
        self.network = network
        self.reader = diskReader if diskReader is not None else DiskReader()


    def forward(self, synset, nextsyn=None):

        ''' 
        Takes a synset and loads the necessary data from disk.  
        Returns activations from the 4096 feature layer for the given synset

        If given nextsyn, will request to load it up.
        ''' 

        images = self.reader.get(synset)
        self.reader.startRequest(nextsyn)

        N, C, H, W = images.shape
        features = np.zeros (N, 4096)

        for n in xrange(0, N, batch_size):

            curSet = images[n:n+batch_size, :, :, :]
            features[n:n+batch_size, :] = np.array(lasagne.layers.get_output(
                                                    net['fc6'], curSet, deterministic=True).eval(), 
                                                    dtype=np.float32)

        return curSet, features


    def sample (features, method='l2', k=300, num_samples=1000):
        '''  
        Bootstraps on the input space using the given method.

        Params:
        - features : a matrix of feature vectors, with the first dimension N.  

        Returns:
        - samples: the set of bootstrapped size-k samples
        '''
        N = features.shape[0]
        mean_img = np.mean (features, axis=0)
        samples = np.zeros(num_samples)

        if method == 'l2':
            features -= mean_img

            for i in xrange(num_samples):
                # draw k samples
                indices = np.random.choice(np.arange(N), size=k, replace=True)
                samp = features[indices] 
                # find l2 distances to mean (0)
                samp_l2 = np.sum(samp*samp) / N
                samples[i] = samp_l2

        return samples            


#-------------
def build_model(input_var,batch_size = None):
    net = {}
    net['input'] = InputLayer((batch_size, 3, 224, 224),input_var=input_var)
    net['conv1_1'] = ConvLayer(
        net['input'], 64, 3, pad=1)
    net['conv1_2'] = ConvLayer(
        net['conv1_1'], 64, 3, pad=1)
    net['pool1'] = PoolLayer(net['conv1_2'], 2)
    net['conv2_1'] = ConvLayer(
        net['pool1'], 128, 3, pad=1)
    net['conv2_2'] = ConvLayer(
        net['conv2_1'], 128, 3, pad=1)
    net['pool2'] = PoolLayer(net['conv2_2'], 2)
    net['conv3_1'] = ConvLayer(
        net['pool2'], 256, 3, pad=1)
    net['conv3_2'] = ConvLayer(
        net['conv3_1'], 256, 3, pad=1)
    net['conv3_3'] = ConvLayer(
        net['conv3_2'], 256, 3, pad=1)
    net['conv3_4'] = ConvLayer(
        net['conv3_3'], 256, 3, pad=1)
    net['pool3'] = PoolLayer(net['conv3_4'], 2)
    net['conv4_1'] = ConvLayer(
        net['pool3'], 512, 3, pad=1)
    net['conv4_2'] = ConvLayer(
        net['conv4_1'], 512, 3, pad=1)
    net['conv4_3'] = ConvLayer(
        net['conv4_2'], 512, 3, pad=1)
    net['conv4_4'] = ConvLayer(
        net['conv4_3'], 512, 3, pad=1)
    net['pool4'] = PoolLayer(net['conv4_4'], 2)
    net['conv5_1'] = ConvLayer(
        net['pool4'], 512, 3, pad=1)
    net['conv5_2'] = ConvLayer(
        net['conv5_1'], 512, 3, pad=1)
    net['conv5_3'] = ConvLayer(
        net['conv5_2'], 512, 3, pad=1)
    net['conv5_4'] = ConvLayer(
        net['conv5_3'], 512, 3, pad=1)
    net['pool5'] = PoolLayer(net['conv5_4'], 2)
    net['fc6'] = DenseLayer(net['pool5'], num_units=4096)

    # Finish at the 4096 level
    return net


def load_data():
    model = pickle.load(open('../weights/vgg19.pkl'))

    classes = model['synset words']
    mean_image= model['mean value']
    
    return model, classes, mean_image

def prepare_vgg16():

    input_var = T.tensor4('inputs') 
    net = build_model(input_var,batch_size=batch_size)
    # Load vgg(16) weights
    model, classes, mean_image = load_data()
    # update only up to the fully connected layer
    lasagne.layers.set_all_param_values(net['fc6'], model['param values'][:-6])
    return net, mean_image


batch_size = 96
if __name__ == '__main__':
    
    synsets = ['n02105056']
    if sys.argv[1] == '-p' or sys.argv[1] == '--pipe': # pipe in synsets to use to stdin.
        synsets = sys.stdin.read().split('\n')[:-1]


    net, mean_image = prepare_vgg16()
    boot = Bootstrap(net)

    syn = synset[0]        
    for i in xrange(1, len(synsets)):
        t0 = time.time()
        current, features = boot.forward(syn, synsets[i], batch_size)
        samples = boot.sample() 
        with open("{0}_samples".format(syn)) as f:
            pickle.dump(samples, f)
        t1 = time.time()
        print "took {0:.3f} seconds to run syns {1}".format(t1 - t0, syn)
        syn = synsets[i]
