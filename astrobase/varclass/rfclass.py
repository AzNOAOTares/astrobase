#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''rfclass.py - Waqas Bhatti (wbhatti@astro.princeton.edu) - Dec 2017
License: MIT. See the LICENSE file for more details.

Does variable classification using random forests. Two types of classification
are supported:

- Variable classification using non-periodic features: this is used to perform a
  binary classification between non-variable and variable. Uses the features in
  varclass/features.py and varclass/starfeatures.py.

- Periodic variable classification using periodic features: this is used to
  perform multi-class classification for periodic variables using the features
  in varclass/periodicfeatures.py and varclass/starfeatures.py. The classes
  recognized are listed in PERIODIC_VARCLASSES below and were generated from
  manual classification run on various HATNet, HATSouth and HATPI fields.

'''

#############
## LOGGING ##
#############

import logging
from datetime import datetime
from traceback import format_exc

# setup a logger
LOGGER = None
LOGMOD = __name__
DEBUG = False

def set_logger_parent(parent_name):
    globals()['LOGGER'] = logging.getLogger('%s.%s' % (parent_name, LOGMOD))

def LOGDEBUG(message):
    if LOGGER:
        LOGGER.debug(message)
    elif DEBUG:
        print('[%s - DBUG] %s' % (
            datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            message)
        )

def LOGINFO(message):
    if LOGGER:
        LOGGER.info(message)
    else:
        print('[%s - INFO] %s' % (
            datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            message)
        )

def LOGERROR(message):
    if LOGGER:
        LOGGER.error(message)
    else:
        print('[%s - ERR!] %s' % (
            datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            message)
        )

def LOGWARNING(message):
    if LOGGER:
        LOGGER.warning(message)
    else:
        print('[%s - WRN!] %s' % (
            datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            message)
        )

def LOGEXCEPTION(message):
    if LOGGER:
        LOGGER.exception(message)
    else:
        print(
            '[%s - EXC!] %s\nexception was: %s' % (
                datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                message, format_exc()
                )
            )


#############
## IMPORTS ##
#############

from time import time as unixtime
import glob
import os.path
import os
import shutil
import itertools

try:
    import cPickle as pickle
except:
    import pickle

try:
    from tqdm import tqdm
    TQDM = True
except:
    TQDM = False
    pass

import numpy as np
import numpy.random as npr
# seed the numpy random generator
# we'll use RANDSEED for scipy.stats distribution functions as well
RANDSEED = 0xdecaff
npr.seed(RANDSEED)

from scipy.stats import randint as sp_randint

# scikit imports
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import KFold, StratifiedKFold, RandomizedSearchCV
from sklearn.model_selection import train_test_split

from operator import itemgetter
from sklearn.metrics import r2_score, median_absolute_error, \
    precision_score, recall_score, confusion_matrix, f1_score

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


#######################
## UTILITY FUNCTIONS ##
#######################

# Utility function to report best scores
# modified from a snippet taken from:
# http://scikit-learn.org/stable/auto_examples/model_selection/plot_randomized_search.html
def gridsearch_report(results, n_top=3):
    for i in range(1, n_top + 1):
        candidates = np.flatnonzero(results['rank_test_score'] == i)
        for candidate in candidates:
            LOGINFO("Model with rank: {0}".format(i))
            LOGINFO("Mean validation score: {0:.3f} (std: {1:.3f})".format(
                  results['mean_test_score'][candidate],
                  results['std_test_score'][candidate]))
            LOGINFO("Parameters: {0}".format(results['params'][candidate]))



###################################
## NON-PERIODIC VAR FEATURE LIST ##
###################################

NONPERIODIC_FEATURES_TO_COLLECT = [
    'stetsonj',
    'stetsonk',
    'amplitude',
    'magnitude_ratio',
    'linear_fit_slope',
    'eta_normal',
    'percentile_difference_flux_percentile',
    'mad',
    'skew',
    'kurtosis',
    'mag_iqr',
    'beyond1std',
    'grcolor',
    'gicolor',
    'ricolor',
    'bvcolor',
    'jhcolor',
    'jkcolor',
    'hkcolor',
    'gkcolor',
    'propermotion',
]



########################
## FEATURE COLLECTION ##
########################

def collect_features(
        featuresdir,
        magcol,
        outfile,
        pklglob='varfeatures-*.pkl',
        featurestouse=NONPERIODIC_FEATURES_TO_COLLECT,
        maxobjects=None,
        labeldict=None,
        labeltype='binary',
):
    '''This collects variability features into arrays.

    featuresdir is the directory where all the varfeatures pickles are. Use
    pklglob to specify the glob to search for. varfeatures pickles contain
    objectids, a light curve magcol, and features as dict key-vals. The lcproc
    module can be used to produce these.


    magcol is the light curve magnitude col key to use when looking inside each
    varfeatures pickle.


    Each varfeature pickle can contain any combination of non-periodic, stellar,
    and periodic features; these must have the same names as elements in the
    list of strings provided in featurestouse.  This tries to get all the
    features listed in NONPERIODIC_FEATURES_TO_COLLECT by default. If
    featurestouse is not None, gets only the features listed in this kwarg
    instead.


    maxobjects controls how many pickles to process.


    If labeldict is not None, it must be a dict with the following key:val
    list:

    '<objectid>':<label value>

    for each objectid collected from the varfeatures pickles. This will turn the
    collected information into a training set for classifiers.

    Example: to carry out non-periodic variable feature collection of fake LCS
    prepared by fakelcs.generation, use the value of the 'isvariable' dict elem
    from fakelcs-info.pkl here, like so:

    labeldict={x:y for x,y in zip(fakelcinfo['objectid'],
                                  fakelcinfo['isvariable'])}

    labeltype is either 'binary' or 'classes' for binary/multi-class
    classification respectively.

    '''

    # list of input pickles generated by varfeatures in lcproc.py
    pklist = glob.glob(os.path.join(featuresdir, pklglob))

    if maxobjects:
        pklist = pklist[:maxobjects]


    # fancy progress bar with tqdm if present
    if TQDM:
        listiterator = tqdm(pklist)
    else:
        listiterator = pklist

    # go through all the varfeatures arrays

    feature_dict = {'objectids':[],'magcol':magcol, 'availablefeatures':[]}

    LOGINFO('collecting features for magcol: %s' % magcol)

    for pkl in listiterator:

        with open(pkl,'rb') as infd:
            varf = pickle.load(infd)

        # update the objectid list
        objectid = varf['objectid']
        if objectid not in feature_dict['objectids']:
            feature_dict['objectids'].append(objectid)

        thisfeatures = varf[magcol]

        if featurestouse and len(featurestouse) > 0:
            featurestoget = featurestouse
        else:
            featurestoget = NONPERIODIC_FEATURES_TO_COLLECT

        # collect all the features for this magcol/objectid combination
        for feature in featurestoget:

            # update the global feature list if necessary
            if ((feature not in feature_dict['availablefeatures']) and
                (feature in thisfeatures)):

                feature_dict['availablefeatures'].append(feature)
                feature_dict[feature] = []

            if feature in thisfeatures:

                feature_dict[feature].append(
                    thisfeatures[feature]
                )

    # now that we've collected all the objects and their features, turn the list
    # into arrays, and then concatenate them
    for feat in feature_dict['availablefeatures']:
        feature_dict[feat] = np.array(feature_dict[feat])

    feature_dict['objectids'] = np.array(feature_dict['objectids'])

    feature_array = np.column_stack([feature_dict[feat] for feat in
                                     feature_dict['availablefeatures']])
    feature_dict['features_array'] = feature_array


    # if there's a labeldict available, use it to generate a label array. this
    # feature collection is now a training set.
    if isinstance(labeldict, dict):

        labelarray = np.zeros(feature_dict['objectids'].size, dtype=np.int64)

        # populate the labels for each object in the training set
        for ind, objectid in enumerate(feature_dict['objectids']):

            if objectid in labeldict:

                # if this is a binary classifier training set, convert bools to
                # ones and zeros
                if labeltype == 'binary':

                    if labeldict[objectid]:
                        labelarray[ind] = 1

                # otherwise, use the actual class label integer
                elif labeltype == 'classes':
                    labelarray[ind] = labeldict[objectid]

        feature_dict['labels_array'] = labelarray


    feature_dict['kwargs'] = {'pklglob':pklglob,
                              'featurestouse':featurestouse,
                              'maxobjects':maxobjects,
                              'labeltype':labeltype}

    # write the info to the output pickle
    with open(outfile,'wb') as outfd:
        pickle.dump(feature_dict, outfd, pickle.HIGHEST_PROTOCOL)

    # return the feature_dict
    return feature_dict



#################################
## TRAINING THE RF CLASSIFIERS ##
#################################

def train_rf_classifier(
        collected_features,
        test_fraction=0.25,
        n_crossval_iterations=20,
        n_kfolds=5,
        crossval_scoring_metric='f1',
        classifier_to_pickle=None,
        nworkers=-1,
):

    '''This gets the best RF classifier after running cross-validation.

    - splits the training set into test/train samples
    - does KFold stratified cross-validation using RandomizedSearchCV
    - gets the randomforest with the best performance after CV
    - gets the confusion matrix for the test set

    Runs on the output dict from functions that produce dicts similar to that
    produced by collect_features.

    By default, this is tuned for binary classification. Change the
    crossval_scoring_metric to another metric (probably 'accuracy') for
    multi-class classification, e.g. for periodic variable classification. See
    the link below to specify the scoring parameter (this can either be a string
    or an actual scorer object):

    http://scikit-learn.org/stable/modules/model_evaluation.html#scoring-parameter

    '''

    if isinstance(collected_features,str) and os.path.exists(collected_features):
        with open(collected_features,'rb') as infd:
            fdict = pickle.load(infd)
    elif isinstance(collected_features, dict):
        fdict = collected_features
    else:
        LOGERROR("can't figure out the input collected_features arg")
        return None

    tfeatures = fdict['features_array']
    tlabels = fdict['labels_array']
    tfeaturenames = fdict['availablefeatures']
    tmagcol = fdict['magcol']
    tobjectids = fdict['objectids']


    # split the training set into training/test samples using stratification
    # to keep the same fraction of variable/nonvariables in each
    training_features, testing_features, training_labels, testing_labels = (
        train_test_split(
            tfeatures,
            tlabels,
            test_size=test_fraction,
            random_state=RANDSEED,
            stratify=tlabels
        )
    )

    # get a random forest classifier
    clf = RandomForestClassifier(n_jobs=nworkers,
                                 random_state=RANDSEED)


    # this is the grid def for hyperparam optimization
    rf_hyperparams = {
        "max_depth": [3,4,5,None],
        "n_estimators":sp_randint(100,2000),
        "max_features": sp_randint(1, 5),
        "min_samples_split": sp_randint(2, 11),
        "min_samples_leaf": sp_randint(2, 11),
    }

    # run the stratified kfold cross-validation on training features using our
    # random forest classifier object
    cvsearch = RandomizedSearchCV(
        clf,
        param_distributions=rf_hyperparams,
        n_iter=n_crossval_iterations,
        scoring=crossval_scoring_metric,
        cv=StratifiedKFold(n_splits=n_kfolds,
                           shuffle=True,
                           random_state=RANDSEED),
        random_state=RANDSEED
    )


    LOGINFO('running grid-search CV to optimize RF hyperparameters...')
    cvsearch_classifiers = cvsearch.fit(training_features,
                                        training_labels)

    # report on the classifiers' performance
    gridsearch_report(cvsearch_classifiers.cv_results_)

    # get the best classifier after CV is done
    bestclf = cvsearch_classifiers.best_estimator_
    bestclf_score = cvsearch_classifiers.best_score_
    bestclf_hyperparams = cvsearch_classifiers.best_params_

    # test this classifier on the testing set
    test_predicted_labels = bestclf.predict(testing_features)

    recscore = recall_score(testing_labels, test_predicted_labels)
    precscore = precision_score(testing_labels,test_predicted_labels)
    f1score = f1_score(testing_labels, test_predicted_labels)
    confmatrix = confusion_matrix(testing_labels, test_predicted_labels)

    # write the classifier, its training/testing set, and its stats to the
    # pickle if requested
    outdict = {'features':tfeatures,
               'labels':tlabels,
               'feature_names':tfeaturenames,
               'magcol':tmagcol,
               'objectids':tobjectids,
               'kwargs':{'test_fraction':test_fraction,
                         'n_crossval_iterations':n_crossval_iterations,
                         'n_kfolds':n_kfolds,
                         'crossval_scoring_metric':crossval_scoring_metric,
                         'nworkers':nworkers},
               'collect_kwargs':fdict['kwargs'],
               'testing_features':testing_features,
               'testing_labels':testing_labels,
               'training_features':training_features,
               'training_labels':training_labels,
               'best_classifier':bestclf,
               'best_score':bestclf_score,
               'best_hyperparams':bestclf_hyperparams,
               'best_recall':recscore,
               'best_precision':precscore,
               'best_f1':f1score,
               'best_confmatrix':confmatrix}


    if classifier_to_pickle:

        with open(classifier_to_pickle,'wb') as outfd:
            pickle.dump(outdict, outfd, pickle.HIGHEST_PROTOCOL)


    # return this classifier and accompanying info
    return outdict



def apply_rf_classifier(classifier,
                        varfeaturesdir,
                        outpickle,
                        maxobjects=None):
    '''This applys an RF classifier trained using train_rf_classifier
    to pickles in varfeaturesdir.

    classifier is the output dict or pickle from get_rf_classifier. This will
    contain a feature_names key that will be used to collect the features from
    the varfeatures pickles in varfeaturesdir.

    varfeaturesdir is a directory where varfeatures pickles generated by
    lcproc.parallel_varfeatures, etc. are located.

    outpickle is the pickle of the result dict generated by this function.

    '''

    if isinstance(classifier,str) and os.path.exists(classifier):
        with open(classifier,'rb') as infd:
            clfdict = pickle.load(infd)
    elif isinstance(classifier, dict):
        clfdict = classifier
    else:
        LOGERROR("can't figure out the input classifier arg")
        return None


    # get the features to extract from clfdict
    if 'feature_names' not in clfdict:
        LOGERROR("feature_names not present in classifier input, "
                 "can't figure out which ones to extract from "
                 "varfeature pickles in %s" % varfeaturesdir)
        return None

    # get the feature labeltype, pklglob, and maxobjects from classifier's
    # collect_kwargs elem.
    featurestouse = clfdict['feature_names']
    labeltype = clfdict['collect_kwargs']['labeltype']
    pklglob = clfdict['collect_kwargs']['pklglob']
    magcol = clfdict['magcol']


    # extract the features used by the classifier from the varfeatures pickles
    # in varfeaturesdir using the pklglob provided
    featfile = os.path.join(
        os.path.dirname(outpickle),
        'actual-collected-features.pkl'
        )

    features = collect_features(
        varfeaturesdir,
        magcol,
        featfile,
        pklglob=pklglob,
        featurestouse=featurestouse,
        maxobjects=maxobjects
    )

    # now use the trained classifier on these features
    bestclf = clfdict['best_classifier']

    predicted_labels = bestclf.predict(features['features_array'])

    # FIXME: do we need to use the probability calibration curves to fix these
    # probabilities? probably. figure out how to do this.
    predicted_label_probs = bestclf.predict_proba(
        features['features_array']
    )

    outdict = {
        'features':features,
        'featfile':featfile,
        'classifier':clfdict,
        'predicted_labels':predicted_labels,
        'predicted_label_probs':predicted_label_probs,
    }

    with open(outpickle,'wb') as outfd:
        pickle.dump(outdict, outfd, pickle.HIGHEST_PROTOCOL)

    return outdict



######################
## PLOTTING RESULTS ##
######################

def plot_training_results(classifier,
                          classlabels,
                          outfile):
    '''
    This plots the training results from the classifier run on the training set.

    - plots the confusion matrix
    - plots the feature importances
    - FIXME: plot the learning curves too, see:
             http://scikit-learn.org/stable/modules/learning_curve.html

    '''

    if isinstance(classifier,str) and os.path.exists(classifier):
        with open(classifier,'rb') as infd:
            clfdict = pickle.load(infd)
    elif isinstance(classifier, dict):
        clfdict = classifier
    else:
        LOGERROR("can't figure out the input classifier arg")
        return None

    confmatrix = clfdict['best_confmatrix']
    overall_feature_importances = clfdict['best_classifier'].feature_importances_
    feature_importances_per_tree = np.array([
        tree.feature_importances_
        for tree in clfdict['best_classifier'].estimators_
    ])
    stdev_feature_importances = np.std(feature_importances_per_tree,axis=0)

    feature_names = np.array(clfdict['feature_names'])

    plt.figure(figsize=(6.4*3.0,4.8))

    # confusion matrix
    plt.subplot(121)
    classes = np.array(classlabels)
    plt.imshow(confmatrix, interpolation='nearest', cmap=plt.cm.Blues)
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes)
    plt.yticks(tick_marks, classes)
    plt.title('evaluation set confusion matrix')
    plt.ylabel('predicted class')
    plt.xlabel('actual class')

    thresh = confmatrix.max() / 2.
    for i, j in itertools.product(range(confmatrix.shape[0]),
                                  range(confmatrix.shape[1])):
        plt.text(j, i, confmatrix[i, j],
                 horizontalalignment="center",
                 color="white" if confmatrix[i, j] > thresh else "black")

    # feature importances
    plt.subplot(122)

    features = np.array(feature_names)
    sorted_ind = np.argsort(overall_feature_importances)[::-1]

    features = features[sorted_ind]
    feature_names = feature_names[sorted_ind]
    overall_feature_importances = overall_feature_importances[sorted_ind]
    stdev_feature_importances = stdev_feature_importances[sorted_ind]

    plt.bar(np.arange(0,features.size),
            overall_feature_importances,
            yerr=stdev_feature_importances,
            width=0.8,
            color='grey')
    plt.xticks(np.arange(0,features.size),
               features,
               rotation=90)
    plt.yticks([0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0])
    plt.xlim(-0.75, features.size - 1.0 + 0.75)
    plt.ylim(0.0,0.9)
    plt.ylabel('relative importance')
    plt.title('relative importance of features')

    plt.subplots_adjust(wspace=0.1)

    plt.savefig(outfile,
                bbox_inches='tight',
                dpi=100)
    plt.close('all')
    return outfile
