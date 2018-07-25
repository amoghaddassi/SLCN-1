import glob
import datetime
import os

import numpy as np
import pandas as pd
import pymc3 as pm
import theano.tensor as T

from shared_modeling_simulation import get_paths


def load_data(run_on_cluster, fitted_data_name, kids_and_teens_only, adults_only, verbose):

    # Get data path and save path
    paths = get_paths(run_on_cluster)
    if fitted_data_name == 'humans':
        data_dir = paths['human data']
        file_name_pattern = 'PS*.csv'
        n_trials = 128
        n_subj = 500
    else:
        learning_style = 'hierarchical'
        data_dir = paths['simulations']
        file_name_pattern = 'PS' + learning_style + '*.csv'
        n_trials = 200
        n_subj = 50

    # Prepare things for loading data
    filenames = glob.glob(data_dir + file_name_pattern)[:n_subj]
    assert len(filenames) > 0, "Error: There are no files with pattern {0} in {1}".format(file_name_pattern, data_dir)
    choices = np.zeros((n_trials, len(filenames)))
    rewards = np.zeros(choices.shape)
    age = np.full(n_subj, np.nan)

    # Load data and bring in the right format
    SLCNinfo = pd.read_csv(paths['ages file name'])
    for file_idx, filename in enumerate(filenames):
        agent_data = pd.read_csv(filename)
        if agent_data.shape[0] > n_trials:
            choices[:, file_idx] = np.array(agent_data['selected_box'])[:n_trials]
            rewards[:, file_idx] = agent_data['reward'].tolist()[:n_trials]
            sID = agent_data['sID'][0]
            age[file_idx] = SLCNinfo[SLCNinfo['ID'] == sID]['PreciseYrs'].values

    # Remove excess columns
    rewards = np.delete(rewards, range(file_idx + 1, n_subj), 1)
    choices = np.delete(choices, range(file_idx + 1, n_subj), 1)
    age = age[:file_idx + 1]
    # pd.DataFrame(age).to_csv('C:/Users/maria/MEGAsync/SLCNdata/age.csv')

    # Delete kid/teen or adult data sets
    if kids_and_teens_only:
        rewards = rewards[:, age <= 18]
        choices = choices[:, age <= 18]
        age = age[age <= 18]
    elif adults_only:
        rewards = rewards[:, age > 18]
        choices = choices[:, age > 18]
        age = age[age > 18]

    n_subj = choices.shape[1]

    # Get each participant's group assignment
    group = np.zeros(n_subj, dtype=int)
    group[age > 12] = 1
    group[age > 17] = 2
    n_groups = len(np.unique(group))

    # z-score age
    age = (age - np.nanmean(age)) / np.nanstd(age)

    # Remove subjects that are missing age
    keep = np.invert(np.isnan(age))
    n_subj = np.sum(keep)
    age = age[keep]
    group = group[keep]
    rewards = rewards[:, keep]
    choices = choices[:, keep]

    # Look at data
    print("Loaded {0} datasets with pattern {1} from {2}...\n".format(n_subj, file_name_pattern, data_dir))
    if verbose:
        print("Choices - shape: {0}\n{1}\n".format(choices.shape, choices))
        print("Rewards - shape: {0}\n{1}\n".format(rewards.shape, rewards))

    return [n_subj,
            T.as_tensor_variable(rewards),
            T.as_tensor_variable(choices),
            T.as_tensor_variable(age),
            T.as_tensor_variable(group),
            n_groups]


def get_save_dir_and_save_id(run_on_cluster, file_name_suff, fitted_data_name, n_samples):

    save_dir = get_paths(run_on_cluster)['fitting results']
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    now = datetime.datetime.now()
    save_id = '_'.join([file_name_suff,
                        str(now.year), str(now.month), str(now.day), str(now.hour), str(now.minute),
                        fitted_data_name, 'n_samples' + str(n_samples)])

    return save_dir, save_id


def print_logp_info(model):

    print("Checking that none of the logp are -inf:")
    print("Test point: {0}".format(model.test_point))
    print("\tmodel.logp(model.test_point): {0}".format(model.logp(model.test_point)))

    for RV in model.basic_RVs:
        print("\tlogp of {0}: {1}".format(RV.name, RV.logp(model.test_point)))
