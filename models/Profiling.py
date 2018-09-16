import pymc3 as pm
import numpy as np
import theano
import theano.tensor as T

from shared_aliens import alien_initial_Q
from modeling_helpers import load_aliens_data

# Which data should be fitted?
fitted_data_name = 'humans'  # 'humans', 'simulations'
n_seasons, n_TS, n_aliens, n_actions = 3, 3, 4, 3


# Define function to update Q
def update_Qs_1subj_flat(season, alien, action, reward,
                         Q_low,
                         alpha, forget):

    # Forget Q-values a little bit
    Q_low = (1 - forget) * Q_low + forget * alien_initial_Q

    # Calculate RPEs & update Q-values
    current_trial_low = season, alien, action
    RPE_low = reward - Q_low[current_trial_low]
    Q_low = T.set_subtensor(Q_low[current_trial_low],
                            Q_low[current_trial_low] + alpha * RPE_low)

    return Q_low


def update_Qs_1subj_hier(season, alien, action, reward,
                         Q_low, Q_high,
                         alpha, alpha_high, forget):

    # Select TS
    Q_high_sub = Q_high[season]
    p_high = T.nnet.softmax(Q_high_sub)  # beta_high *
    TS = T.argmax(p_high, axis=1)  # Hierarchical deterministic

    # Forget Q-values a little bit
    Q_low = (1 - forget) * Q_low + forget * alien_initial_Q

    # Calculate RPEs & update Q-values
    current_trial_high = season, TS
    RPE_high = reward - Q_high[current_trial_high]
    Q_high = T.set_subtensor(Q_high[current_trial_high],
                             Q_high[current_trial_high] + alpha_high * RPE_high)

    current_trial_low = TS, alien, action
    RPE_low = reward - Q_low[current_trial_low]
    Q_low = T.set_subtensor(Q_low[current_trial_low],
                            Q_low[current_trial_low] + alpha * RPE_low)

    return [Q_low, Q_high, TS]


# PROFILE JUST THESE FUNCTIONS
# Define flat update symbolically
seasons = T.imatrix('seasons')
aliens = T.imatrix('seasons')
actions = T.imatrix('seasons')
rewards = T.imatrix('seasons')

alpha = T.iscalar('alpha')
forget = T.iscalar('forget')

Q_low0 = alien_initial_Q * T.ones([n_TS, n_aliens, n_actions], dtype='int32')

Q_low, updates = theano.scan(fn=update_Qs_1subj_flat,
                             sequences=[seasons, aliens, actions, rewards],
                             outputs_info=[Q_low0],
                             non_sequences=[alpha, forget],
                             profile=True,
                             name='my_scan')

print('compiling flat theano scan as function...')
Qs_scan = theano.function(inputs=[seasons, aliens, actions, rewards, Q_low0, alpha, forget],
                          outputs=[Q_low],
                          updates=updates,
                          profile=True)

# Profile flat update
Qs_scan.profile.summary()

# Define hierarchical update symbolically
Q_high0 = alien_initial_Q * T.ones([n_seasons, n_TS])
alpha_high = T.iscalar('alpha_high')

[Q_low, _, TS], updates_hier = theano.scan(fn=update_Qs_1subj_hier,
                                sequences=[seasons, aliens, actions, rewards],
                                outputs_info=[Q_low0, Q_high0, None],
                                non_sequences=[alpha, alpha_high, forget],
                                profile=True,
                                name='my_scan')

Qs_scan_hier = theano.function(inputs=[seasons, aliens, actions, rewards, Q_low0, Q_high0, alpha, alpha_high, forget],
                               outputs=[Q_low, _, TS],
                               updates=updates_hier,
                               profile=True)

# Profile hierarchical update
Qs_scan_hier.profile.summary()

# PROFILE THE WHOLE MODEL
max_n_subj = 1  # set > 31 to include all subjects
n_subj, n_trials, seasons, aliens, actions, rewards =\
    load_aliens_data(False, fitted_data_name, max_n_subj, False)

# Convert data to tensor variables
seasons = theano.shared(np.asarray(seasons, dtype='int32'))
aliens = theano.shared(np.asarray(aliens, dtype='int32'))
actions = theano.shared(np.asarray(actions, dtype='int32'))
rewards = theano.shared(np.asarray(rewards, dtype='int32'))
#
# with pm.Model() as flat_model:
#
#     ## RL parameters: softmax temperature beta; learning rate alpha; forgetting of Q-values
#     # Parameter means
#     beta = pm.Bound(pm.Normal, lower=0)('beta', mu=1, sd=5, testval=1.5)
#     alpha = pm.Uniform('alpha', lower=0, upper=1, testval=0.1)
#     forget = pm.Uniform('forget', lower=0, upper=1, testval=0.001)
#     T.printing.Print('alpha')(alpha)
#
#     ## Select action based on Q-values
#     Q_low0 = alien_initial_Q * T.ones([n_TS, n_aliens, n_actions])
#     Q_low, _ = theano.scan(fn=update_Qs_1subj_flat,
#                            sequences=[seasons, aliens, actions, rewards],
#                            outputs_info=[Q_low0],
#                            non_sequences=[alpha, forget],
#                            profile=True,
#                            name='my_scan')
#
#     Q_low = T.concatenate([[Q_low0], Q_low[:-1]], axis=0)  # Add first trial's Q-values, remove last trials Q-values
#
#     # Select Q-values for each trial & translate into probabilities
#     Q_sub = Q_low[T.arange(n_trials), seasons.flatten(), aliens.flatten()]  # Q_sub.shape -> [n_trials, n_subj, n_actions]
#     Q_sub = beta * Q_sub
#     p_low = T.nnet.softmax(Q_sub)
#     T.printing.Print('p_low')(p_low)
#
#     # Select actions based on Q-values
#     action_wise_actions = actions.flatten()
#     actions = pm.Categorical('actions', p=p_low, observed=action_wise_actions)
#
#     # Check logps and draw samples
#     flat_trace = pm.sample(2, tune=2, chains=1, cores=1)
#
# flat_model.profile(flat_model.logpt).summary()

# with pm.Model() as hier_model:
#
#     ## RL parameters: softmax temperature beta; learning rate alpha; forgetting of Q-values
#     # Parameter means
#     beta = pm.Bound(pm.Normal, lower=0)('beta', mu=1, sd=5, testval=1.5)
#     alpha = pm.Uniform('alpha', lower=0, upper=1, testval=0.1)
#     forget = pm.Uniform('forget', lower=0, upper=1, testval=0.001)
#     alpha_high = pm.Uniform('alpha_high', lower=0, upper=1, testval=0.1)
#
#     ## Select action based on Q-values
#     Q_low0 = alien_initial_Q * T.ones([n_TS, n_aliens, n_actions])
#     Q_high0 = alien_initial_Q * T.ones([n_seasons, n_TS])
#
#     [Q_low, _, TS], _ = theano.scan(fn=update_Qs_1subj_hier,
#                                     sequences=[seasons, aliens, actions, rewards],
#                                     outputs_info=[Q_low0, Q_high0, None],
#                                     non_sequences=[alpha, alpha_high, forget],
#                                     profile=True,
#                                     name='my_scan')
#
#     Q_low = T.concatenate([[Q_low0], Q_low[:-1]], axis=0)  # Add first trial's Q-values, remove last trials Q-values
#
#     # Select Q-values for each trial & translate into probabilities
#     Q_sub = Q_low[T.arange(n_trials), TS.flatten(), aliens.flatten()]  # Q_sub.shape -> [n_trials, n_subj, n_actions]
#     Q_sub = beta * Q_sub
#     p_low = T.nnet.softmax(Q_sub)
#
#     # Select actions based on Q-values
#     action_wise_actions = actions.flatten()
#     actions = pm.Categorical('actions', p=p_low, observed=action_wise_actions)
#
#     # Check logps and draw samples
#     hier_trace = pm.sample(2, tune=2, chains=1, cores=1)
#
# hier_model.profile(hier_model.logpt).summary()
